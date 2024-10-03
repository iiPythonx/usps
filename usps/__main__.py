# Copyright (c) 2024 iiPython

# Modules
import typing
import textwrap

import typer
from rich.console import Console

from usps.storage import packages
from usps.tracking import Package

from .utils import get_delta

# Initialization
app = typer.Typer(help = "A CLI for tracking packages from USPS.")
con = Console(highlight = False)

# Handle commands
def show_package(tracking_number: str, package: Package) -> None:
    con.print(f"°︎ USPS [bright_blue]{tracking_number}[/] - [cyan]{package.state}[/]")
    if package.expected:
        def ordinal(day: int) -> str:
            return str(day) + ("th" if 4 <= day % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th"))

        date = package.expected[0].strftime("%A, %B {day}").format(day = ordinal(package.expected[0].day))
        times = [time.strftime("%I:%M %p") for time in package.expected]
        if len(package.expected) == 1:
            con.print(f"\t[green]Estimated delivery on {date} by {times[0]}.[/]")

        else:
            con.print(f"\t[green]Estimated delivery on {date} between {times[0]} and {times[1]}.[/]")

    else:
        con.print("\t[red]No estimated delivery time yet.[/]")

    con.print(*[f"\t[yellow]{line}[/]" for line in textwrap.wrap(package.last_status, 102)], "", sep = "\n")
    for step in package.steps:
        con.print(f"\t[cyan]{step.details}[/]\t[yellow]{step.location}[/]\t[bright_blue]{get_delta(step.time)}[/]")

    print()

@app.command("track")
def command_track(tracking_number: typing.Annotated[typing.Optional[str], typer.Argument()] = None) -> None:
    """Track the specified tracking numbers, tracking your package list if no tracking
    number is specified."""

    from .tracking import tracking

    if tracking_number is not None:
        return show_package(tracking_number, tracking.track_package(tracking_number))

    tracking_numbers = packages.load()
    if not tracking_numbers:
        return con.print("[red]× You don't have any default packages to track.[/]")

    for package in tracking_numbers:
        show_package(package, tracking.track_package(package))

@app.command("add")
def command_add(tracking_numbers: list[str]) -> None:
    """Add tracking numbers to your package list."""
    packages.save(packages.load() + list(tracking_numbers))
    for tracking_number in tracking_numbers:
        con.print(f"[green]✓ USPS {tracking_number} added to your package list.[/]")

@app.command("remove")
def command_remove(tracking_numbers: list[str]) -> None:
    """Remove tracking numbers from your package list."""
    current_packages = packages.load()
    for tracking_number in tracking_numbers:
        if tracking_number in current_packages:
            current_packages.remove(tracking_number)
            con.print(f"[green]✓ USPS {tracking_number} removed from your package list.[/]")

    packages.save(current_packages)
