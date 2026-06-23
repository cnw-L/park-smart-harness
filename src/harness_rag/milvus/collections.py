"""Official-style Milvus collection setup helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class MilvusCollectionClient(Protocol):
    def has_collection(self, *, collection_name: str) -> bool:
        ...

    def drop_collection(self, *, collection_name: str) -> Any:
        ...

    def create_collection(self, *, collection_name: str, schema: Any, index_params: Any) -> Any:
        ...


@dataclass(frozen=True)
class CollectionSetupResult:
    collection_name: str
    created: bool
    dropped_existing: bool = False


def ensure_collection(
    *,
    client: MilvusCollectionClient,
    collection_name: str,
    schema: Any,
    index_params: Any,
    drop_existing: bool = False,
) -> CollectionSetupResult:
    """Create a Milvus collection using official schema and index params."""

    exists = client.has_collection(collection_name=collection_name)
    if exists and not drop_existing:
        return CollectionSetupResult(collection_name=collection_name, created=False)
    if exists:
        client.drop_collection(collection_name=collection_name)
    client.create_collection(
        collection_name=collection_name,
        schema=schema,
        index_params=index_params,
    )
    return CollectionSetupResult(
        collection_name=collection_name,
        created=True,
        dropped_existing=exists,
    )
