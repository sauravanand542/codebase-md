### PR Description:
This pull request adds support for parsing PHP dependencies from `composer.json` files in the `codebase-md` project. It includes the following changes:

1. Introduced a new `_parse_composer` function in `src/codebase_md/scanner/dependency_parser.py` to parse dependencies from the `composer.json` file.
2. Updated the file detection logic to recognize and use `composer.json`.
3. Added test fixtures and tests to verify the functionalities of the new parser.

#### Detailed Code Changes:

1. **Dependency Parser Update**:
   - Added a new function `_parse_composer` that mirrors the `_parse_package_json` function to handle the structure of `composer.json`.

```python
# src/codebase_md/scanner/dependency_parser.py
import json
from typing import List
from src.codebase_md.model.project import DependencyInfo

def _parse_composer(file_content: str) -> List[DependencyInfo]:
    """Parse dependencies from composer.json."""
    data = json.loads(file_content)
    dependencies = data.get('require', {})
    
    return [
        DependencyInfo(name=name, version=version)
        for name, version in dependencies.items()
    ]

# Register the composer.json in the detector logic
DETECTORS = {
    ...
    "composer.json": _parse_composer,
    ...
}
```

2. **Test Cases**:
   - Created a test fixture for `composer.json` and implemented test cases to ensure correctness.

```python
# tests/test_dependency_parser.py
import pytest
from src.codebase_md.scanner.dependency_parser import _parse_composer
from src.codebase_md.model.project import DependencyInfo

@pytest.fixture
def composer_json():
    return """
    {
        "require": {
            "php": "^7.4 || ^8.0",
            "symfony/console": "^5.3",
            "guzzlehttp/guzzle": "^7.0"
        }
    }
    """

def test_parse_composer(composer_json):
    expected_dependencies = [
        DependencyInfo(name="php", version="^7.4 || ^8.0"),
        DependencyInfo(name="symfony/console", version="^5.3"),
        DependencyInfo(name="guzzlehttp/guzzle", version="^7.0")
    ]

    dependencies = _parse_composer(composer_json)
    assert dependencies == expected_dependencies
```

#### Explanation:
- A new function `_parse_composer` was implemented to read and parse the JSON structure of `composer.json`, extracting dependencies listed under the `require` section.
- The function was registered to handle `composer.json` files in the detection logic.
- Test cases were written to validate the parser using a set of expected dependencies as found typically in a `composer.json`.

These changes ensure that the `codebase-md` tool can now parse and recognize PHP dependencies, enhancing its overall utility and coverage across different programming environments.