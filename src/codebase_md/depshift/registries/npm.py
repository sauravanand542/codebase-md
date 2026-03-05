"""npm registry client for querying package metadata.

Queries the npm registry API to retrieve latest versions, release dates,
and package metadata for JavaScript/TypeScript packages.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx


class NpmRegistryError(Exception):
    """Raised when npm registry query fails."""


@dataclass(frozen=True)
class NpmPackageInfo:
    """Package metadata from the npm registry.

    Attributes:
        name: Package name on npm.
        latest_version: Latest version from the 'latest' dist-tag.
        description: Short package description.
        homepage: Project homepage URL.
        license_name: License identifier (e.g. 'MIT').
        repository_url: Source code repository URL.
        release_dates: Mapping of version → release ISO date (most recent N).
        all_versions: All available versions sorted newest-first.
        deprecated: Deprecation message, if any.
    """

    name: str
    latest_version: str
    description: str = ""
    homepage: str = ""
    license_name: str = ""
    repository_url: str = ""
    release_dates: dict[str, str] = field(default_factory=dict)
    all_versions: list[str] = field(default_factory=list)
    deprecated: str = ""


_NPM_BASE_URL = "https://registry.npmjs.org"
_DEFAULT_TIMEOUT = 10.0


async def fetch_package_info(
    package_name: str,
    *,
    timeout: float = _DEFAULT_TIMEOUT,
) -> NpmPackageInfo:
    """Fetch package metadata from the npm registry.

    Args:
        package_name: Name of the package on npm (e.g. 'react').
        timeout: HTTP request timeout in seconds.

    Returns:
        NpmPackageInfo with the latest version and metadata.

    Raises:
        NpmRegistryError: If the package is not found or the request fails.
    """
    url = f"{_NPM_BASE_URL}/{package_name}"

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
    except httpx.HTTPError as e:
        raise NpmRegistryError(f"Failed to query npm for '{package_name}': {e}") from e

    if response.status_code == 404:
        raise NpmRegistryError(f"Package '{package_name}' not found on npm")
    if response.status_code != 200:
        raise NpmRegistryError(f"npm returned HTTP {response.status_code} for '{package_name}'")

    try:
        data = response.json()
    except ValueError as e:
        raise NpmRegistryError(f"Invalid JSON response from npm for '{package_name}': {e}") from e

    return _parse_npm_response(package_name, data)


def fetch_package_info_sync(
    package_name: str,
    *,
    timeout: float = _DEFAULT_TIMEOUT,
) -> NpmPackageInfo:
    """Synchronous version of fetch_package_info.

    Args:
        package_name: Name of the package on npm.
        timeout: HTTP request timeout in seconds.

    Returns:
        NpmPackageInfo with the latest version and metadata.

    Raises:
        NpmRegistryError: If the package is not found or the request fails.
    """
    url = f"{_NPM_BASE_URL}/{package_name}"

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
    except httpx.HTTPError as e:
        raise NpmRegistryError(f"Failed to query npm for '{package_name}': {e}") from e

    if response.status_code == 404:
        raise NpmRegistryError(f"Package '{package_name}' not found on npm")
    if response.status_code != 200:
        raise NpmRegistryError(f"npm returned HTTP {response.status_code} for '{package_name}'")

    try:
        data = response.json()
    except ValueError as e:
        raise NpmRegistryError(f"Invalid JSON response from npm for '{package_name}': {e}") from e

    return _parse_npm_response(package_name, data)


def _parse_npm_response(
    package_name: str,
    data: dict[str, object],
) -> NpmPackageInfo:
    """Parse npm registry JSON response into NpmPackageInfo.

    Args:
        package_name: The queried package name.
        data: Parsed JSON response from npm.

    Returns:
        Populated NpmPackageInfo.

    Raises:
        NpmRegistryError: If the response structure is unexpected.
    """
    try:
        # Get latest version from dist-tags
        dist_tags = data.get("dist-tags", {})
        if not isinstance(dist_tags, dict):
            dist_tags = {}
        latest_version = str(dist_tags.get("latest", "unknown"))

        # Get release dates from time field
        time_map = data.get("time", {})
        if not isinstance(time_map, dict):
            time_map = {}

        # Build version list from 'time' (excludes 'created' and 'modified' keys)
        version_dates: list[tuple[str, str]] = []
        release_dates: dict[str, str] = {}
        for key, value in time_map.items():
            if key in ("created", "modified"):
                continue
            date_str = str(value)
            version_dates.append((key, date_str))
            release_dates[key] = date_str

        # Sort by date, newest first
        version_dates.sort(key=lambda x: x[1], reverse=True)
        all_versions = [v for v, _ in version_dates]

        # Keep only 20 most recent release dates
        recent_dates: dict[str, str] = {}
        for ver in all_versions[:20]:
            if ver in release_dates:
                recent_dates[ver] = release_dates[ver]

        # Get description from top level or latest version info
        description = str(data.get("description", ""))

        # Get homepage
        homepage = str(data.get("homepage", "") or "")

        # Get license
        license_raw = data.get("license", "")
        if isinstance(license_raw, dict):
            license_name = str(license_raw.get("type", ""))
        else:
            license_name = str(license_raw or "")

        # Get repository URL
        repo_raw = data.get("repository", "")
        if isinstance(repo_raw, dict):
            repository_url = str(repo_raw.get("url", ""))
        else:
            repository_url = str(repo_raw or "")

        # Check for deprecation in latest version
        versions_map = data.get("versions", {})
        deprecated = ""
        if isinstance(versions_map, dict) and latest_version in versions_map:
            latest_data = versions_map[latest_version]
            if isinstance(latest_data, dict):
                dep_msg = latest_data.get("deprecated", "")
                if dep_msg:
                    deprecated = str(dep_msg)

        return NpmPackageInfo(
            name=package_name,
            latest_version=latest_version,
            description=description,
            homepage=homepage,
            license_name=license_name,
            repository_url=repository_url,
            release_dates=recent_dates,
            all_versions=all_versions,
            deprecated=deprecated,
        )
    except (KeyError, TypeError, IndexError) as e:
        raise NpmRegistryError(f"Failed to parse npm response for '{package_name}': {e}") from e
