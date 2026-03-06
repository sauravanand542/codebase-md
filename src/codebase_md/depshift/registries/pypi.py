"""PyPI registry client for querying package metadata.

Queries the PyPI JSON API to retrieve latest versions, release dates,
and package metadata for Python packages.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx


class PyPIRegistryError(Exception):
    """Raised when PyPI registry query fails."""


@dataclass(frozen=True)
class PyPIPackageInfo:
    """Package metadata from the PyPI registry.

    Attributes:
        name: Package name on PyPI.
        latest_version: Latest stable release version.
        summary: Short package description.
        home_page: Project URL or homepage.
        license_name: License identifier.
        requires_python: Python version constraint.
        release_dates: Mapping of version → release date (most recent N).
        all_versions: All available versions sorted newest-first.
    """

    name: str
    latest_version: str
    summary: str = ""
    home_page: str = ""
    license_name: str = ""
    requires_python: str = ""
    release_dates: dict[str, str] = field(default_factory=dict)
    all_versions: list[str] = field(default_factory=list)


_PYPI_BASE_URL = "https://pypi.org/pypi"
_DEFAULT_TIMEOUT = 10.0
_MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # 10 MB


async def fetch_package_info(
    package_name: str,
    *,
    timeout: float = _DEFAULT_TIMEOUT,
) -> PyPIPackageInfo:
    """Fetch package metadata from the PyPI JSON API.

    Args:
        package_name: Name of the package on PyPI (e.g. 'requests').
        timeout: HTTP request timeout in seconds.

    Returns:
        PyPIPackageInfo with the latest version and metadata.

    Raises:
        PyPIRegistryError: If the package is not found or the request fails.
    """
    url = f"{_PYPI_BASE_URL}/{package_name}/json"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
    except httpx.HTTPError as e:
        raise PyPIRegistryError(f"Failed to query PyPI for '{package_name}': {e}") from e

    if response.status_code == 404:
        raise PyPIRegistryError(f"Package '{package_name}' not found on PyPI")
    if response.status_code != 200:
        raise PyPIRegistryError(f"PyPI returned HTTP {response.status_code} for '{package_name}'")

    if len(response.content) > _MAX_RESPONSE_SIZE:
        raise PyPIRegistryError(f"Response for '{package_name}' exceeds {_MAX_RESPONSE_SIZE} bytes")

    try:
        data = response.json()
    except ValueError as e:
        raise PyPIRegistryError(f"Invalid JSON response from PyPI for '{package_name}': {e}") from e

    return _parse_pypi_response(package_name, data)


def fetch_package_info_sync(
    package_name: str,
    *,
    timeout: float = _DEFAULT_TIMEOUT,
) -> PyPIPackageInfo:
    """Synchronous version of fetch_package_info.

    Args:
        package_name: Name of the package on PyPI.
        timeout: HTTP request timeout in seconds.

    Returns:
        PyPIPackageInfo with the latest version and metadata.

    Raises:
        PyPIRegistryError: If the package is not found or the request fails.
    """
    url = f"{_PYPI_BASE_URL}/{package_name}/json"

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
    except httpx.HTTPError as e:
        raise PyPIRegistryError(f"Failed to query PyPI for '{package_name}': {e}") from e

    if response.status_code == 404:
        raise PyPIRegistryError(f"Package '{package_name}' not found on PyPI")
    if response.status_code != 200:
        raise PyPIRegistryError(f"PyPI returned HTTP {response.status_code} for '{package_name}'")

    if len(response.content) > _MAX_RESPONSE_SIZE:
        raise PyPIRegistryError(f"Response for '{package_name}' exceeds {_MAX_RESPONSE_SIZE} bytes")

    try:
        data = response.json()
    except ValueError as e:
        raise PyPIRegistryError(f"Invalid JSON response from PyPI for '{package_name}': {e}") from e

    return _parse_pypi_response(package_name, data)


def _parse_pypi_response(
    package_name: str,
    data: dict[str, object],
) -> PyPIPackageInfo:
    """Parse PyPI JSON API response into PyPIPackageInfo.

    Args:
        package_name: The queried package name.
        data: Parsed JSON response from PyPI.

    Returns:
        Populated PyPIPackageInfo.

    Raises:
        PyPIRegistryError: If the response structure is unexpected.
    """
    try:
        info = data.get("info", {})
        if not isinstance(info, dict):
            raise PyPIRegistryError(f"Unexpected 'info' format for '{package_name}'")

        releases = data.get("releases", {})
        if not isinstance(releases, dict):
            releases = {}

        # Extract release dates (most recent 20 versions)
        release_dates: dict[str, str] = {}
        version_list: list[tuple[str, str]] = []

        for version, release_files in releases.items():
            if not isinstance(release_files, list) or not release_files:
                continue
            # Use the upload_time of the first file in the release
            first_file = release_files[0]
            if isinstance(first_file, dict):
                upload_time = first_file.get("upload_time", "")
                if isinstance(upload_time, str) and upload_time:
                    release_dates[version] = upload_time
                    version_list.append((version, upload_time))

        # Sort versions by upload time (newest first)
        version_list.sort(key=lambda x: x[1], reverse=True)
        all_versions = [v for v, _ in version_list]

        # Keep only the 20 most recent release dates
        recent_dates: dict[str, str] = {}
        for ver in all_versions[:20]:
            if ver in release_dates:
                recent_dates[ver] = release_dates[ver]

        latest_version = str(info.get("version", "unknown"))
        summary = str(info.get("summary", ""))
        home_page = str(info.get("home_page", "") or info.get("project_url", "") or "")
        license_name = str(info.get("license", "") or "")
        requires_python = str(info.get("requires_python", "") or "")

        return PyPIPackageInfo(
            name=package_name,
            latest_version=latest_version,
            summary=summary,
            home_page=home_page,
            license_name=license_name,
            requires_python=requires_python,
            release_dates=recent_dates,
            all_versions=all_versions,
        )
    except (KeyError, TypeError, IndexError) as e:
        raise PyPIRegistryError(f"Failed to parse PyPI response for '{package_name}': {e}") from e
