"""AST-based code analysis for codebase scanning.

Uses tree-sitter to parse source files and extract exports (functions,
classes, constants), imports, and infer file purpose. Enriches FileInfo
and ModuleInfo with deeper code intelligence.

Supports Python, JavaScript, and TypeScript with regex fallback.
"""

from __future__ import annotations

import re
from pathlib import Path

from codebase_md.model.module import FileInfo
from codebase_md.scanner.language_detector import DEFAULT_EXCLUDES, EXTENSION_MAP, _should_exclude

# Maximum file size for AST parsing
_MAX_FILE_SIZE = 200_000  # 200 KB

# Languages we can parse with tree-sitter
_PARSEABLE_LANGUAGES: set[str] = {"python", "javascript", "typescript"}

# Extensions for parseable languages
_PARSEABLE_EXTENSIONS: dict[str, str] = {
    ext: lang for ext, lang in EXTENSION_MAP.items() if lang in _PARSEABLE_LANGUAGES
}


class ASTAnalysisError(Exception):
    """Raised when AST analysis fails."""


# --- Purpose Inference ---

_PURPOSE_KEYWORDS: dict[str, list[str]] = {
    "API routes": [
        "router",
        "route",
        "endpoint",
        "api",
        "app.get",
        "app.post",
        "app.put",
        "app.delete",
        "@app.route",
        "@router",
        "fastapi",
        "APIRouter",
    ],
    "database models": [
        "model",
        "schema",
        "entity",
        "Base",
        "Column",
        "ForeignKey",
        "relationship",
        "Table",
        "prisma",
        "drizzle",
    ],
    "CLI commands": [
        "typer",
        "click",
        "argparse",
        "ArgumentParser",
        "command",
        "@app.command",
    ],
    "tests": [
        "pytest",
        "test_",
        "unittest",
        "describe(",
        "it(",
        "expect(",
        "assert",
        "jest",
        "vitest",
    ],
    "configuration": [
        "config",
        "settings",
        "env",
        "constants",
        "CONFIG",
        "SETTINGS",
    ],
    "utilities": [
        "util",
        "helper",
        "utils",
        "helpers",
        "common",
        "shared",
    ],
    "middleware": [
        "middleware",
        "interceptor",
        "guard",
        "pipe",
    ],
    "authentication": [
        "auth",
        "login",
        "logout",
        "token",
        "jwt",
        "session",
        "passport",
        "oauth",
    ],
    "data access": [
        "repository",
        "repo",
        "dao",
        "store",
        "persistence",
        "database",
        "db",
    ],
    "UI components": [
        "component",
        "widget",
        "jsx",
        "tsx",
        "render",
        "useState",
        "useEffect",
    ],
    "type definitions": [
        "types",
        "interfaces",
        "typing",
        "type",
        "interface",
        "TypeVar",
    ],
    "error handling": [
        "error",
        "exception",
        "Error",
        "Exception",
    ],
}


def _infer_purpose(file_path: Path, content: str, exports: list[str]) -> str:
    """Infer the purpose of a file from its name, content, and exports.

    Args:
        file_path: Path to the source file.
        content: File content as string.
        exports: List of exported symbol names.

    Returns:
        Inferred purpose string, or empty string if undetermined.
    """
    name_lower = file_path.stem.lower()
    content_lower = content.lower()

    scores: dict[str, int] = {}

    for purpose, keywords in _PURPOSE_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            kw_lower = keyword.lower()
            # Check filename
            if kw_lower in name_lower:
                score += 3
            # Check content
            if kw_lower in content_lower:
                score += 1
        if score > 0:
            scores[purpose] = score

    if not scores:
        return ""

    return max(scores, key=lambda k: scores[k])


# --- Python AST Analysis ---


def _analyze_python_file(file_path: Path) -> FileInfo:
    """Analyze a Python file and extract exports, imports, and purpose.

    Args:
        file_path: Path to the Python file.

    Returns:
        FileInfo with extracted data.
    """
    try:
        content = file_path.read_bytes()
    except OSError:
        return FileInfo(path=str(file_path))

    if len(content) > _MAX_FILE_SIZE:
        return FileInfo(path=str(file_path), language="python")

    content_str = content.decode("utf-8", errors="ignore")

    try:
        exports, imports = _parse_python_treesitter(content)
    except Exception:
        exports, imports = _parse_python_regex(content_str)

    purpose = _infer_purpose(file_path, content_str, exports)

    return FileInfo(
        path=str(file_path),
        language="python",
        exports=exports,
        imports=imports,
        purpose=purpose,
    )


