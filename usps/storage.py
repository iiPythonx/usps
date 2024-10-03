# Copyright (c) 2024 iiPython

# Modules
import json
import typing
from pathlib import Path

# Initialization
usps_global = Path.home() / ".local/share/usps"
usps_global.mkdir(exist_ok = True, parents = True)

# Handle saving/loading current packages
class PackageStorage():
    def __init__(self) -> None:
        self.package_file = usps_global / "packages.json"

    def load(self) -> list[str]:
        if not self.package_file.is_file():
            return []

        return json.loads(self.package_file.read_text())

    def save(self, packages: list[str]) -> None:
        self.package_file.write_text(json.dumps(packages, indent = 4))

packages = PackageStorage()

# Handle caching cookies/headers
class SecurityStorage():
    def __init__(self) -> None:
        self.security_file = usps_global / "security.json"

    def load(self) -> dict[str, str]:
        if not self.security_file.is_file():
            return {}

        return json.loads(self.security_file.read_text())

    def save(self, data: dict[str, typing.Any]) -> None:
        self.security_file.write_text(json.dumps(data, indent = 4))

security = SecurityStorage()