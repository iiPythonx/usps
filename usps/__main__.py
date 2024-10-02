# Copyright (c) 2024 iiPython

# Modules
import json
from signal import default_int_handler
import typing
from pathlib import Path

import click

# Handle saving/loading current packages
package_file = Path.home() / ".local/share/usps/packages.json"
package_file.parent.mkdir(exist_ok = True, parents = True)

def load_packages() -> list[str]:
    if not package_file.is_file():
        return []

    return json.loads(package_file.read_text())

def save_packages(packages: list[str]) -> None:
    package_file.write_text(json.dumps(packages, indent = 4))

# Click setup
class DefaultCommandGroup(click.Group):
    default_command: str

    def command(self, *args, **kwargs) -> typing.Callable:  # type: ignore
        default_command = kwargs.pop("default_command", False)
        if default_command and not args:
            kwargs["name"] = kwargs.get("name", "<>")

        decorator = super(DefaultCommandGroup, self).command(*args, **kwargs)
        if default_command:
            def new_decorator(func: typing.Callable) -> typing.Callable:
                cmd = decorator(func)
                if cmd.name is None:
                    return cmd

                self.default_command = cmd.name
                return cmd

            return new_decorator

        return decorator

    def resolve_command(self, ctx, args) -> tuple:
        try:
            return super(DefaultCommandGroup, self).resolve_command(ctx, args)

        except click.UsageError:
            args.insert(0, self.default_command)
            return super(DefaultCommandGroup, self).resolve_command(ctx, args)

@click.group(cls = DefaultCommandGroup, epilog = "Copyright (c) 2024 iiPython")
def usps() -> None:
    """A CLI for tracking packages from USPS.
    
    \b
    USPS site  : https://usps.com
    Source code: https://github.com/iiPythonx/usps"""
    return

# Handle commands
@usps.group(cls = DefaultCommandGroup, default_command = True)
def track() -> None:
    return

@track.command("show", default_command = True)
def show() -> None:
    print("this is show")

@track.command("add")
def add() -> None:
    print("this is add")
