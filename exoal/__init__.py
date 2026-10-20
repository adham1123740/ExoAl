"""ExoAl — dynamic Python client for AI APIs."""

from .client import (
    ExoAl,
    ExoAlError,
    APIError,
    ModelNotFoundError,
    StreamEvent,
)

__version__ = "1.1.0"
__all__ = [
    "ExoAl",
    "ExoAlError",
    "APIError",
    "ModelNotFoundError",
    "StreamEvent",
    "__version__",
]
