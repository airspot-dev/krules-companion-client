import json
import re
from datetime import datetime

import sys

import requests
import typer
from requests import HTTPError
from rich.console import Console
from rich import print
from pathlib import Path
from typing import Optional, List, Tuple, Any
from typing_extensions import Annotated
# import tomllib
import tomli
import validators
from .accounts import app as accounts_app

app = typer.Typer()
app.add_typer(accounts_app, name="accounts")

err_console = Console(stderr=True)

RE_TOPIC = re.compile("^projects/.*/topics/.*$")


def _parse_property_value(val: str) -> dict:
    if val == "-":
        try:
            return json.loads(sys.stdin.read())
        except json.JSONDecodeError as ex:
            err_console.print(ex)
            raise typer.Abort()
    try:
        k, v = val.split("=")
    except ValueError:
        err_console.print(f"Malformed property '{val}'. Expected property=value")
        raise typer.Abort()
    t_v = type(v)
    if t_v == bytes or t_v == str:
        try:
            v = json.loads(v)
        except json.JSONDecodeError:
            if t_v == bytes:
                v = v.decode()
    return {k: v}


DEFAULT_CONFIG_FILE = Path.home() / ".config/companion/config"

defaults = {}


def _check_defaults():
    if "address" not in defaults:
        err_console.print("No backend 'address' provided")
        typer.Abort()
        if not validators.url(defaults['address']):
            err_console.print(f"'{defaults['address']}' is not a valid URL")
            raise typer.Abort()
    if "subscription" not in defaults:
        err_console.print("No 'subscription' provided")
        raise typer.Abort()
    if "api_key" not in defaults:
        err_console.print("No 'api_key' provided")
        raise typer.Abort()


@app.command()
def publish(
        group: Annotated[str, typer.Option("-g", "--group", help="Entity group", envvar="COMPANION_GROUP")],
        entity: Annotated[str, typer.Option("-e", "--entity", help="Entity ID", envvar="COMPANION_ENTITY")] = None,
        properties: Annotated[List[dict], typer.Argument(parser=_parse_property_value,
                                                         help="List of properties to set in form name=value, value "
                                                              "can be a json string, '-' for stdin")] = None,
        filter: Annotated[Optional[Tuple[str, str, str]], typer.Option("-f", "--filter",
                                                                       help="Filter query. Eg: [col \"==\" value]")] = (
                None, None, None),

        verbose: Annotated[
            bool, typer.Option("-v", "--verbose", help="Be verbose", envvar="COMPANION_VERBOSE")] = False,
        dry_run: Annotated[bool, typer.Option(help="Do not post http request", envvar="COMPANION_DRYRUN")] = False

):
    _check_defaults()

    filter = _validate_filter(filter)
    has_filter = filter is not None and sum(p is not None for p in filter) == 3
    # if not has_filter and entity is None:
    #     err_console.print("Entity or filter missing")
    #     raise typer.Abort()
    if has_filter and entity is not None:
        err_console.print("You can specify only one from entity or filter")
        raise typer.Abort()

    if properties is None:
        properties = []

    all_props = {}
    [all_props.update(p) for p in properties]

    all_props["_last_update"] = f"dt|{datetime.now().isoformat()}"

    if verbose:
        print({
            "group": group,
            "entity": entity,
            "filter": filter,
            "properties": all_props,
        })
    if not dry_run:

        if entity is not None:
            response = requests.post(
                f'{defaults["address"]}/api/v1/{defaults["subscription"]}/{group}/{entity}',
                headers={"api-key": defaults["api_key"]},
                json=all_props
            )
        else:
            response = requests.post(
                f'{defaults["address"]}/api/v1/{defaults["subscription"]}/{group}',
                headers={"api-key": defaults["api_key"]},
                json={
                    "data": all_props,
                    "entities_filter": filter
                }
            )
        response.raise_for_status()
        if verbose:
            print(response)