def _parse_python_treesitter(content: bytes) -> tuple[list[str], list[str]]:
    """Parse a Python file with tree-sitter to extract exports and imports.

    Args:
        content: Raw file bytes.

    Returns:
        Tuple of (exports, imports).
    """
    import tree_sitter as ts
    import tree_sitter_python as tspython

    py_lang = ts.Language(tspython.language())
    parser = ts.Parser(py_lang)
    tree = parser.parse(content)

    exports: list[str] = []
    imports: list[str] = []

    for node in tree.root_node.children:
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            if name_node and name_node.text is not None:
                name = name_node.text.decode("utf-8")
                # Public functions (no leading underscore) are exports
                if not name.startswith("_"):
                    exports.append(name)

        elif node.type == "class_definition":
            name_node = node.child_by_field_name("name")
            if name_node and name_node.text is not None:
                name = name_node.text.decode("utf-8")
                if not name.startswith("_"):
                    exports.append(name)

        elif node.type == "expression_statement":
            # Top-level assignments — public constants
            if node.children and node.children[0].type == "assignment":
                left = node.children[0].child_by_field_name("left")
                if left and left.type == "identifier" and left.text is not None:
                    name = left.text.decode("utf-8")
                    if not name.startswith("_"):
                        exports.append(name)

        elif node.type == "import_statement":
            # import foo, bar
            for child in node.children:
                if child.type == "dotted_name" and child.text is not None:
                    imports.append(child.text.decode("utf-8"))

        elif node.type == "import_from_statement":
            # from foo.bar import Baz
            module_node = node.child_by_field_name("module_name")
            if module_node and module_node.text is not None:
                imports.append(module_node.text.decode("utf-8"))

        elif node.type == "decorated_definition":
            # @decorator above function/class
            for child in node.children:
                if child.type in ("function_definition", "class_definition"):
                    name_node = child.child_by_field_name("name")
                    if name_node and name_node.text is not None:
                        name = name_node.text.decode("utf-8")
                        if not name.startswith("_"):
                            exports.append(name)

    return exports, imports


def _parse_python_regex(content: str) -> tuple[list[str], list[str]]:
    """Parse a Python file with regex fallback.

    Args:
        content: File content as string.

    Returns:
        Tuple of (exports, imports).
    """
    exports: list[str] = []
    imports: list[str] = []

    # Functions and classes at module level (no indentation)
    for match in re.finditer(r"^(?:def|class)\s+(\w+)", content, re.MULTILINE):
        name = match.group(1)
        if not name.startswith("_"):
            exports.append(name)

    # Top-level assignments (no indentation)
    for match in re.finditer(r"^([A-Za-z]\w*)\s*=", content, re.MULTILINE):
        name = match.group(1)
        if not name.startswith("_"):
            exports.append(name)

    # Imports
    for match in re.finditer(r"^import\s+([\w.]+)", content, re.MULTILINE):
        imports.append(match.group(1))
    for match in re.finditer(r"^from\s+([\w.]+)\s+import", content, re.MULTILINE):
        imports.append(match.group(1))

    return exports, imports


# --- JavaScript/TypeScript AST Analysis ---


def _analyze_js_ts_file(file_path: Path) -> FileInfo:
    """Analyze a JavaScript/TypeScript file and extract exports, imports, purpose.

    Args:
        file_path: Path to the JS/TS file.

    Returns:
        FileInfo with extracted data.
    """
    try:
        content = file_path.read_bytes()
    except OSError:
        return FileInfo(path=str(file_path))

    suffix = file_path.suffix.lower()
    language = EXTENSION_MAP.get(suffix, "javascript")

    if len(content) > _MAX_FILE_SIZE:
        return FileInfo(path=str(file_path), language=language)

    content_str = content.decode("utf-8", errors="ignore")
    is_typescript = suffix in {".ts", ".tsx"}

    try:
        exports, imports = _parse_js_ts_treesitter(content, is_typescript)
    except Exception:
        exports, imports = _parse_js_ts_regex(content_str)

    purpose = _infer_purpose(file_path, content_str, exports)

    return FileInfo(
        path=str(file_path),
        language=language,
        exports=exports,
        imports=imports,
        purpose=purpose,
    )


def _parse_js_ts_treesitter(
    content: bytes, is_typescript: bool
) -> tuple[list[str], list[str]]:
    """Parse a JS/TS file with tree-sitter to extract exports and imports.

    Args:
        content: Raw file bytes.
        is_typescript: Whether the file is TypeScript.

    Returns:
        Tuple of (exports, imports).
    """
    import tree_sitter as ts

    if is_typescript:
        import tree_sitter_typescript as tsts

        lang = ts.Language(tsts.language_typescript())
    else:
        import tree_sitter_javascript as tsjs

        lang = ts.Language(tsjs.language())

    parser = ts.Parser(lang)
    tree = parser.parse(content)

    exports: list[str] = []
    imports: list[str] = []

    for node in tree.root_node.children:
        if node.type == "import_statement":
            _extract_js_import(node, imports)

        elif node.type == "export_statement":
            _extract_js_export(node, exports)

        elif node.type in ("function_declaration", "class_declaration"):
            name_node = node.child_by_field_name("name")
            if name_node and name_node.text is not None:
                exports.append(name_node.text.decode("utf-8"))

        elif node.type in ("lexical_declaration", "variable_declaration"):
            _extract_js_variable_names(node, exports)

    return exports, imports


