# Copyright (c) 2024 iiPython

# Modules
import json
from pathlib import Path

# Initialization
usps_global = Path.home() / ".local/share/usps"
usps_global.mkdir(exist_ok = True, parents = True)

# Handle saving/loading current packages
class PackageStorage:
    def __init__(self) -> None:
        self.package_file = usps_global / "packages.json"

    def load(self) -> dict[str, str | None]:
        if not self.package_file.is_file():
            return {}

        return json.loads(self.package_file.read_text())

    def save(self, _packages: dict[str, str | None]) -> None:
        self.package_file.write_text(json.dumps(_packages, indent = 4))

packages = PackageStorage()

# Handle caching cookies/headers
class SecurityStorage:
    def __init__(self) -> None:
        self.security_file = usps_global / "security.json"

    def load(self) -> dict[str, str]:
        if not self.security_file.is_file():
            return {}

        return json.loads(self.security_file.read_text())

    def save(self, _security: dict[str, str]) -> None:
        self.security_file.write_text(json.dumps(_security, indent = 4))

security = SecurityStorage()
