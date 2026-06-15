from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class RateLimiter:
    """Simple min-interval rate limiter."""

    min_interval: float = 0.12
    _last: float = field(default=0.0, repr=False)

    def wait(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self._last = time.monotonic()


# EP API: 500 requests / 5 min
ep_limiter = RateLimiter(min_interval=0.12)
# WMM / EP profile pages
web_limiter = RateLimiter(min_interval=1.0)
