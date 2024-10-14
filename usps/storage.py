# Copyright (c) 2024 iiPython

# Modules
import sys
import json
from pathlib import Path

# Initialization
usps_global = Path.home() / (".local/share" if sys.platform == "linux" else "AppData/Roaming") / "usps"
usps_global.mkdir(exist_ok = True, parents = True)

# Handle storage of everything
class Storage:
    def __init__(self, filename: str) -> None:
        self.file = usps_global / filename
        
    def load(self) -> dict[str, str | None]:
        if not self.file.is_file():
            return {}

        return json.loads(self.file.read_text())

    def save(self, data: dict[str, str | None]) -> None:
        self.file.write_text(json.dumps(data, indent = 4))

packages, security = Storage("packages.json"), Storage("security.json")
