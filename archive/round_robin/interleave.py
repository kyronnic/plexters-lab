from __future__ import annotations

from itertools import zip_longest
from typing import Iterable, Iterator, List, Sequence, TypeVar

T = TypeVar("T")

def round_robin(*iterables: Iterable[T], fillvalue=None) -> Iterator[T]:
    for group in zip_longest(*iterables, fillvalue=fillvalue):
        for item in group:
            if item is not fillvalue:
                yield item

def interleave_episode_lists(episode_lists: Sequence[List[T]]) -> List[T]:
    return list(round_robin(*episode_lists))