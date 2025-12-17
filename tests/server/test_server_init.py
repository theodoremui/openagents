"""
Tests for server/__init__.py lazy import functionality.
"""

import pytest
from unittest.mock import patch


class TestServerInit:
    """Test server package initialization."""

    def test_lazy_import_app(self):
        """Test that app is lazily imported."""
        # Import server package
        import server
        
        # App should not be in dir() until accessed
        # (though __getattr__ makes it available)
        # Accessing app should trigger import
        app = server.app
        assert app is not None
        # Should be FastAPI app
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)

    def test_lazy_import_attribute_error(self):
        """Test that accessing non-existent attribute raises AttributeError."""
        import server
        
        with pytest.raises(AttributeError):
            _ = server.nonexistent_attribute

    def test_lazy_import_works(self):
        """Test that lazy import actually works."""
        import server
        
        # Should be able to access app
        app = server.app
        assert app is not None
        # Should be FastAPI app
        from fastapi import FastAPI
        assert isinstance(app, FastAPI)
        
        # Accessing again should return same instance
        app2 = server.app
        assert app is app2

