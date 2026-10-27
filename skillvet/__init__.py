"""skillvet — security audit for AI agent skills, hooks and MCP configs."""

__version__ = "1.0.0"

from .model import Finding, ScanResult, Severity  # noqa: F401
from .scanner import Scanner  # noqa: F401

__all__ = ["Finding", "ScanResult", "Scanner", "Severity", "__version__"]