def _extract_js_import(node: object, imports: list[str]) -> None:
    """Extract import source from an import statement node.

    Args:
        node: tree-sitter import_statement node.
        imports: List to append module names to (mutated).
    """
    source_node = getattr(node, "child_by_field_name", lambda _: None)("source")
    if source_node:
        # Remove quotes from string value
        raw = source_node.text.decode("utf-8").strip("'\"")
        imports.append(raw)


def _extract_js_export(node: object, exports: list[str]) -> None:
    """Extract exported names from an export statement node.

    Args:
        node: tree-sitter export_statement node.
        exports: List to append exported names to (mutated).
    """
    children = getattr(node, "children", [])
    for child in children:
        child_type = getattr(child, "type", "")

        if child_type in ("function_declaration", "class_declaration"):
            name_node = getattr(child, "child_by_field_name", lambda _: None)("name")
            if name_node:
                exports.append(name_node.text.decode("utf-8"))

        elif child_type in ("lexical_declaration", "variable_declaration"):
            _extract_js_variable_names(child, exports)


def _extract_js_variable_names(node: object, names: list[str]) -> None:
    """Extract variable names from a lexical/variable declaration node.

    Args:
        node: tree-sitter declaration node.
        names: List to append variable names to (mutated).
    """
    children = getattr(node, "children", [])
    for child in children:
        if getattr(child, "type", "") == "variable_declarator":
            name_node = getattr(child, "child_by_field_name", lambda _: None)("name")
            if name_node:
                names.append(name_node.text.decode("utf-8"))


def _parse_js_ts_regex(content: str) -> tuple[list[str], list[str]]:
    """Parse a JS/TS file with regex fallback.

    Args:
        content: File content as string.

    Returns:
        Tuple of (exports, imports).
    """
    exports: list[str] = []
    imports: list[str] = []

    # Exports: export function/class/const
    for match in re.finditer(
        r"\bexport\s+(?:default\s+)?(?:function|class)\s+(\w+)", content
    ):
        exports.append(match.group(1))
    for match in re.finditer(
        r"\bexport\s+(?:const|let|var)\s+(\w+)", content
    ):
        exports.append(match.group(1))

    # Imports: import ... from 'module'
    for match in re.finditer(r"""(?:from|require\()\s*['"]([^'"]+)['"]""", content):
        imports.append(match.group(1))

    return exports, imports


# --- Main Entry Point ---


def analyze_file(file_path: Path) -> FileInfo | None:
    """Analyze a single source file to extract exports, imports, and purpose.

    Args:
        file_path: Path to the source file.

    Returns:
        FileInfo with analysis results, or None if the file is not parseable.
    """
    suffix = file_path.suffix.lower()
    language = _PARSEABLE_EXTENSIONS.get(suffix)

    if language is None:
        return None

    if language == "python":
        return _analyze_python_file(file_path)
    if language in ("javascript", "typescript"):
        return _analyze_js_ts_file(file_path)

    return None


def analyze_files(
    root_path: Path,
    exclude: list[str] | None = None,
    max_files: int = 200,
) -> list[FileInfo]:
    """Analyze all parseable source files in a project.

    Walks the file tree and parses each analyzable file to extract
    exports, imports, and purpose.

    Args:
        root_path: Root directory of the project.
        exclude: Directory/file names to skip. Uses DEFAULT_EXCLUDES if None.
        max_files: Maximum number of files to analyze.

    Returns:
        List of FileInfo for analyzed files.

    Raises:
        ASTAnalysisError: If root_path is invalid.
    """
    if not root_path.exists():
        raise ASTAnalysisError(f"Path does not exist: {root_path}")
    if not root_path.is_dir():
        raise ASTAnalysisError(f"Path is not a directory: {root_path}")

    exclude_list = exclude if exclude is not None else DEFAULT_EXCLUDES
    results: list[FileInfo] = []

    for file_path in root_path.rglob("*"):
        if not file_path.is_file():
            continue
        relative = file_path.relative_to(root_path)
        if _should_exclude(relative, exclude_list):
            continue
        if file_path.suffix.lower() not in _PARSEABLE_EXTENSIONS:
            continue
        if file_path.stat().st_size > _MAX_FILE_SIZE:
            continue

        result = analyze_file(file_path)
        if result is not None:
            # Store relative path instead of absolute
            result = FileInfo(
                path=str(relative),
                language=result.language,
                exports=result.exports,
                imports=result.imports,
                purpose=result.purpose,
            )
            results.append(result)

        if len(results) >= max_files:
            break

    return results
