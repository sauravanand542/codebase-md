"""Convention inference for codebase scanning.

Analyzes source files to detect naming conventions, import styles,
file organization patterns, test conventions, and design patterns.
Uses tree-sitter for AST-based analysis with regex fallback.
"""

from __future__ import annotations

import re
from pathlib import Path

from codebase_md.model.convention import ConventionSet, ImportStyle, NamingConvention
from codebase_md.scanner.ast_analyzer import _get_js_parser, _get_python_parser, _get_ts_parser
from codebase_md.scanner.language_detector import DEFAULT_EXCLUDES, EXTENSION_MAP, _should_exclude

# Maximum number of files to sample for convention detection
_MAX_SAMPLE_FILES = 50

# Maximum file size to parse (skip very large files)
_MAX_FILE_SIZE = 100_000  # 100 KB

# Languages we do convention analysis on
_ANALYZABLE_LANGUAGES: set[str] = {"python", "javascript", "typescript"}

# Extensions for analyzable languages
_ANALYZABLE_EXTENSIONS: set[str] = {
    ext for ext, lang in EXTENSION_MAP.items() if lang in _ANALYZABLE_LANGUAGES
}


class ConventionInferenceError(Exception):
    """Raised when convention inference fails."""


# --- Naming Convention Detection ---

# Regex patterns for naming styles
_SNAKE_CASE_RE = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$")
_CAMEL_CASE_RE = re.compile(r"^[a-z][a-zA-Z0-9]*$")
_PASCAL_CASE_RE = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
_KEBAB_CASE_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
_UPPER_SNAKE_RE = re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$")


def _classify_name(name: str) -> NamingConvention | None:
    """Classify a single identifier name into a naming convention.

    Args:
        name: The identifier name to classify.

    Returns:
        The detected naming convention, or None if unclassifiable.
    """
    if len(name) <= 1:
        return None
    if name.startswith("_"):
        name = name.lstrip("_")
        if not name:
            return None

    # Skip ALL_CAPS constants — they're convention-neutral
    if _UPPER_SNAKE_RE.match(name):
        return None

    if _SNAKE_CASE_RE.match(name):
        return NamingConvention.SNAKE_CASE
    if _CAMEL_CASE_RE.match(name):
        return NamingConvention.CAMEL_CASE
    if _PASCAL_CASE_RE.match(name):
        return NamingConvention.PASCAL_CASE
    if _KEBAB_CASE_RE.match(name):
        return NamingConvention.KEBAB_CASE

    return None


def _detect_naming_from_identifiers(identifiers: list[str]) -> NamingConvention:
    """Determine the dominant naming convention from a list of identifiers.

    Args:
        identifiers: List of identifier names to analyze.

    Returns:
        The most common naming convention, or MIXED if no clear winner.
    """
    counts: dict[NamingConvention, int] = {}

    for name in identifiers:
        convention = _classify_name(name)
        if convention is not None:
            counts[convention] = counts.get(convention, 0) + 1

    if not counts:
        return NamingConvention.MIXED

    total = sum(counts.values())
    dominant = max(counts, key=lambda k: counts[k])
    dominant_ratio = counts[dominant] / total

    # If one convention covers >70% of names, it's dominant
    if dominant_ratio > 0.7:
        return dominant
    return NamingConvention.MIXED


# --- Import Style Detection ---


def _detect_import_style_python(file_path: Path) -> ImportStyle | None:
    """Detect import style from a Python file using regex.

    Args:
        file_path: Path to the Python file.

    Returns:
        The detected import style, or None if no imports found.
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None

    absolute_count = 0
    relative_count = 0

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("from ."):
            relative_count += 1
        elif stripped.startswith("from ") or stripped.startswith("import "):
            absolute_count += 1

    if absolute_count == 0 and relative_count == 0:
        return None
    if relative_count == 0:
        return ImportStyle.ABSOLUTE
    if absolute_count == 0:
        return ImportStyle.RELATIVE
    return ImportStyle.MIXED


def _detect_import_style_js_ts(file_path: Path) -> ImportStyle | None:
    """Detect import style from a JS/TS file using regex.

    Args:
        file_path: Path to the JS/TS file.

    Returns:
        The detected import style, or None if no imports found.
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return None

    absolute_count = 0
    relative_count = 0

    # Match:  import ... from './...'  or  import ... from '../...'
    # vs:     import ... from 'package'  or import ... from '@scope/package'
    import_from_re = re.compile(r"""(?:from|require\()\s*['"]([^'"]+)['"]""")

    for match in import_from_re.finditer(content):
        specifier = match.group(1)
        if specifier.startswith("."):
            relative_count += 1
        else:
            absolute_count += 1

    if absolute_count == 0 and relative_count == 0:
        return None
    if relative_count == 0:
        return ImportStyle.ABSOLUTE
    if absolute_count == 0:
        return ImportStyle.RELATIVE
    return ImportStyle.MIXED


