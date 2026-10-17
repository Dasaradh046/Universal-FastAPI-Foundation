"""
Architecture tests for the Universal FastAPI Foundation.

Validates PRD §6.3 module rules:
- Module manifests are validated (IDs, versions, dependencies)
- Module boundaries are respected (no forbidden cross-module imports)
- Layer separation: routers HTTP, services business logic, repositories data
- Module dependency graph is acyclic
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from app.modules.module_sdk import ModuleManifest

# ---------------------------------------------------------------------------
# Module manifest validation
# ---------------------------------------------------------------------------


def test_module_manifest_requires_id():
    """ModuleManifest rejects an empty module ID."""
    with pytest.raises(ValueError, match="Module ID is required"):
        ModuleManifest(
            id="",
            version="1.0.0",
            name="Test",
            description="Test module",
            router=None,
        )


def test_module_manifest_requires_version():
    """ModuleManifest rejects an empty module version."""
    with pytest.raises(ValueError, match="Module version is required"):
        ModuleManifest(
            id="test_module",
            version="",
            name="Test",
            description="Test module",
            router=None,
        )


def test_module_manifest_requires_name():
    """ModuleManifest rejects an empty module name."""
    with pytest.raises(ValueError, match="Module name is required"):
        ModuleManifest(
            id="test_module",
            version="1.0.0",
            name="",
            description="Test module",
            router=None,
        )


def test_module_manifest_creates_default_router_when_none_provided():
    """ModuleManifest creates a default APIRouter when no router is passed."""
    manifest = ModuleManifest(
        id="test_module",
        version="1.0.0",
        name="Test",
        description="Test module",
    )
    assert manifest.router is not None


def test_example_module_manifest_is_valid():
    """The reference example module has a valid manifest."""
    from app.modules.example_module import MANIFEST

    assert MANIFEST.id == "example_module"
    assert MANIFEST.version == "1.0.0"
    assert MANIFEST.name == "Example Module"
    assert MANIFEST.dependencies == []
    assert MANIFEST.router is not None


# ---------------------------------------------------------------------------
# Module boundary rules
# ---------------------------------------------------------------------------

MODULES_DIR = Path(__file__).resolve().parents[2] / "modules"


def _module_source_files(module_name: str) -> list[Path]:
    """Return all .py source files for a given module."""
    module_dir = MODULES_DIR / module_name
    if not module_dir.is_dir():
        return []
    return sorted(module_dir.rglob("*.py"))


def _source_tree(module_name: str) -> str:
    """Concatenate all source files of a module into one string."""
    parts = []
    for path in _module_source_files(module_name):
        parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


@pytest.mark.parametrize("module_name", ["example_module", "auth", "identity", "audit"])
def test_modules_do_not_create_database_engines(module_name: str):
    """Modules must not create database engines directly (PRD §6.3 rule 4)."""
    source = _source_tree(module_name)
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute):
                if func.attr in ("create_async_engine", "create_engine"):
                    pytest.fail(
                        f"{module_name} creates a database engine directly:"
                        f" {ast.dump(node)}"
                    )


@pytest.mark.parametrize("module_name", ["example_module", "auth", "identity", "audit"])
def test_modules_do_not_import_cross_module_repositories(module_name: str):
    """Modules must not import cross-module repositories (PRD §6.3 rule 2)."""
    source = _source_tree(module_name)
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            # Match app.modules.<other_module>.repository.*
            parts = node.module.split(".")
            if (
                len(parts) >= 4
                and parts[0] == "app"
                and parts[1] == "modules"
                and parts[3] == "repository"
                and parts[2] != module_name
            ):
                pytest.fail(
                    f"{module_name} imports repository from another module"
                    f" ({parts[2]}): {node.module}"
                )


def test_example_module_follows_router_service_repository_layers():
    """Example module separates router, service, and repository concerns."""
    example_dir = MODULES_DIR / "example_module"
    router_src = (example_dir / "router.py").read_text()
    service_src = (example_dir / "service.py").read_text()
    repository_src = (example_dir / "repository.py").read_text()

    # Router should reference HTTP concepts (APIRouter, Depends, status)
    assert "APIRouter" in router_src
    assert "Depends" in router_src

    # Service should reference business logic patterns
    assert "class ExampleService" in service_src
    assert "repository" in service_src.lower()

    # Repository should reference data access patterns
    assert "class ExampleRepository" in repository_src
    assert "AsyncSession" in repository_src or "session" in repository_src.lower()


def test_example_module_registers_routes_through_registry():
    """Modules register routes through ModuleManifest.router (PRD §6.3 rule 5)."""
    from app.modules.example_module import MANIFEST

    assert MANIFEST.router is not None
    # The manifest's router should have routes registered
    routes = [r for r in MANIFEST.router.routes]
    assert len(routes) > 0, "Example module router should have registered routes"


def test_module_dependency_graph_is_acyclic():
    """Module dependencies must be acyclic (PRD §6.3 rule 7)."""
    from app.modules.auth import MANIFEST as auth_manifest
    from app.modules.example_module import MANIFEST as example_manifest
    from app.modules.identity import MANIFEST as identity_manifest

    manifests = {
        example_manifest.id: example_manifest,
        auth_manifest.id: auth_manifest,
        identity_manifest.id: identity_manifest,
    }

    # Simple cycle detection: DFS
    visited: set[str] = set()
    rec_stack: set[str] = set()

    def has_cycle(module_id: str) -> bool:
        visited.add(module_id)
        rec_stack.add(module_id)
        manifest = manifests.get(module_id)
        if manifest:
            for dep in manifest.dependencies:
                if dep not in visited:
                    if has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True
        rec_stack.discard(module_id)
        return False

    for module_id in manifests:
        if module_id not in visited:
            assert not has_cycle(module_id), f"Cycle detected starting at {module_id}"


__all__ = []
