"""
Version Information Module for SomaBrain.

This module defines version constants for the SomaBrain package, including API version
for compatibility checking and package version for release management.

Version Constants:
    API_VERSION: Integer version for API compatibility (incremented on breaking changes).
    PACKAGE_VERSION: Semantic version string for the package release.
"""

API_VERSION = 1
"""
API version number for compatibility checking.

This integer is incremented whenever there are breaking changes to the public API.
Clients can use this to ensure compatibility with the installed version.

Type: int
Value: 1
"""

PACKAGE_VERSION = "0.1.0"
"""
Package version string following semantic versioning.

This string represents the current release version of the SomaBrain package.
Follows semantic versioning format: MAJOR.MINOR.PATCH

Type: str
Value: "0.1.0"
"""
