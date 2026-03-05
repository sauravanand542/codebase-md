"""Language detection for codebase scanning.

Walks the file tree, classifies files by extension, detects
programming languages and frameworks by marker files and configs.
"""

from __future__ import annotations

from pathlib import Path

EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".kt": "kotlin",
    ".rb": "ruby",
    ".php": "php",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".cs": "csharp",
    ".swift": "swift",
    ".m": "objective-c",
    ".scala": "scala",
    ".r": "r",
    ".R": "r",
    ".lua": "lua",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".ps1": "powershell",
    ".dart": "dart",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".hs": "haskell",
    ".ml": "ocaml",
    ".clj": "clojure",
    ".vue": "vue",
    ".svelte": "svelte",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".sql": "sql",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".xml": "xml",
    ".md": "markdown",
    ".proto": "protobuf",
    ".graphql": "graphql",
    ".gql": "graphql",
}

# Marker files that indicate a specific framework
FRAMEWORK_MARKERS: dict[str, dict[str, str]] = {
    # filename -> {language, framework}
    "next.config.js": {"language": "typescript", "framework": "nextjs"},
    "next.config.ts": {"language": "typescript", "framework": "nextjs"},
    "next.config.mjs": {"language": "typescript", "framework": "nextjs"},
    "nuxt.config.ts": {"language": "typescript", "framework": "nuxt"},
    "nuxt.config.js": {"language": "javascript", "framework": "nuxt"},
    "angular.json": {"language": "typescript", "framework": "angular"},
    "svelte.config.js": {"language": "svelte", "framework": "sveltekit"},
    "svelte.config.ts": {"language": "svelte", "framework": "sveltekit"},
    "remix.config.js": {"language": "typescript", "framework": "remix"},
    "astro.config.mjs": {"language": "typescript", "framework": "astro"},
    "gatsby-config.js": {"language": "javascript", "framework": "gatsby"},
    "gatsby-config.ts": {"language": "typescript", "framework": "gatsby"},
    "vite.config.ts": {"language": "typescript", "framework": "vite"},
    "vite.config.js": {"language": "javascript", "framework": "vite"},
    "webpack.config.js": {"language": "javascript", "framework": "webpack"},
    "tailwind.config.js": {"language": "javascript", "framework": "tailwind"},
    "tailwind.config.ts": {"language": "typescript", "framework": "tailwind"},
    "manage.py": {"language": "python", "framework": "django"},
    "Gemfile": {"language": "ruby", "framework": "rails"},
    "Cargo.toml": {"language": "rust", "framework": "rust"},
    "go.mod": {"language": "go", "framework": "go"},
    "build.gradle": {"language": "java", "framework": "gradle"},
    "build.gradle.kts": {"language": "kotlin", "framework": "gradle"},
    "pom.xml": {"language": "java", "framework": "maven"},
    "pubspec.yaml": {"language": "dart", "framework": "flutter"},
    "mix.exs": {"language": "elixir", "framework": "elixir"},
    "Makefile": {"language": "make", "framework": "make"},
    "CMakeLists.txt": {"language": "cmake", "framework": "cmake"},
    "docker-compose.yml": {"language": "yaml", "framework": "docker-compose"},
    "docker-compose.yaml": {"language": "yaml", "framework": "docker-compose"},
    "Dockerfile": {"language": "dockerfile", "framework": "docker"},
}

DEFAULT_EXCLUDES: list[str] = [
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    ".git",
    ".hg",
    ".svn",
    "dist",
    "build",
    ".next",
    ".nuxt",
    "target",
    "out",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "coverage",
    ".coverage",
    "htmlcov",
    ".eggs",
    "*.egg-info",
    ".idea",
    ".vscode",
    ".DS_Store",
]


class LanguageDetectionError(Exception):
    """Raised when language detection fails."""


def _should_exclude(path: Path, exclude: list[str]) -> bool:
    """Check if a path should be excluded from scanning.

    Args:
        path: Path to check.
        exclude: List of directory/file names to exclude.

    Returns:
        True if the path should be skipped.
    """
    for part in path.parts:
        if part in exclude:
            return True
        # Handle glob-like patterns (e.g. *.egg-info)
        for pattern in exclude:
            if "*" in pattern and path.match(pattern):
                return True
    return False