# --- File Organization Detection ---


def _detect_file_organization(root_path: Path, exclude: list[str]) -> str:
    """Detect the file organization pattern of the project.

    Looks for patterns like:
    - 'feature-based': src/auth/, src/users/, src/payments/
    - 'layer-based': controllers/, services/, models/, routes/
    - 'flat': all files in src/ with no subdirectories

    Args:
        root_path: Project root directory.
        exclude: Directories to skip.

    Returns:
        Organization pattern string.
    """
    layer_indicators = {
        "controllers",
        "services",
        "models",
        "views",
        "routes",
        "handlers",
        "middleware",
        "repositories",
        "entities",
        "dtos",
    }

    feature_indicators = {
        "auth",
        "users",
        "payments",
        "orders",
        "products",
        "dashboard",
        "settings",
        "profile",
        "notifications",
    }

    top_dirs: set[str] = set()
    src_subdirs: set[str] = set()

    for item in root_path.iterdir():
        if item.is_dir() and not _should_exclude(item.relative_to(root_path), exclude):
            top_dirs.add(item.name.lower())

    # Also check src/ subdirectories
    for src_name in ("src", "lib", "app"):
        src_dir = root_path / src_name
        if src_dir.is_dir():
            for item in src_dir.iterdir():
                if item.is_dir() and not _should_exclude(item.relative_to(root_path), exclude):
                    src_subdirs.add(item.name.lower())

    all_dirs = top_dirs | src_subdirs
    layer_matches = all_dirs & layer_indicators
    feature_matches = all_dirs & feature_indicators

    if len(layer_matches) >= 2:
        return "layer-based"
    if len(feature_matches) >= 2:
        return "feature-based"
    if src_subdirs:
        return "modular"

    return "flat"


# --- Test Pattern Detection ---


def _detect_test_pattern(root_path: Path, exclude: list[str]) -> str:
    """Detect the test file naming and location pattern.

    Args:
        root_path: Project root directory.
        exclude: Directories to skip.

    Returns:
        Test pattern string, e.g. 'test_*.py', '*.test.ts', '*.spec.js'.
    """
    patterns: dict[str, int] = {}

    for file_path in root_path.rglob("*"):
        if not file_path.is_file():
            continue
        relative = file_path.relative_to(root_path)
        if _should_exclude(relative, exclude):
            continue

        name = file_path.name
        if name.startswith("test_") and name.endswith(".py"):
            patterns["test_*.py"] = patterns.get("test_*.py", 0) + 1
        elif name.endswith("_test.py"):
            patterns["*_test.py"] = patterns.get("*_test.py", 0) + 1
        elif name.endswith(".test.ts") or name.endswith(".test.tsx"):
            patterns["*.test.ts"] = patterns.get("*.test.ts", 0) + 1
        elif name.endswith(".spec.ts") or name.endswith(".spec.tsx"):
            patterns["*.spec.ts"] = patterns.get("*.spec.ts", 0) + 1
        elif name.endswith(".test.js") or name.endswith(".test.jsx"):
            patterns["*.test.js"] = patterns.get("*.test.js", 0) + 1
        elif name.endswith(".spec.js") or name.endswith(".spec.jsx"):
            patterns["*.spec.js"] = patterns.get("*.spec.js", 0) + 1
        elif name.endswith("_test.go"):
            patterns["*_test.go"] = patterns.get("*_test.go", 0) + 1

    if not patterns:
        return ""

    return max(patterns, key=lambda k: patterns[k])