def _validate_filter(filter):
    supported_operators = [
        "<",
        "<=",
        "==",
        ">",
        ">=",
        "!=",
        "array-contains",
        "array-contains-any",
        "in",
        "not-in"
    ]
    if filter is None:
        return filter
    lval, op, rval = filter
    if lval is not None:
        if op not in supported_operators:
            err_console.print(f"operator '{op}' not in {supported_operators}")
            raise typer.Abort()
        try:
            rval = json.loads(rval)
        except json.JSONDecodeError:
            pass
    if lval is None:
        filter = None
    return filter


@app.command()
def delete(
        group: Annotated[str, typer.Option("-g", "--group", help="Entity group", envvar="COMPANION_GROUP")],
        entity: Annotated[str, typer.Option("-e", "--entity", help="Entity ID", envvar="COMPANION_ENTITY")],
        verbose: Annotated[
            bool, typer.Option("-v", "--verbose", help="Be verbose", envvar="COMPANION_VERBOSE")] = False,
        dry_run: Annotated[bool, typer.Option(help="Do not post http request", envvar="COMPANION_DRYRUN")] = False
):
    _check_defaults()

    if verbose:
        print({
            "group": group,
            "entity": entity,
        })
    if not dry_run:
        response = requests.delete(
            f'{defaults["address"]}/api/v1/{defaults["subscription"]}/{group}/{entity}',
            headers={"api-key": defaults["api_key"]},
        )
        response.raise_for_status()
        if verbose:
            print(response)


@app.command()
def delete_all(
        group: Annotated[str, typer.Option("-g", "--group", help="Entity group", envvar="COMPANION_GROUP")],
        confirm: Annotated[bool, typer.Option("-y", "--yes", help="Confirm deletion")] = False,
        verbose: Annotated[
            bool, typer.Option("-v", "--verbose", help="Be verbose", envvar="COMPANION_VERBOSE")] = False,
        dry_run: Annotated[bool, typer.Option(help="Do not post http request", envvar="COMPANION_DRYRUN")] = False
):
    _check_defaults()

    if not confirm:
        delete = typer.confirm(f"Are you really sure you want to delete all the entities in group '{group}'?")
        if not delete:
            print("Not deleting")
            raise typer.Abort()

    if verbose:
        print({
            "group": group,
        })
    if not dry_run:
        response = requests.delete(
            f'{defaults["address"]}/api/v1/{defaults["subscription"]}/{group}',
            headers={"api-key": defaults["api_key"]},
        )
        response.raise_for_status()
        if verbose:
            print(response)


