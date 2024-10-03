# Copyright (c) 2024 iiPython

# Modules
import json
import textwrap
from pathlib import Path

import click
from rich.console import Console

from usps.tracking import Package

from .commands import usps, DefaultCommandGroup
from .commands.utils import get_delta

# Handle saving/loading current packages
package_file = Path.home() / ".local/share/usps/packages.json"
package_file.parent.mkdir(exist_ok = True, parents = True)

def load_packages() -> list[str]:
    if not package_file.is_file():
        return []

    return json.loads(package_file.read_text())

def save_packages(packages: list[str]) -> None:
    package_file.write_text(json.dumps(packages, indent = 4))

# Initialization
con = Console(highlight = False)

# Handle commands
@usps.group(cls = DefaultCommandGroup, name = "track", default_group = True)
def group_track() -> None:
    return

def show_package(tracking_number: str, package: Package) -> None:
    con.print(f"°︎ USPS [bright_blue]{tracking_number}[/] - [cyan]{package.state}[/]")
    if package.expected:
        def ordinal(day: int) -> str:
            return str(day) + ("th" if 4 <= day % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th"))

        time = package.expected.strftime("%A, %B {day} by %I:%M %p").format(day = ordinal(package.expected.day))
        con.print(f"\t[green]Estimated delivery on {time}.[/]")

    else:
        con.print("\t[red]No estimated delivery time yet.[/]")

    con.print(*[f"\t[yellow]{line}[/]" for line in textwrap.wrap(package.last_status, 102)], "", sep = "\n")
    for step in package.steps:
        con.print(f"\t[cyan]{step.details}[/]\t[yellow]{step.location}[/]\t[bright_blue]{get_delta(step.time)}[/]")

    print()

@group_track.command("show", default_command = True)
@click.argument("tracking-number", required = False)
def command_show(tracking_number: str | None) -> None:
    from .tracking import tracking

    if tracking_number is not None:
        return show_package(tracking_number, tracking.track_package(tracking_number))

    packages = load_packages()
    if not packages:
        return con.print("[red]× You don't have any default packages to track.[/]")

    for package in packages:
        show_package(package, tracking.track_package(package))

@group_track.command("add")
@click.argument("tracking-numbers", nargs = -1)
def command_add(tracking_numbers: tuple[str]) -> None:
    save_packages(load_packages() + list(tracking_numbers))
    for tracking_number in tracking_numbers:
        con.print(f"[green]✓ USPS {tracking_number} added to your package list.[/]")
