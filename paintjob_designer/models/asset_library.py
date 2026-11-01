# coding: utf-8

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

TAsset = TypeVar("TAsset")


class AssetLibrary(BaseModel, Generic[TAsset]):
    """Ordered collection of assets the session is working on.

    Subclasses declare the list field, whose name is part of the saved JSON,
    and return it from `_items`.
    """

    model_config = ConfigDict(frozen=False)

    def _items(self) -> list[TAsset]:
        raise NotImplementedError

    def count(self) -> int:
        return len(self._items())

    def add(self, asset: TAsset) -> int:
        """Append `asset` and return its new index."""
        items = self._items()
        items.append(asset)
        return len(items) - 1

    def remove(self, index: int) -> TAsset:
        return self._items().pop(index)

    def move(self, from_index: int, to_index: int) -> None:
        items = self._items()
        asset = items.pop(from_index)
        items.insert(max(0, min(to_index, len(items))), asset)