# --- Design Pattern Detection ---


def _detect_design_patterns(root_path: Path, exclude: list[str]) -> list[str]:
    """Detect design patterns from directory and file names.

    Looks for common patterns like repository, service, controller,
    factory, middleware, decorator, observer, etc.

    Args:
        root_path: Project root directory.
        exclude: Directories to skip.

    Returns:
        List of detected pattern names.
    """
    pattern_indicators: dict[str, list[str]] = {
        "repository": ["repository", "repositories", "repo"],
        "service": ["service", "services"],
        "controller": ["controller", "controllers"],
        "factory": ["factory", "factories"],
        "middleware": ["middleware", "middlewares"],
        "decorator": ["decorator", "decorators"],
        "observer": ["observer", "observers", "listener", "listeners"],
        "strategy": ["strategy", "strategies"],
        "adapter": ["adapter", "adapters"],
        "command": ["command", "commands"],
        "provider": ["provider", "providers"],
        "guard": ["guard", "guards"],
        "interceptor": ["interceptor", "interceptors"],
        "pipe": ["pipe", "pipes"],
        "resolver": ["resolver", "resolvers"],
        "gateway": ["gateway", "gateways"],
        "module": ["module", "modules"],
        "dto": ["dto", "dtos"],
        "entity": ["entity", "entities"],
        "model": ["model", "models"],
        "view": ["view", "views"],
        "router": ["router", "routers", "routes"],
        "handler": ["handler", "handlers"],
        "helper": ["helper", "helpers", "util", "utils", "utility", "utilities"],
    }

    found_names: set[str] = set()

    for file_path in root_path.rglob("*"):
        relative = file_path.relative_to(root_path)
        if _should_exclude(relative, exclude):
            continue

        name_lower = file_path.stem.lower()
        for pattern_name, indicators in pattern_indicators.items():
            for indicator in indicators:
                if indicator in name_lower or (
                    file_path.is_dir() and file_path.name.lower() in indicators
                ):
                    found_names.add(pattern_name)
                    break

    return sorted(found_names)


# --- AST-based Identifier Extraction ---


def _extract_identifiers_python(file_path: Path) -> list[str]:
    """Extract function and variable identifiers from a Python file using tree-sitter.

    Falls back to regex if tree-sitter is not available.

    Args:
        file_path: Path to the Python file.

    Returns:
        List of identifier names.
    """
    try:
        content = file_path.read_bytes()
    except OSError:
        return []

    if len(content) > _MAX_FILE_SIZE:
        return []

    try:
        return _extract_identifiers_python_treesitter(content)
    except Exception:
        return _extract_identifiers_python_regex(content.decode("utf-8", errors="ignore"))


def _extract_identifiers_python_treesitter(content: bytes) -> list[str]:
    """Extract Python identifiers using tree-sitter.

    Args:
        content: Raw file content as bytes.

    Returns:
        List of identifier names (function names, variable names).
    """
    _lang, parser = _get_python_parser()
    tree = parser.parse(content)

    identifiers: list[str] = []
    for node in tree.root_node.children:
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node and name_node.text is not None:
                identifiers.append(name_node.text.decode("utf-8"))
        elif node.type == "class_definition":
            # Don't count class names for naming (they're always PascalCase)
            # But collect method names
            body = node.child_by_field_name("body")
            if body:
                for child in body.children:
                    if child.type == "function_definition":
                        name_node = child.child_by_field_name("name")
                        if name_node and name_node.text is not None:
                            identifiers.append(name_node.text.decode("utf-8"))
        elif node.type == "expression_statement":
            # Top-level assignments
            if node.children and node.children[0].type == "assignment":
                left = node.children[0].child_by_field_name("left")
                if left and left.type == "identifier" and left.text is not None:
                    identifiers.append(left.text.decode("utf-8"))

    return identifiers


