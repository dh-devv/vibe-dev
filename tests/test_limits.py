from src.app.limits import RateLimiter


class Clock:
    def __init__(self, now: float = 86400 * 100 + 100) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


def make(clock: Clock, **overrides: int) -> RateLimiter:
    limits = {"ip_per_minute": 3, "ip_per_day": 20, "user_per_minute": 3, "user_per_day": 20, "global_per_day": 300}
    return RateLimiter(**{**limits, **overrides}, clock=clock)


def test_ip_minute_window_slides() -> None:
    clock = Clock()
    limiter = make(clock)
    for _ in range(3):
        assert limiter.acquire("1.1.1.1", "u1") is None
        clock.now += 1

    denied = limiter.acquire("1.1.1.1", "u2")
    assert denied is not None and denied.code == "RATE_LIMITED"
    assert 55 <= denied.retry_after <= 60

    clock.now += 58
    assert limiter.acquire("1.1.1.1", "u2") is None


def test_user_limit_is_independent_of_ip() -> None:
    limiter = make(Clock(), user_per_minute=1)

    assert limiter.acquire("1.1.1.1", "u1") is None
    assert limiter.acquire("2.2.2.2", "u1").code == "RATE_LIMITED"
    assert limiter.acquire("2.2.2.2", "u2") is None


def test_denied_requests_are_not_counted() -> None:
    clock = Clock()
    limiter = make(clock, ip_per_minute=100, user_per_minute=100, ip_per_day=2)
    assert limiter.acquire("ip", "a") is None
    assert limiter.acquire("ip", "b") is None
    for _ in range(5):
        assert limiter.acquire("ip", "c").code == "RATE_LIMITED"

    clock.now += 86400
    assert limiter.acquire("ip", "c") is None


def test_daily_limit_resets_at_utc_midnight() -> None:
    clock = Clock(86400 * 100 + 86400 - 10)
    limiter = make(clock, ip_per_minute=100, user_per_minute=100, global_per_day=1)
    assert limiter.acquire("ip", "u") is None

    denied = limiter.acquire("ip2", "u2")
    assert denied.code == "DAILY_LIMIT" and denied.retry_after == 10

    clock.now += 11
    assert limiter.acquire("ip2", "u2") is None
