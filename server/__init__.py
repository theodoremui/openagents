"""Multi-agent orchestration server package."""

__version__ = "0.1.0"

# Lazy import to avoid triggering dependency chain during tests
# Only import app when actually accessed via `from server import app`
def __getattr__(name):
    if name == "app":
        from .main import app
        return app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["app"]