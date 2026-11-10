"""Primary key generation.

Models use ``new_uuid`` as their default so that the synthetic data
generator can temporarily swap in a seeded factory and produce the
same identifiers on every run. Normal application code always gets
random UUIDs.
"""
import random
import uuid
from contextlib import contextmanager
from typing import Callable, Iterator

_factory: Callable[[], uuid.UUID] = uuid.uuid4


def new_uuid() -> uuid.UUID:
    return _factory()


@contextmanager
def deterministic_uuids(seed: int) -> Iterator[None]:
    global _factory

    rng = random.Random(seed)
    previous = _factory

    def seeded() -> uuid.UUID:
        return uuid.UUID(int=rng.getrandbits(128), version=4)

    _factory = seeded

    try:
        yield
    finally:
        _factory = previous
