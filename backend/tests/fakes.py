"""A tiny in-memory stand-in for the Upstash Redis client, just enough to
back app.core.rate_limit.check_and_increment in tests without a real
network-reachable Redis instance."""

import time


class _FakePipeline:
    def __init__(self, store: dict):
        self._store = store
        self._ops = []

    def incr(self, key: str):
        self._ops.append(("incr", key))
        return self

    def ttl(self, key: str):
        self._ops.append(("ttl", key))
        return self

    async def execute(self):
        results = []
        for op, key in self._ops:
            if op == "incr":
                count, expires_at = self._store.get(key, (0, None))
                count += 1
                self._store[key] = (count, expires_at)
                results.append(count)
            elif op == "ttl":
                _, expires_at = self._store.get(key, (0, None))
                if expires_at is None:
                    results.append(-1)
                else:
                    remaining = int(expires_at - time.time())
                    results.append(remaining if remaining > 0 else -2)
        self._ops = []
        return results


class FakeRedis:
    def __init__(self):
        self._store: dict[str, tuple[int, float | None]] = {}

    def pipeline(self):
        return _FakePipeline(self._store)

    async def expire(self, key: str, seconds: int):
        count, _ = self._store.get(key, (0, None))
        self._store[key] = (count, time.time() + seconds)

    async def ping(self):
        return True

    async def aclose(self):
        return None

    def reset(self):
        self._store.clear()
