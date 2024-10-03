# Copyright (c) 2024 iiPython

# Modules
import click
import typing

# Click setup
class DefaultCommandGroup(click.Group):
    def group(self, *args, **kwargs) -> click.Group:  # type: ignore
        default_group = kwargs.pop("default_group", False)
        if default_group and not args:
            kwargs["name"] = kwargs.get("name", "<>")

        decorator = super(DefaultCommandGroup, self).command(*args, **kwargs)
        if default_group:
            def new_decorator(func: typing.Callable) -> typing.Callable:
                cmd = decorator(func)
                self.default_group = cmd.name  # type: ignore
                return cmd

            return new_decorator  # type: ignore

        return decorator  # type: ignore

    def command(self, *args, **kwargs) -> typing.Callable:  # type: ignore
        default_command = kwargs.pop("default_command", False)
        if default_command and not args:
            kwargs["name"] = kwargs.get("name", "<>")

        decorator = super(DefaultCommandGroup, self).command(*args, **kwargs)
        if default_command:
            def new_decorator(func: typing.Callable) -> typing.Callable:
                cmd = decorator(func)
                self.default_command = cmd.name  # type: ignore
                return cmd

            return new_decorator

        return decorator

    def resolve_command(self, ctx, args) -> tuple:
        try:
            return super(DefaultCommandGroup, self).resolve_command(ctx, args)

        except click.UsageError:
            default_group = self.default_group if hasattr(self, "default_group") else None  # type: ignore
            default_command = self.default_command if hasattr(self, "default_command") else None  # type: ignore
            if default_group:
                args.insert(0, default_group)  # type: ignore

            if default_command:
                args.insert(0, default_command)  # type: ignore

            return super(DefaultCommandGroup, self).resolve_command(ctx, args)

@click.group(cls = DefaultCommandGroup, epilog = "Copyright (c) 2024 iiPython")
def usps() -> None:
    """A CLI for tracking packages from USPS.
    
    \b
    USPS site  : https://usps.com
    Source code: https://github.com/iiPythonx/usps"""
    return
