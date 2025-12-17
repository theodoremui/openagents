#!/usr/bin/env python3
"""
Fallback setup.py for Heroku Python buildpack compatibility.
This file allows the Python buildpack to install the package even if
pyproject.toml isn't detected correctly.
"""

from setuptools import setup, find_packages

# Read pyproject.toml if available, otherwise use minimal setup
try:
    # Try Python 3.11+ tomllib first
    try:
        import tomllib
        with open("pyproject.toml", "rb") as f:
            pyproject = tomllib.load(f)
    except ImportError:
        # Fallback to tomli for older Python
        import tomli
        with open("pyproject.toml", "rb") as f:
            pyproject = tomli.load(f)
    
    project = pyproject.get("project", {})
    setup(
        name=project.get("name", "openagents-server"),
        version=project.get("version", "0.1.0"),
        description=project.get("description", "Multi-agent orchestration server API"),
        packages=find_packages(),
        install_requires=project.get("dependencies", []),
        python_requires=project.get("requires-python", ">=3.11"),
    )
except Exception as e:
    # Fallback minimal setup if pyproject.toml can't be read
    print(f"Warning: Could not read pyproject.toml: {e}")
    print("Using minimal setup configuration")
    setup(
        name="openagents-server",
        version="0.1.0",
        description="Multi-agent orchestration server API",
        packages=find_packages(),
        python_requires=">=3.11",
    )
