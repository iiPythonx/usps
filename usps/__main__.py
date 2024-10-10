# Copyright (c) 2024 iiPython

# Modules
import time
import typing
import textwrap

import typer
from rich.console import Console

from usps.storage import packages

from . import __version__
from .utils import get_delta
from .tracking import track_package, get_service
from .tracking.exceptions import StatusNotAvailable

# Initialization
app = typer.Typer(help = "A CLI for tracking packages from USPS.", pretty_exceptions_show_locals = False)
con = Console(highlight = False)

# Handle commands
def show_package(tracking_number: str, name: str | None) -> None:
    identifier = f"{get_service(tracking_number)} [bright_blue]{tracking_number}[/]"
    if name is not None:
        identifier = f"{name} ({identifier})"

    try:
        package = track_package(tracking_number)
        con.print(f"°︎ {identifier} - [cyan]{package.state}[/]")

    except StatusNotAvailable as failure:
        return con.print(f"°︎ {identifier} - [red]{failure}[/]")
    
    if package.expected:
        def ordinal(day: int) -> str:
            return str(day) + ("th" if 4 <= day % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th"))

        date = package.expected[0].strftime("%A, %B {day}").format(day = ordinal(package.expected[0].day))

        # Show delivery time based on whether there's 1 or 2
        times = [time.strftime("%I:%M %p") for time in package.expected]
        if len(package.expected) == 1:
            con.print(f"\t[green]Estimated delivery on {date} by {times[0]}.[/]")

        else:
            con.print(f"\t[green]Estimated delivery on {date} between {times[0]} and {times[1]}.[/]")

    else:
        if package.state == "Delivered":
            con.print("\t[green]This package has been delivered.[/]")

        else:
            con.print("\t[red]No estimated delivery time yet.[/]")

    con.print(*[f"\t[yellow]{line}[/]" for line in textwrap.wrap(package.last_status, 102)], "", sep = "\n")

    # Print out steps
    location_max = len(max(package.steps, key = lambda _package: len(_package.location)).location)
    for step in package.steps[:10]:
        location_block = f"[yellow]{step.location}[/]{' ' * (location_max - len(step.location))}"
        con.print(f"\t[cyan]{step.details}[/]\t{location_block}\t[bright_blue]{get_delta(step.location, step.time)}[/]")

    print()

@app.command("track")
def command_track(
    tracking_number: typing.Annotated[typing.Optional[str], typer.Argument()] = None,
    refresh: typing.Annotated[typing.Optional[int], typer.Option(help = "Auto refresh the tracking information every x minutes.")] = None,
) -> None:
    """Track the specified tracking numbers, tracking your package list if no tracking
    number is specified."""

    if tracking_number is not None:
        return show_package(tracking_number, None)

    tracking_numbers = packages.load()
    if not tracking_numbers:
        return con.print("[red]× You don't have any default packages to track.[/]")

    if refresh is not None:
        while True:
            print("\033[H\033[2J", end = "")
            for package, name in tracking_numbers.items():
                show_package(package, name)

            time.sleep(refresh * 60)

    else:
        for package, name in tracking_numbers.items():
            show_package(package, name)

@app.command("add")
def command_add(tracking_numbers: list[str]) -> None:
    """Add tracking numbers to your package list."""
    packages.save(packages.load() | {number: None for number in tracking_numbers})
    for tracking_number in tracking_numbers:
        con.print(f"[green]✓ USPS {tracking_number} added to your package list.[/]")

@app.command("remove")
def command_remove(tracking_numbers: list[str]) -> None:
    """Remove tracking numbers from your package list."""
    current_packages = packages.load()
    for tracking_number in tracking_numbers:
        if tracking_number in current_packages:
            del current_packages[tracking_number]
            con.print(f"[green]✓ USPS {tracking_number} removed from your package list.[/]")

    packages.save(current_packages)

@app.command("name")
def command_name(
    tracking_number: str,
    name: typing.Annotated[typing.Optional[str], typer.Argument()] = None,
    erase: typing.Annotated[bool, typer.Option(help = "Remove the name from the given package.")] = False,
) -> None:
    """Assign a name to the given package, updating if it already has one. Package
    will be saved to the package list if it hasn't been added previously."""
    original_packages = packages.load()
    if erase:
        if tracking_number in original_packages:
            return con.print(f"[green]✓ USPS {tracking_number}'s name has been erased.[/]")

        return con.print(f"[red]× USPS {tracking_number} is not in the package list.[/]")

    if name is None:
        name = con.input("[cyan]Choose a package name: ")
        if not name.strip():
            return con.print("[red]× Name cannot be an empty string.[/]")

    if tracking_number not in original_packages:
        con.print(f"[green]✓ USPS {tracking_number} added to your package list with name [cyan]'{name}'[/].[/]")

    else:
        con.print(f"[green]✓ USPS {tracking_number} updated with name [cyan]'{name}'[/].[/]")

    packages.save(original_packages | {tracking_number: name})

@app.command("version")
def command_version() -> None:
    """Show the package version."""
    con.print(f"[cyan]USPS-cli v{__version__} by iiPython[/]\n -> [yellow]https://github.com/iiPythonx/usps")