def detect_languages(
    root_path: Path,
    exclude: list[str] | None = None,
) -> list[str]:
    """Detect programming languages used in the project.

    Walks the file tree and classifies files by their extension.
    Returns a deduplicated list of language names sorted by file count
    (most common first).

    Args:
        root_path: Root directory of the project to scan.
        exclude: Directory/file names to skip. Uses DEFAULT_EXCLUDES if None.

    Returns:
        List of detected language names, sorted by prevalence.

    Raises:
        LanguageDetectionError: If root_path does not exist or is not a directory.
    """
    if not root_path.exists():
        raise LanguageDetectionError(f"Path does not exist: {root_path}")
    if not root_path.is_dir():
        raise LanguageDetectionError(f"Path is not a directory: {root_path}")

    exclude_list = exclude if exclude is not None else DEFAULT_EXCLUDES
    language_counts: dict[str, int] = {}

    try:
        for file_path in root_path.rglob("*"):
            try:
                if not file_path.is_file():
                    continue
                if file_path.is_symlink():
                    continue

                relative = file_path.relative_to(root_path)
                if _should_exclude(relative, exclude_list):
                    continue

                suffix = file_path.suffix.lower()
                language = EXTENSION_MAP.get(suffix)
                if language and language not in _NON_CODE_LANGUAGES:
                    language_counts[language] = language_counts.get(language, 0) + 1
            except (PermissionError, OSError):
                continue  # Skip individual unreadable files
    except PermissionError as e:
        raise LanguageDetectionError(f"Permission denied while scanning: {e}") from e

    # Sort by file count descending
    sorted_langs = sorted(language_counts.keys(), key=lambda k: language_counts[k], reverse=True)
    return sorted_langs


def detect_frameworks(
    root_path: Path,
    extra_dirs: list[Path] | None = None,
) -> list[dict[str, str]]:
    """Detect frameworks by checking for marker files in the project root.

    Also checks extra directories (e.g. monorepo sub-packages) for
    nested framework markers.

    Args:
        root_path: Root directory of the project to scan.
        extra_dirs: Additional directories to check for framework markers.

    Returns:
        List of dicts with 'language' and 'framework' keys for each
        detected framework.

    Raises:
        LanguageDetectionError: If root_path does not exist or is not a directory.
    """
    if not root_path.exists():
        raise LanguageDetectionError(f"Path does not exist: {root_path}")
    if not root_path.is_dir():
        raise LanguageDetectionError(f"Path is not a directory: {root_path}")

    detected: list[dict[str, str]] = []

    for marker_file, info in FRAMEWORK_MARKERS.items():
        if (root_path / marker_file).exists():
            detected.append(info)

    # Check extra directories for nested frameworks (monorepo sub-packages)
    if extra_dirs:
        for extra_dir in extra_dirs:
            if not extra_dir.is_dir():
                continue
            for marker_file, info in FRAMEWORK_MARKERS.items():
                if (extra_dir / marker_file).exists() and info not in detected:
                    detected.append(info)
            # Check nested package.json for JS/TS frameworks
            nested_pkg = extra_dir / "package.json"
            if nested_pkg.is_file():
                _detect_js_framework(nested_pkg, detected)
            # Check nested pyproject.toml for Python frameworks
            nested_pyproject = extra_dir / "pyproject.toml"
            if nested_pyproject.is_file():
                _detect_python_framework(nested_pyproject, detected)
            # Check nested requirements.txt for Python frameworks
            nested_reqs = extra_dir / "requirements.txt"
            if nested_reqs.is_file():
                _detect_python_framework_requirements(nested_reqs, detected)

    # Check pyproject.toml for Python frameworks
    pyproject = root_path / "pyproject.toml"
    if pyproject.is_file():
        _detect_python_framework(pyproject, detected)

    # Check requirements.txt for Python frameworks
    requirements = root_path / "requirements.txt"
    if requirements.is_file():
        _detect_python_framework_requirements(requirements, detected)

    # Check package.json for JS/TS frameworks
    package_json = root_path / "package.json"
    if package_json.is_file():
        _detect_js_framework(package_json, detected)

    return detected


def _detect_python_framework(pyproject_path: Path, detected: list[dict[str, str]]) -> None:
    """Detect Python frameworks from pyproject.toml dependencies.

    Args:
        pyproject_path: Path to pyproject.toml.
        detected: List to append detected frameworks to (mutated in place).
    """
    try:
        content = pyproject_path.read_text(encoding="utf-8").lower()
        _match_python_frameworks(content, detected)
    except OSError:
        pass  # Can't read file — skip


