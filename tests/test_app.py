import os

from typer.testing import CliRunner

from krules_companion_client.commands import app

runner = CliRunner()

conf_args = ("--config", os.path.join(os.path.dirname(os.path.abspath(__file__)), "testconfig"))
default_args = ("--dry-run", "--verbose")

def test_publish():
    result = runner.invoke(app, [
        *conf_args, "publish", *default_args,
        "--group", "mygroup",
        "--entity", "myentity",
        "prop=myprop"]
    )
    try:
        out = eval(result.output)
    except:
        print(result.output)
        raise
    assert result.exit_code == 0
    assert out["properties"]["prop"] == "myprop"

## TODOs.........



