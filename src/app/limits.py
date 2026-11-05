import math
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

_DAY = 86400
_MINUTE = 60
_GC_THRESHOLD = 5000


@dataclass(frozen=True)
class Denied:
    code: str
    retry_after: int


class RateLimiter:
    """프로세스 메모리 기반 한도. 재시작하면 초기화되고 복제본 간에는 공유되지 않는다."""

    def __init__(
        self,
        ip_per_minute: int,
        ip_per_day: int,
        user_per_minute: int,
        user_per_day: int,
        global_per_day: int,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._limits = (ip_per_minute, ip_per_day, user_per_minute, user_per_day, global_per_day)
        self._clock = clock
        self._day = -1
        self._ip_minute: dict[str, deque[float]] = {}
        self._user_minute: dict[str, deque[float]] = {}
        self._ip_day: dict[str, int] = {}
        self._user_day: dict[str, int] = {}
        self._global_day = 0

    def acquire(self, ip: str, user: str) -> Denied | None:
        """사전 검사를 모두 통과한 요청만 센다. 거부된 요청은 세지 않는다."""
        now = self._clock()
        self._roll_day(now)
        self._gc(now)
        ip_min_limit, ip_day_limit, user_min_limit, user_day_limit, global_limit = self._limits
        until_midnight = max(1, math.ceil((self._day + 1) * _DAY - now))

        ip_window = self._window(self._ip_minute, ip, now)
        if len(ip_window) >= ip_min_limit:
            return Denied("RATE_LIMITED", self._wait(ip_window, now))
        if self._ip_day.get(ip, 0) >= ip_day_limit:
            return Denied("RATE_LIMITED", until_midnight)
        user_window = self._window(self._user_minute, user, now)
        if len(user_window) >= user_min_limit:
            return Denied("RATE_LIMITED", self._wait(user_window, now))
        if self._user_day.get(user, 0) >= user_day_limit:
            return Denied("RATE_LIMITED", until_midnight)
        if self._global_day >= global_limit:
            return Denied("DAILY_LIMIT", until_midnight)

        ip_window.append(now)
        user_window.append(now)
        self._ip_day[ip] = self._ip_day.get(ip, 0) + 1
        self._user_day[user] = self._user_day.get(user, 0) + 1
        self._global_day += 1
        return None

    def _roll_day(self, now: float) -> None:
        day = int(now // _DAY)
        if day != self._day:
            self._day = day
            self._ip_day.clear()
            self._user_day.clear()
            self._global_day = 0

    @staticmethod
    def _window(store: dict[str, deque[float]], key: str, now: float) -> deque[float]:
        window = store.setdefault(key, deque())
        while window and window[0] <= now - _MINUTE:
            window.popleft()
        return window

    @staticmethod
    def _wait(window: deque[float], now: float) -> int:
        return max(1, math.ceil(window[0] + _MINUTE - now))

    def _gc(self, now: float) -> None:
        for store in (self._ip_minute, self._user_minute):
            if len(store) < _GC_THRESHOLD:
                continue
            for key in [k for k, w in store.items() if not w or w[-1] <= now - _MINUTE]:
                del store[key]