@app.command()
def callback(
        group: Annotated[str, typer.Option("-g", "--group", help="Entity group", envvar="COMPANION_GROUP")],
        entity: Annotated[str, typer.Option("-e", "--entity", help="Entity ID (returns state in callback)",
                                            envvar="COMPANION_ENTITY")] = None,
        filter: Annotated[Tuple[str, str, str], typer.Option("-f", "--filter",
                                                             help="Filter query. Eg: [col \"==\" value]")] = (
                None, None, None),
        when: Annotated[datetime, typer.Option("-w", "--when", help="When to call back")] = None,
        seconds: Annotated[int, typer.Option("-s", "--seconds", help="Number of seconds starting now")] = None,
        now: Annotated[bool, typer.Option("-n", "--now", help="Do it now")] = None,
        channels: Annotated[List[str], typer.Option("-c", "--channel",
                                                    help="Callback preconfigured channel name (accept multiple)",
                                                    envvar="COMPANION_CALLBACK_CHANNELS")] = None,
        replace_id: Annotated[str, typer.Option("-r", "--replace",
                                                help="If present, replace previously scheduled callbacks having this id")] = None,
        rnd_delay: Annotated[int, typer.Option("-d", "--rnd-delay", help="Add some random delay between seconds")] = 0,
        fresh: Annotated[bool, typer.Option("--fresh",
                                            help="If delayed and a group query is specified, always get fresh data before send")] = False,
        message: Annotated[
            str, typer.Argument(help="message returned in callback, json is supported, if '-' read from stdin")] = None,
        verbose: Annotated[
            bool, typer.Option("-v", "--verbose", help="Be verbose", envvar="COMPANION_VERBOSE")] = False,
        dry_run: Annotated[bool, typer.Option(help="Do not post http request", envvar="COMPANION_DRYRUN")] = False

) -> str:
    _check_defaults()

    # at least one from entity or filter (group of entities)
    filter = _validate_filter(filter)
    has_filter = filter is not None and sum(p is not None for p in filter) == 3
    # if not has_filter and entity is None:
    #     err_console.print("Entity or filter missing")
    #     raise typer.Abort()
    if has_filter and entity is not None:
        err_console.print("You can specify only one from entity or filter")
        raise typer.Abort()
    if has_filter and replace_id is not None:
        err_console.print("Cannot use replace_id with filter")
        raise typer.Abort()
    if entity and fresh:
        err_console.print("notice> option --fresh ignored for entity callback")

    tt_sum = sum(p is not None for p in [when, seconds, now])
    if tt_sum > 1:
        err_console.print("You can specify only one from --when, --seconds, --now")
        raise typer.Abort()
    if tt_sum == 0:
        now = True
    if when is not None:
        when = when.isoformat()

    if len(channels) == 0:
        err_console.print("At least one channel must be scpecified")
        raise typer.Abort()

    if message is not None and message == "-":
        message = sys.stdin.read().strip()

    if verbose:
        print({
            "group": group,
            "entity": entity,
            "filter": filter,
            "when": when,
            "seconds": seconds,
            "now": now,
            "channels": channels,
            "replace_id": replace_id,
            "rnd_delay": rnd_delay,
            "message": message,
        })

    if not dry_run:
        if entity is not None:
            response = requests.post(
                f'{defaults["address"]}/api/scheduler/v1/{defaults["subscription"]}/{group}/{entity}',
                headers={"api-key": defaults["api_key"]},
                json={
                    "seconds": seconds,
                    "now": now,
                    "when": when,
                    "rnd_delay": rnd_delay,
                    "channels": channels,
                    "replace_id": replace_id,
                    "message": message,
                }
            )
            try:
                response.raise_for_status()
            except HTTPError as ex:
                err_console.print(f"status: {ex.response.status_code}")
                try:
                    err_console.print(ex.response.json()["detail"])
                except:
                    pass
                raise typer.Abort()

            if verbose:
                print(response, response.json())
            return response.json().get("task_id")
        else:
            response = requests.post(
                f'{defaults["address"]}/api/scheduler/v1/{defaults["subscription"]}/{group}',
                headers={"api-key": defaults["api_key"]},
                json={
                    "filter": filter,
                    "seconds": seconds,
                    "now": now,
                    "when": when,
                    "rnd_delay": rnd_delay,
                    "fresh_data": fresh,
                    "channels": channels,
                    "message": message,
                }
            )
            try:
                response.raise_for_status()
            except HTTPError as ex:
                err_console.print(f"status: {ex.response.status_code}")
                try:
                    err_console.print(ex.response.json()["detail"])
                except:
                    pass
                raise typer.Abort()
            if verbose:
                print(response, response.json())

        return None


@app.command()
def version():
    from krules_companion_client import __version__
    err_console.print(__version__)


@app.callback()
def config(
        config: Annotated[Optional[Path], typer.Option(envvar="COMPANION_CONFIG",
                                                       help="Configuration file with defaults")] = DEFAULT_CONFIG_FILE,
        address: Annotated[
            Optional[str], typer.Option(envvar="COMPANION_ADDRESS", help="Backend address (override defaults)")] = None,
        subscription: Annotated[Optional[int], typer.Option(envvar="COMPANION_SUBSCRIPTION",
                                                            help="Subscription id (override defaults)")] = None,
        api_key: Annotated[Optional[str], typer.Option(envvar="COMPANION_APIKEY",
                                                       help="Authentication key (override defaults)")] = None,
):
    global defaults

    if config != DEFAULT_CONFIG_FILE and not config.exists():
        err_console.print(f"config file '{config}' does not exists")
        raise typer.Abort()
    elif config.exists() and config.is_file():
        defaults = tomli.load(config.open("rb"))

    if address is not None:
        defaults["address"] = address
    if subscription is not None:
        defaults["subscription"] = subscription
    if api_key is not None:
        defaults["api_key"] = api_key


def main():
    app()


if __name__ == "__main__":
    main()
