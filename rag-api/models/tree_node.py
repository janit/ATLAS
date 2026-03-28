"""PageIndex tree domain models.

Covers the unified navigation tree used by the indexer and retriever:
NodeType enum, NodeMetadata, TreeNode (recursive), and TreeIndex (root
wrapper persisted to disk).
"""

from __future__ import annotations

import enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enum
# ---------------------------------------------------------------------------

class NodeType(str, enum.Enum):
    """Kind of node in the code navigation tree."""

    REPOSITORY = "repository"
    DIRECTORY = "directory"
    FILE = "file"
    CLASS = "class"
    FUNCTION = "function"
    BLOCK = "block"


# ---------------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------------

class NodeMetadata(BaseModel):
    """Optional metadata attached to a tree node."""

    line_count: Optional[int] = None
    language: Optional[str] = None
    file_hash: Optional[str] = None
    import_count: Optional[int] = None
    start_line: Optional[int] = None
    end_line: Optional[int] = None


# ---------------------------------------------------------------------------
# Tree node (recursive)
# ---------------------------------------------------------------------------

class TreeNode(BaseModel):
    """A single node in the code navigation tree."""

    node_id: str
    node_type: NodeType
    name: str = ""
    path: str = ""
    metadata: NodeMetadata = Field(default_factory=NodeMetadata)
    content: Optional[str] = None
    summary: Optional[str] = None
    children: List[TreeNode] = Field(default_factory=list)

    def node_count(self) -> int:
        """Return the total number of nodes in this subtree (inclusive)."""
        return 1 + sum(child.node_count() for child in self.children)


# Pydantic v2 needs the model to be rebuilt after forward-ref definition.
TreeNode.model_rebuild()


# ---------------------------------------------------------------------------
# Top-level index wrapper
# ---------------------------------------------------------------------------

class TreeIndex(BaseModel):
    """Persisted wrapper around the root TreeNode plus project metadata."""

    project_id: str
    root: TreeNode
    file_hashes: Dict[str, str] = Field(default_factory=dict)
    created_at: Optional[str] = None
