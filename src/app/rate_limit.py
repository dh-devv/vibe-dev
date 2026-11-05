from __future__ import annotations

from collections import defaultdict, deque
from datetime import date, datetime, timedelta, timezone
from ipaddress import ip_address, ip_network
from typing import Deque

from fastapi import HTTPException, Request

from src.app.config import Settings


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._events: dict[tuple[str, str], Deque[datetime]] = defaultdict(deque)
        self._last_pruned_day: date | None = None

    def check_and_record(
        self, settings: Settings, client_ip: str, user_id: str
    ) -> None:
        now = datetime.now(timezone.utc)
        minute_ago = now - timedelta(seconds=60)
        today = now.date()
        if self._last_pruned_day != today:
            for key, events in list(self._events.items()):
                while events and events[0].date() < today:
                    events.popleft()
                if not events:
                    del self._events[key]
            self._last_pruned_day = today
        identities = (("ip", client_ip), ("user", user_id), ("global", "all"))
        limits = (
            (settings.ip_per_minute, settings.ip_per_day),
            (settings.user_per_minute, settings.user_per_day),
            (settings.global_per_day, settings.global_per_day),
        )
        retry_after = max(
            1,
            int(
                (
                    now.replace(hour=0, minute=0, second=0, microsecond=0)
                    + timedelta(days=1)
                    - now
                ).total_seconds()
            ),
        )
        for (kind, identity), (per_minute, per_day) in zip(
            identities, limits, strict=True
        ):
            events = self._events[(kind, identity)]
            while events and events[0].date() < today:
                events.popleft()
            daily_count = sum(event.date() == today for event in events)
            minute_count = sum(event > minute_ago for event in events)
            if kind == "global" and daily_count >= settings.global_per_day:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "code": "DAILY_LIMIT",
                        "message": "오늘 법정이 만석입니다. 내일 다시 이용해 주세요.",
                        "retryable": True,
                    },
                    headers={"Retry-After": str(retry_after)},
                )
            if daily_count >= per_day or (
                kind != "global" and minute_count >= per_minute
            ):
                raise HTTPException(
                    status_code=429,
                    detail={
                        "code": "RATE_LIMITED",
                        "message": "요청 한도를 넘었습니다. 잠시 후 다시 시도해 주세요.",
                        "retryable": True,
                    },
                    headers={
                        "Retry-After": "60"
                        if minute_count >= per_minute
                        else str(retry_after)
                    },
                )
        for kind, identity in identities:
            self._events[(kind, identity)].append(now)


def client_ip(request: Request, trusted_proxy_ips: str) -> str:
    peer = request.client.host if request.client else "unknown"
    try:
        peer_address = ip_address(peer)
    except ValueError:
        return peer
    trusted = []
    for entry in trusted_proxy_ips.split(","):
        entry = entry.strip()
        if entry:
            try:
                trusted.append(ip_network(entry, strict=False))
            except ValueError:
                continue
    if any(peer_address in network for network in trusted):
        forwarded_for = request.headers.get("x-forwarded-for", "").split(",")
        for entry in reversed(forwarded_for):
            try:
                candidate = ip_address(entry.strip())
            except ValueError:
                break
            if not any(candidate in network for network in trusted):
                return str(candidate)
    return str(peer_address)