def _extract_identifiers_python_regex(content: str) -> list[str]:
    """Extract Python identifiers using regex fallback.

    Args:
        content: File content as string.

    Returns:
        List of identifier names.
    """
    identifiers: list[str] = []

    # Function definitions
    for match in re.finditer(r"^def\s+(\w+)", content, re.MULTILINE):
        identifiers.append(match.group(1))

    # Top-level assignments
    for match in re.finditer(r"^([a-zA-Z_]\w*)\s*=", content, re.MULTILINE):
        identifiers.append(match.group(1))

    return identifiers


def _extract_identifiers_js_ts(file_path: Path) -> list[str]:
    """Extract identifiers from a JavaScript/TypeScript file using tree-sitter.

    Falls back to regex if tree-sitter is not available.

    Args:
        file_path: Path to the JS/TS file.

    Returns:
        List of identifier names.
    """
    try:
        content = file_path.read_bytes()
    except OSError:
        return []

    if len(content) > _MAX_FILE_SIZE:
        return []

    suffix = file_path.suffix.lower()
    is_typescript = suffix in {".ts", ".tsx"}

    try:
        return _extract_identifiers_js_ts_treesitter(content, is_typescript)
    except Exception:
        return _extract_identifiers_js_ts_regex(content.decode("utf-8", errors="ignore"))


def _extract_identifiers_js_ts_treesitter(content: bytes, is_typescript: bool) -> list[str]:
    """Extract JS/TS identifiers using tree-sitter.

    Args:
        content: Raw file content as bytes.
        is_typescript: Whether the file is TypeScript.

    Returns:
        List of identifier names.
    """
    if is_typescript:
        _lang, parser = _get_ts_parser()
    else:
        _lang, parser = _get_js_parser()

    tree = parser.parse(content)

    identifiers: list[str] = []
    _collect_js_ts_identifiers(tree.root_node, identifiers)
    return identifiers


def _collect_js_ts_identifiers(node: object, identifiers: list[str]) -> None:
    """Recursively collect identifiers from a JS/TS AST node.

    Handles export statements by unwrapping them.

    Args:
        node: tree-sitter Node to traverse.
        identifiers: List to append found names to (mutated).
    """
    # Use getattr for type safety since tree-sitter node type varies
    node_type = getattr(node, "type", "")
    children = getattr(node, "children", [])

    if node_type == "export_statement":
        # Unwrap exports — look at the declaration inside
        for child in children:
            _collect_js_ts_identifiers(child, identifiers)
        return

    if node_type in ("function_declaration", "function"):
        name_node = getattr(node, "child_by_field_name", lambda _: None)("name")
        if name_node:
            identifiers.append(name_node.text.decode("utf-8"))
    elif node_type == "lexical_declaration":
        # const/let/var — look for variable_declarator children
        for child in children:
            if getattr(child, "type", "") == "variable_declarator":
                name_node = getattr(child, "child_by_field_name", lambda _: None)("name")
                if name_node:
                    identifiers.append(name_node.text.decode("utf-8"))
    elif node_type == "variable_declaration":
        for child in children:
            if getattr(child, "type", "") == "variable_declarator":
                name_node = getattr(child, "child_by_field_name", lambda _: None)("name")
                if name_node:
                    identifiers.append(name_node.text.decode("utf-8"))
    elif node_type == "class_declaration":
        # Collect method names from class body
        body = getattr(node, "child_by_field_name", lambda _: None)("body")
        if body:
            for child in getattr(body, "children", []):
                if getattr(child, "type", "") == "method_definition":
                    name_node = getattr(child, "child_by_field_name", lambda _: None)("name")
                    if name_node:
                        identifiers.append(name_node.text.decode("utf-8"))


def _extract_identifiers_js_ts_regex(content: str) -> list[str]:
    """Extract JS/TS identifiers using regex fallback.

    Args:
        content: File content as string.

    Returns:
        List of identifier names.
    """
    identifiers: list[str] = []

    # function declarations
    for match in re.finditer(r"\bfunction\s+(\w+)", content):
        identifiers.append(match.group(1))

    # const/let/var declarations
    for match in re.finditer(r"\b(?:const|let|var)\s+(\w+)", content):
        identifiers.append(match.group(1))

    return identifiers


# --- File Organization Naming (file names to kebab/snake) ---


