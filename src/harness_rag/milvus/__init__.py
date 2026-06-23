"""Shared Milvus infrastructure for assistant_core."""

from .collections import CollectionSetupResult, MilvusCollectionClient, ensure_collection
from .client import Embedder, MilvusClientConfig, MilvusSearchClient
from .executor import BoundedMilvusExecutor, MilvusExecutorBusy, MilvusExecutorConfig

__all__ = [
    "BoundedMilvusExecutor",
    "CollectionSetupResult",
    "Embedder",
    "MilvusCollectionClient",
    "MilvusClientConfig",
    "MilvusExecutorBusy",
    "MilvusExecutorConfig",
    "MilvusSearchClient",
    "ensure_collection",
]