def _detect_python_framework_requirements(
    requirements_path: Path,
    detected: list[dict[str, str]],
) -> None:
    """Detect Python frameworks from requirements.txt.

    Args:
        requirements_path: Path to requirements.txt.
        detected: List to append detected frameworks to (mutated in place).
    """
    try:
        content = requirements_path.read_text(encoding="utf-8").lower()
        _match_python_frameworks(content, detected)
    except OSError:
        pass  # Can't read file — skip


def _match_python_frameworks(content: str, detected: list[dict[str, str]]) -> None:
    """Match known Python framework names against file content.

    Args:
        content: Lowercased file content to search.
        detected: List to append detected frameworks to (mutated in place).
    """
    python_frameworks = {
        "fastapi": "fastapi",
        "django": "django",
        "flask": "flask",
        "starlette": "starlette",
        "typer": "typer",
        "click": "click",
        "celery": "celery",
        "sqlalchemy": "sqlalchemy",
        "pytest": "pytest",
        "scrapy": "scrapy",
        "tornado": "tornado",
        "aiohttp": "aiohttp",
        "sanic": "sanic",
        "litestar": "litestar",
    }
    for dep, framework in python_frameworks.items():
        if dep in content:
            entry = {"language": "python", "framework": framework}
            if entry not in detected:
                detected.append(entry)


def _detect_js_framework(package_json_path: Path, detected: list[dict[str, str]]) -> None:
    """Detect JavaScript/TypeScript frameworks from package.json.

    Args:
        package_json_path: Path to package.json.
        detected: List to append detected frameworks to (mutated in place).
    """
    import json

    try:
        data = json.loads(package_json_path.read_text(encoding="utf-8"))
        all_deps: dict[str, str] = {}
        all_deps.update(data.get("dependencies", {}))
        all_deps.update(data.get("devDependencies", {}))

        js_frameworks: dict[str, tuple[str, str]] = {
            "react": ("javascript", "react"),
            "react-dom": ("javascript", "react"),
            "vue": ("javascript", "vue"),
            "svelte": ("javascript", "svelte"),
            "@angular/core": ("typescript", "angular"),
            "express": ("javascript", "express"),
            "fastify": ("javascript", "fastify"),
            "koa": ("javascript", "koa"),
            "hono": ("typescript", "hono"),
            "next": ("typescript", "nextjs"),
            "nuxt": ("typescript", "nuxt"),
            "gatsby": ("javascript", "gatsby"),
            "remix": ("typescript", "remix"),
            "astro": ("typescript", "astro"),
            "jest": ("javascript", "jest"),
            "vitest": ("javascript", "vitest"),
            "mocha": ("javascript", "mocha"),
            "tailwindcss": ("javascript", "tailwind"),
            "prisma": ("javascript", "prisma"),
            "drizzle-orm": ("typescript", "drizzle"),
            "typeorm": ("typescript", "typeorm"),
            "sequelize": ("javascript", "sequelize"),
            "mongoose": ("javascript", "mongoose"),
        }
        for dep, (lang, framework) in js_frameworks.items():
            if dep in all_deps:
                entry = {"language": lang, "framework": framework}
                if entry not in detected:
                    detected.append(entry)
    except (OSError, json.JSONDecodeError):
        pass  # Can't read or parse — skip


def get_file_count(root_path: Path, language: str, exclude: list[str] | None = None) -> int:
    """Count files of a specific language in the project.

    Args:
        root_path: Root directory of the project.
        language: Language name to count files for.
        exclude: Directory/file names to skip.

    Returns:
        Number of files matching the language.
    """
    exclude_list = exclude if exclude is not None else DEFAULT_EXCLUDES
    count = 0

    # Build reverse map: language -> extensions
    lang_extensions = [ext for ext, lang in EXTENSION_MAP.items() if lang == language]

    for file_path in root_path.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.is_symlink():
            continue
        relative = file_path.relative_to(root_path)
        if _should_exclude(relative, exclude_list):
            continue
        if file_path.suffix.lower() in lang_extensions:
            count += 1

    return count


# Languages that are config/data, not "code" — excluded from language detection
_NON_CODE_LANGUAGES: set[str] = {
    "yaml",
    "toml",
    "json",
    "xml",
    "markdown",
    "html",
    "css",
    "scss",
    "sass",
    "less",
    "sql",
}