def _detect_file_naming(root_path: Path, exclude: list[str]) -> NamingConvention | None:
    """Detect naming convention used for file names.

    Args:
        root_path: Project root.
        exclude: Exclusions.

    Returns:
        Naming convention for files, or None if undetermined.
    """
    file_stems: list[str] = []

    for file_path in root_path.rglob("*"):
        if not file_path.is_file():
            continue
        relative = file_path.relative_to(root_path)
        if _should_exclude(relative, exclude):
            continue
        if file_path.suffix.lower() not in _ANALYZABLE_EXTENSIONS:
            continue

        stem = file_path.stem
        # Skip index/main/app — they're too generic
        if stem.lower() in {"index", "main", "app", "__init__", "setup", "conftest"}:
            continue
        file_stems.append(stem)

    if not file_stems:
        return None

    return _detect_naming_from_identifiers(file_stems)


# --- Main Entry Point ---


def infer_conventions(
    root_path: Path,
    exclude: list[str] | None = None,
) -> ConventionSet:
    """Infer coding conventions from the project source files.

    Samples up to _MAX_SAMPLE_FILES source files and analyzes them
    for naming conventions, import style, file organization, test
    patterns, and design patterns.

    Args:
        root_path: Root directory of the project.
        exclude: Directory/file names to skip. Uses DEFAULT_EXCLUDES if None.

    Returns:
        ConventionSet with detected conventions.

    Raises:
        ConventionInferenceError: If root_path is invalid.
    """
    if not root_path.exists():
        raise ConventionInferenceError(f"Path does not exist: {root_path}")
    if not root_path.is_dir():
        raise ConventionInferenceError(f"Path is not a directory: {root_path}")

    exclude_list = exclude if exclude is not None else DEFAULT_EXCLUDES

    # Collect sample files
    sample_files = _collect_sample_files(root_path, exclude_list)

    # Extract identifiers from all sample files
    all_identifiers: list[str] = []
    import_styles: list[ImportStyle] = []

    for file_path in sample_files:
        suffix = file_path.suffix.lower()
        lang = EXTENSION_MAP.get(suffix, "")

        if lang == "python":
            all_identifiers.extend(_extract_identifiers_python(file_path))
            style = _detect_import_style_python(file_path)
            if style is not None:
                import_styles.append(style)
        elif lang in ("javascript", "typescript"):
            all_identifiers.extend(_extract_identifiers_js_ts(file_path))
            style = _detect_import_style_js_ts(file_path)
            if style is not None:
                import_styles.append(style)

    # Determine naming convention
    naming = _detect_naming_from_identifiers(all_identifiers)

    # Determine import style (majority vote)
    if import_styles:
        style_counts: dict[ImportStyle, int] = {}
        for s in import_styles:
            style_counts[s] = style_counts.get(s, 0) + 1
        import_style = max(style_counts, key=lambda k: style_counts[k])
    else:
        import_style = ImportStyle.MIXED

    # File organization
    file_org = _detect_file_organization(root_path, exclude_list)

    # Test pattern
    test_pattern = _detect_test_pattern(root_path, exclude_list)

    # Design patterns
    patterns_used = _detect_design_patterns(root_path, exclude_list)

    return ConventionSet(
        naming=naming,
        file_org=file_org,
        import_style=import_style,
        test_pattern=test_pattern,
        patterns_used=patterns_used,
    )


def _collect_sample_files(root_path: Path, exclude: list[str]) -> list[Path]:
    """Collect a sample of source files for convention analysis.

    Prioritizes files in src/, lib/, app/ directories.
    Limits to _MAX_SAMPLE_FILES.

    Args:
        root_path: Project root.
        exclude: Exclusions.

    Returns:
        List of file paths to analyze.
    """
    files: list[Path] = []

    for file_path in root_path.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.is_symlink():
            continue
        relative = file_path.relative_to(root_path)
        if _should_exclude(relative, exclude):
            continue
        if file_path.suffix.lower() not in _ANALYZABLE_EXTENSIONS:
            continue
        try:
            if file_path.stat().st_size > _MAX_FILE_SIZE:
                continue
        except OSError:
            continue
        files.append(file_path)
        if len(files) >= _MAX_SAMPLE_FILES:
            break

    return files
