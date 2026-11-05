from starlette.requests import Request

from src.app.rate_limit import client_ip


def _request(peer: str, forwarded: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"x-forwarded-for", forwarded.encode("ascii"))],
            "client": (peer, 1234),
            "server": ("testserver", 80),
            "scheme": "http",
            "query_string": b"",
        }
    )


def test_forwarded_ip_is_used_only_for_trusted_proxy_chain() -> None:
    assert (
        client_ip(
            _request("10.0.0.2", "203.0.113.8, 10.0.0.1"),
            "10.0.0.0/8",
        )
        == "203.0.113.8"
    )
    assert (
        client_ip(_request("198.51.100.5", "203.0.113.8"), "10.0.0.0/8")
        == "198.51.100.5"
    )
