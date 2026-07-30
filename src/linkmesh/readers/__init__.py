"""LinkMesh input readers.

Public interfaces:
    read_gfile(filepath: str) -> GFileData
    read_boundary_file(filepath: str | Path) -> np.ndarray
"""

from linkmesh.readers.boundary_reader import (
    BoundaryFormatError,
    read_boundary_file,
)
from linkmesh.readers.gfile_reader import GFileData, read_gfile

__all__ = [
    "BoundaryFormatError",
    "GFileData",
    "read_boundary_file",
    "read_gfile",
]
