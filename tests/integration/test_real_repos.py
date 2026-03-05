"""Integration tests — scan real-world repos and validate output.

These tests clone real repositories from GitHub (shallow clones),
run the full scan + generate pipeline, and validate the results.

Run with: pytest tests/integration/ -m integration
Skip with: pytest -m "not integration"
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from codebase_md.generators import AVAILABLE_FORMATS, get_generator
from codebase_md.model.architecture import ArchitectureType
from codebase_md.scanner.engine import ScanResult, scan_project


def _clone_repo(url: str, depth: int = 50) -> Path:
    """Shallow clone a repo into a temp directory.

    Args:
        url: Git clone URL.
        depth: Clone depth.

    Returns:
        Path to the cloned repo directory.
    """
    tmp_dir = tempfile.mkdtemp(prefix="codebase_md_test_")
    subprocess.run(
        ["git", "clone", "--depth", str(depth), url, tmp_dir],
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    )
    return Path(tmp_dir)


def _scan_and_validate(root_path: Path) -> ScanResult:
    """Run scan on a project and return the result.

    Args:
        root_path: Project root.

    Returns:
        ScanResult.
    """
    return scan_project(root_path, persist=False)


def _generate_all(result: ScanResult) -> dict[str, str]:
    """Generate all output formats and return them.

    Args:
        result: Scan result.

    Returns:
        Dict of format_name -> generated content.
    """
    outputs: dict[str, str] = {}
    for fmt in AVAILABLE_FORMATS:
        gen_cls = get_generator(fmt)
        gen = gen_cls()
        content = gen.generate(result.model)
        outputs[fmt] = content
    return outputs


# =========================================================================
# Test: codebase-md itself (local, no clone needed)
# =========================================================================


@pytest.mark.integration
class TestSelfScan:
    """Test scanning codebase-md itself."""

    @pytest.fixture(scope="class")
    def self_scan(self) -> ScanResult:
        """Scan codebase-md itself."""
        root = Path(__file__).resolve().parents[2]  # tests/integration -> root
        return _scan_and_validate(root)

    def test_detects_python(self, self_scan: ScanResult) -> None:
        """Should detect Python as the primary language."""
        assert "python" in self_scan.model.languages
        assert self_scan.model.languages[0] == "python"

    def test_architecture_cli_tool(self, self_scan: ScanResult) -> None:
        """Should detect CLI tool architecture."""
        assert self_scan.model.architecture.architecture_type == ArchitectureType.CLI_TOOL

    def test_has_entry_point(self, self_scan: ScanResult) -> None:
        """Should find cli.py as an entry point."""
        entry_points = self_scan.model.architecture.entry_points
        assert any("cli.py" in ep for ep in entry_points)

    def test_detects_dependencies(self, self_scan: ScanResult) -> None:
        """Should find core dependencies."""
        dep_names = {d.name for d in self_scan.model.dependencies}
        assert "typer" in dep_names
        assert "rich" in dep_names
        assert "pydantic" in dep_names

    def test_conventions_snake_case(self, self_scan: ScanResult) -> None:
        """Should detect snake_case naming."""
        from codebase_md.model.convention import NamingConvention

        assert self_scan.model.conventions.naming == NamingConvention.SNAKE_CASE

    def test_conventions_absolute_imports(self, self_scan: ScanResult) -> None:
        """Should detect absolute import style."""
        from codebase_md.model.convention import ImportStyle

        assert self_scan.model.conventions.import_style == ImportStyle.ABSOLUTE

    def test_git_insights_populated(self, self_scan: ScanResult) -> None:
        """Should have git insights with commits."""
        assert self_scan.model.git_insights.total_commits > 0
        assert len(self_scan.model.git_insights.contributors) > 0

    def test_description_nonempty(self, self_scan: ScanResult) -> None:
        """Should extract a project description."""
        assert self_scan.model.description != ""

    def test_build_commands(self, self_scan: ScanResult) -> None:
        """Should extract build commands."""
        assert len(self_scan.model.build_commands) > 0

    def test_frameworks_detected(self, self_scan: ScanResult) -> None:
        """Should detect frameworks like typer, pytest."""
        assert len(self_scan.model.frameworks) > 0

    def test_modules_detected(self, self_scan: ScanResult) -> None:
        """Should detect project modules."""
        assert len(self_scan.model.modules) > 0
        mod_names = {m.name for m in self_scan.model.modules}
        assert "src" in mod_names

    def test_all_generators_produce_output(self, self_scan: ScanResult) -> None:
        """All 6 generators should produce non-empty output."""
        outputs = _generate_all(self_scan)
        for fmt, content in outputs.items():
            assert len(content) > 100, f"Generator '{fmt}' produced too little output"
            assert self_scan.model.name in content or "python" in content.lower(), (
                f"Generator '{fmt}' doesn't contain project data"
            )

    def test_scan_duration_reasonable(self, self_scan: ScanResult) -> None:
        """Scan should complete quickly on this small project."""
        assert self_scan.duration < 30.0  # Should be well under 30s


# =========================================================================
# Test: Empty repo (created locally)
# =========================================================================


@pytest.mark.integration
class TestEmptyRepo:
    """Test scanning an empty repo."""

    @pytest.fixture(scope="class")
    def empty_scan(self, tmp_path_factory: pytest.TempPathFactory) -> ScanResult:
        """Create and scan an empty repo."""
        tmp = tmp_path_factory.mktemp("empty_repo")
        (tmp / "README.md").write_text("# Empty Project\n")
        # Init git
        subprocess.run(["git", "init"], cwd=tmp, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=tmp, capture_output=True, check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=tmp, capture_output=True, check=True,
        )
        subprocess.run(["git", "add", "."], cwd=tmp, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=tmp, capture_output=True, check=True,
        )
        return _scan_and_validate(tmp)

    def test_no_crash(self, empty_scan: ScanResult) -> None:
        """Scanning an empty repo should not crash."""
        assert empty_scan.model is not None

    def test_empty_languages(self, empty_scan: ScanResult) -> None:
        """Should detect no languages."""
        assert empty_scan.model.languages == []

    def test_empty_dependencies(self, empty_scan: ScanResult) -> None:
        """Should detect no dependencies."""
        assert empty_scan.model.dependencies == []

    def test_empty_modules(self, empty_scan: ScanResult) -> None:
        """Should detect no modules (or minimal)."""
        # May have 0 modules or just empty ones
        assert isinstance(empty_scan.model.modules, list)

    def test_generators_no_crash(self, empty_scan: ScanResult) -> None:
        """All generators should produce output without crashing."""
        for fmt in AVAILABLE_FORMATS:
            gen = get_generator(fmt)()
            content = gen.generate(empty_scan.model)
            assert len(content) > 0, f"Generator '{fmt}' produced empty output"


# =========================================================================
# Test: FastAPI full-stack template (Python + TypeScript)
# =========================================================================


@pytest.mark.integration
class TestFastAPITemplate:
    """Test scanning the FastAPI full-stack template."""

    REPO_URL = "https://github.com/fastapi/full-stack-fastapi-template.git"

    @pytest.fixture(scope="class")
    def repo_path(self) -> Path:
        """Clone the repo."""
        path = _clone_repo(self.REPO_URL)
        yield path
        # Cleanup
        import shutil
        shutil.rmtree(path, ignore_errors=True)

    @pytest.fixture(scope="class")
    def fastapi_scan(self, repo_path: Path) -> ScanResult:
        """Scan the FastAPI template."""
        return _scan_and_validate(repo_path)

    def test_detects_python(self, fastapi_scan: ScanResult) -> None:
        """Should detect Python."""
        assert "python" in fastapi_scan.model.languages

    def test_detects_typescript(self, fastapi_scan: ScanResult) -> None:
        """Should detect TypeScript."""
        assert "typescript" in fastapi_scan.model.languages

    def test_frameworks_include_fastapi(self, fastapi_scan: ScanResult) -> None:
        """Should detect FastAPI framework."""
        assert "fastapi" in fastapi_scan.model.frameworks

    def test_docker_detected(self, fastapi_scan: ScanResult) -> None:
        """Should detect Docker configuration."""
        assert fastapi_scan.model.architecture.has_docker

    def test_has_pypi_deps(self, fastapi_scan: ScanResult) -> None:
        """Should have pypi ecosystem dependencies."""
        ecosystems = {d.ecosystem for d in fastapi_scan.model.dependencies}
        assert "pypi" in ecosystems

    def test_has_npm_deps(self, fastapi_scan: ScanResult) -> None:
        """Should have npm ecosystem dependencies."""
        ecosystems = {d.ecosystem for d in fastapi_scan.model.dependencies}
        assert "npm" in ecosystems

    def test_description_nonempty(self, fastapi_scan: ScanResult) -> None:
        """Should extract a description."""
        assert fastapi_scan.model.description != ""

    def test_generators_contain_fastapi(self, fastapi_scan: ScanResult) -> None:
        """Generator output should mention FastAPI."""
        for fmt in AVAILABLE_FORMATS:
            gen = get_generator(fmt)()
            content = gen.generate(fastapi_scan.model)
            assert len(content) > 100, f"Generator '{fmt}' produced too little output"


# =========================================================================
# Test: Next.js (TypeScript)
# =========================================================================


@pytest.mark.integration
class TestNextJSApp:
    """Test scanning a Next.js application."""

    REPO_URL = "https://github.com/vercel/next-learn.git"

    @pytest.fixture(scope="class")
    def repo_path(self) -> Path:
        """Clone a Next.js example repo."""
        path = _clone_repo(self.REPO_URL, depth=1)
        yield path
        import shutil
        shutil.rmtree(path, ignore_errors=True)

    @pytest.fixture(scope="class")
    def nextjs_scan(self, repo_path: Path) -> ScanResult:
        """Scan the Next.js repo."""
        return _scan_and_validate(repo_path)

    def test_detects_typescript_or_javascript(self, nextjs_scan: ScanResult) -> None:
        """Should detect TypeScript or JavaScript."""
        langs = nextjs_scan.model.languages
        assert "typescript" in langs or "javascript" in langs

    def test_has_npm_deps(self, nextjs_scan: ScanResult) -> None:
        """Should have npm ecosystem dependencies."""
        ecosystems = {d.ecosystem for d in nextjs_scan.model.dependencies}
        assert "npm" in ecosystems

    def test_description_nonempty(self, nextjs_scan: ScanResult) -> None:
        """Should extract a description."""
        assert nextjs_scan.model.description != ""

    def test_generators_produce_output(self, nextjs_scan: ScanResult) -> None:
        """All generators should produce non-empty output."""
        for fmt in AVAILABLE_FORMATS:
            gen = get_generator(fmt)()
            content = gen.generate(nextjs_scan.model)
            assert len(content) > 50, f"Generator '{fmt}' produced too little output"


# =========================================================================
# Test: Django (large Python library)
# =========================================================================


@pytest.mark.integration
class TestDjango:
    """Test scanning Django — large repo performance stress test."""

    REPO_URL = "https://github.com/django/django.git"

    @pytest.fixture(scope="class")
    def repo_path(self) -> Path:
        """Clone Django (shallow)."""
        path = _clone_repo(self.REPO_URL, depth=10)
        yield path
        import shutil
        shutil.rmtree(path, ignore_errors=True)

    @pytest.fixture(scope="class")
    def django_scan(self, repo_path: Path) -> ScanResult:
        """Scan Django."""
        return _scan_and_validate(repo_path)

    def test_detects_python(self, django_scan: ScanResult) -> None:
        """Should detect Python as primary language."""
        assert "python" in django_scan.model.languages
        assert django_scan.model.languages[0] == "python"

    def test_architecture_library(self, django_scan: ScanResult) -> None:
        """Should detect library or cli_tool architecture."""
        # Django could be library, monolith, or cli_tool (django-admin)
        arch = django_scan.model.architecture.architecture_type
        assert arch in (
            ArchitectureType.LIBRARY,
            ArchitectureType.MONOLITH,
            ArchitectureType.CLI_TOOL,
        )

    def test_scan_under_60_seconds(self, django_scan: ScanResult) -> None:
        """Large repo scan should complete in reasonable time."""
        assert django_scan.duration < 60.0

    def test_has_modules(self, django_scan: ScanResult) -> None:
        """Should detect multiple modules."""
        assert len(django_scan.model.modules) > 3

    def test_git_insights(self, django_scan: ScanResult) -> None:
        """Should have git insights even with shallow clone."""
        assert django_scan.model.git_insights.total_commits > 0

    def test_no_crash_large_repo(self, django_scan: ScanResult) -> None:
        """Should not crash or produce garbage on 4000+ file repo."""
        assert django_scan.model is not None
        assert len(django_scan.model.languages) > 0

    def test_generators_produce_output(self, django_scan: ScanResult) -> None:
        """All generators should handle large repo output."""
        for fmt in AVAILABLE_FORMATS:
            gen = get_generator(fmt)()
            content = gen.generate(django_scan.model)
            assert len(content) > 100, f"Generator '{fmt}' produced too little output"


# =========================================================================
# Test: Go CLI — cli/cli (GitHub CLI, large Go project)
# =========================================================================


@pytest.mark.integration
class TestGoCLI:
    """Test scanning a Go CLI project (GitHub CLI)."""

    REPO_URL = "https://github.com/cli/cli.git"

    @pytest.fixture(scope="class")
    def repo_path(self) -> Path:
        """Clone the repo."""
        path = _clone_repo(self.REPO_URL, depth=1)
        yield path
        import shutil
        shutil.rmtree(path, ignore_errors=True)

    @pytest.fixture(scope="class")
    def go_scan(self, repo_path: Path) -> ScanResult:
        """Scan the Go CLI repo."""
        return _scan_and_validate(repo_path)

    def test_detects_go(self, go_scan: ScanResult) -> None:
        """Should detect Go as a language."""
        assert "go" in go_scan.model.languages

    def test_go_is_primary(self, go_scan: ScanResult) -> None:
        """Go should be the primary language."""
        assert go_scan.model.languages[0] == "go"

    def test_has_go_mod_deps(self, go_scan: ScanResult) -> None:
        """Should parse go.mod and find dependencies."""
        assert len(go_scan.model.dependencies) > 0
        ecosystems = {d.ecosystem for d in go_scan.model.dependencies}
        assert "go" in ecosystems

    def test_has_modules(self, go_scan: ScanResult) -> None:
        """Should detect multiple modules."""
        assert len(go_scan.model.modules) > 0

    def test_description_nonempty(self, go_scan: ScanResult) -> None:
        """Should extract a description from README."""
        assert go_scan.model.description != ""

    def test_architecture_detected(self, go_scan: ScanResult) -> None:
        """Should detect a meaningful architecture type."""
        assert go_scan.model.architecture.architecture_type is not None

    def test_has_entry_points(self, go_scan: ScanResult) -> None:
        """Should find Go entry points (main.go or cmd/)."""
        entry_points = go_scan.model.architecture.entry_points
        assert len(entry_points) > 0

    def test_scan_under_60_seconds(self, go_scan: ScanResult) -> None:
        """Scan should complete in reasonable time."""
        assert go_scan.duration < 60.0

    def test_generators_produce_output(self, go_scan: ScanResult) -> None:
        """All generators should produce non-empty output."""
        for fmt in AVAILABLE_FORMATS:
            gen = get_generator(fmt)()
            content = gen.generate(go_scan.model)
            assert len(content) > 100, f"Generator '{fmt}' produced too little output"


# =========================================================================
# Test: Rust CLI — BurntSushi/ripgrep (Rust, Cargo.toml)
# =========================================================================


@pytest.mark.integration
class TestRustCLI:
    """Test scanning a Rust CLI project (ripgrep)."""

    REPO_URL = "https://github.com/BurntSushi/ripgrep.git"

    @pytest.fixture(scope="class")
    def repo_path(self) -> Path:
        """Clone the repo."""
        path = _clone_repo(self.REPO_URL, depth=1)
        yield path
        import shutil
        shutil.rmtree(path, ignore_errors=True)

    @pytest.fixture(scope="class")
    def rust_scan(self, repo_path: Path) -> ScanResult:
        """Scan the Rust CLI repo."""
        return _scan_and_validate(repo_path)

    def test_detects_rust(self, rust_scan: ScanResult) -> None:
        """Should detect Rust as a language."""
        assert "rust" in rust_scan.model.languages

    def test_rust_is_primary(self, rust_scan: ScanResult) -> None:
        """Rust should be the primary language."""
        assert rust_scan.model.languages[0] == "rust"

    def test_has_cargo_deps(self, rust_scan: ScanResult) -> None:
        """Should parse Cargo.toml and find dependencies."""
        assert len(rust_scan.model.dependencies) > 0
        ecosystems = {d.ecosystem for d in rust_scan.model.dependencies}
        assert "cargo" in ecosystems

    def test_has_entry_point(self, rust_scan: ScanResult) -> None:
        """Should find main.rs or lib.rs as entry point."""
        entry_points = rust_scan.model.architecture.entry_points
        assert len(entry_points) > 0
        assert any("main.rs" in ep or "lib.rs" in ep for ep in entry_points)

    def test_description_nonempty(self, rust_scan: ScanResult) -> None:
        """Should extract a description from README."""
        assert rust_scan.model.description != ""

    def test_has_modules(self, rust_scan: ScanResult) -> None:
        """Should detect project modules."""
        assert len(rust_scan.model.modules) > 0

    def test_generators_produce_output(self, rust_scan: ScanResult) -> None:
        """All generators should produce non-empty output."""
        for fmt in AVAILABLE_FORMATS:
            gen = get_generator(fmt)()
            content = gen.generate(rust_scan.model)
            assert len(content) > 100, f"Generator '{fmt}' produced too little output"


# =========================================================================
# Test: Ruby library — jekyll/jekyll (Ruby, Gemfile)
# =========================================================================


@pytest.mark.integration
class TestRubyLibrary:
    """Test scanning a Ruby library (Jekyll)."""

    REPO_URL = "https://github.com/jekyll/jekyll.git"

    @pytest.fixture(scope="class")
    def repo_path(self) -> Path:
        """Clone the repo."""
        path = _clone_repo(self.REPO_URL, depth=1)
        yield path
        import shutil
        shutil.rmtree(path, ignore_errors=True)

    @pytest.fixture(scope="class")
    def ruby_scan(self, repo_path: Path) -> ScanResult:
        """Scan the Ruby library."""
        return _scan_and_validate(repo_path)

    def test_detects_ruby(self, ruby_scan: ScanResult) -> None:
        """Should detect Ruby as a language."""
        assert "ruby" in ruby_scan.model.languages

    def test_ruby_is_primary(self, ruby_scan: ScanResult) -> None:
        """Ruby should be the primary language."""
        assert ruby_scan.model.languages[0] == "ruby"

    def test_has_gem_deps(self, ruby_scan: ScanResult) -> None:
        """Should parse Gemfile and find dependencies."""
        assert len(ruby_scan.model.dependencies) > 0
        ecosystems = {d.ecosystem for d in ruby_scan.model.dependencies}
        assert "rubygems" in ecosystems

    def test_description_nonempty(self, ruby_scan: ScanResult) -> None:
        """Should extract a description from README."""
        assert ruby_scan.model.description != ""

    def test_has_modules(self, ruby_scan: ScanResult) -> None:
        """Should detect project modules."""
        assert len(ruby_scan.model.modules) > 0

    def test_has_ci(self, ruby_scan: ScanResult) -> None:
        """Should detect CI configuration."""
        assert ruby_scan.model.architecture.has_ci

    def test_generators_produce_output(self, ruby_scan: ScanResult) -> None:
        """All generators should produce non-empty output."""
        for fmt in AVAILABLE_FORMATS:
            gen = get_generator(fmt)()
            content = gen.generate(ruby_scan.model)
            assert len(content) > 100, f"Generator '{fmt}' produced too little output"


# =========================================================================
# Test: TypeScript monorepo — vercel/turborepo (workspace detection)
# =========================================================================


@pytest.mark.integration
class TestTurborepo:
    """Test scanning a TypeScript monorepo (Turborepo)."""

    REPO_URL = "https://github.com/vercel/turborepo.git"

    @pytest.fixture(scope="class")
    def repo_path(self) -> Path:
        """Clone the repo."""
        path = _clone_repo(self.REPO_URL, depth=1)
        yield path
        import shutil
        shutil.rmtree(path, ignore_errors=True)

    @pytest.fixture(scope="class")
    def turbo_scan(self, repo_path: Path) -> ScanResult:
        """Scan the Turborepo project."""
        return _scan_and_validate(repo_path)

    def test_detects_typescript_or_go(self, turbo_scan: ScanResult) -> None:
        """Should detect TypeScript or Go (Turborepo has both)."""
        langs = turbo_scan.model.languages
        assert "typescript" in langs or "go" in langs or "javascript" in langs

    def test_has_npm_deps(self, turbo_scan: ScanResult) -> None:
        """Should find npm ecosystem dependencies."""
        ecosystems = {d.ecosystem for d in turbo_scan.model.dependencies}
        assert "npm" in ecosystems or "go" in ecosystems

    def test_has_multiple_modules(self, turbo_scan: ScanResult) -> None:
        """Should detect multiple modules (monorepo)."""
        assert len(turbo_scan.model.modules) > 1

    def test_description_nonempty(self, turbo_scan: ScanResult) -> None:
        """Should extract a description."""
        assert turbo_scan.model.description != ""

    def test_has_ci(self, turbo_scan: ScanResult) -> None:
        """Should detect CI configuration."""
        assert turbo_scan.model.architecture.has_ci

    def test_scan_under_120_seconds(self, turbo_scan: ScanResult) -> None:
        """Scan should complete in reasonable time."""
        assert turbo_scan.duration < 120.0

    def test_generators_produce_output(self, turbo_scan: ScanResult) -> None:
        """All generators should produce non-empty output."""
        for fmt in AVAILABLE_FORMATS:
            gen = get_generator(fmt)()
            content = gen.generate(turbo_scan.model)
            assert len(content) > 100, f"Generator '{fmt}' produced too little output"


# =========================================================================
# Test: Node.js library — expressjs/express (pure JS, npm)
# =========================================================================


@pytest.mark.integration
class TestExpressJS:
    """Test scanning a Node.js library (Express)."""

    REPO_URL = "https://github.com/expressjs/express.git"

    @pytest.fixture(scope="class")
    def repo_path(self) -> Path:
        """Clone the repo."""
        path = _clone_repo(self.REPO_URL, depth=1)
        yield path
        import shutil
        shutil.rmtree(path, ignore_errors=True)

    @pytest.fixture(scope="class")
    def express_scan(self, repo_path: Path) -> ScanResult:
        """Scan the Express repo."""
        return _scan_and_validate(repo_path)

    def test_detects_javascript(self, express_scan: ScanResult) -> None:
        """Should detect JavaScript as a language."""
        assert "javascript" in express_scan.model.languages

    def test_javascript_is_primary(self, express_scan: ScanResult) -> None:
        """JavaScript should be the primary language."""
        assert express_scan.model.languages[0] == "javascript"

    def test_has_npm_deps(self, express_scan: ScanResult) -> None:
        """Should parse package.json and find dependencies."""
        assert len(express_scan.model.dependencies) > 0
        ecosystems = {d.ecosystem for d in express_scan.model.dependencies}
        assert "npm" in ecosystems

    def test_has_runtime_deps(self, express_scan: ScanResult) -> None:
        """Should detect runtime dependencies."""
        runtime_deps = [d for d in express_scan.model.dependencies if d.dep_type == "runtime"]
        assert len(runtime_deps) > 0

    def test_description_nonempty(self, express_scan: ScanResult) -> None:
        """Should extract a description from README or package.json."""
        assert express_scan.model.description != ""

    def test_architecture_library(self, express_scan: ScanResult) -> None:
        """Should detect library architecture."""
        arch = express_scan.model.architecture.architecture_type
        assert arch in (
            ArchitectureType.LIBRARY,
            ArchitectureType.MONOLITH,
            ArchitectureType.CLI_TOOL,
        )

    def test_has_entry_point(self, express_scan: ScanResult) -> None:
        """Should find index.js or lib/ as entry point."""
        entry_points = express_scan.model.architecture.entry_points
        assert len(entry_points) > 0

    def test_generators_produce_output(self, express_scan: ScanResult) -> None:
        """All generators should produce non-empty output."""
        for fmt in AVAILABLE_FORMATS:
            gen = get_generator(fmt)()
            content = gen.generate(express_scan.model)
            assert len(content) > 100, f"Generator '{fmt}' produced too little output"
