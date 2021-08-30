from datetime import datetime, timedelta
import json
import sys
import click

from robot.libraries.OperatingSystem import OperatingSystem
from RPA.FileSystem import FileSystem

PROD_API_URL = "https://api.eu1.robocloud.eu"


def run_command(command):
    ret = OperatingSystem().run(command)
    return ret


def output_and_exit(message, level="error"):
    bg_color = "red"
    fg_color = "white"
    msg_prefix = "Error"
    if level == "warn":
        bg_color = "yellow"
        fg_color = "black"
        msg_prefix = "Warning"
    click.secho(f"{msg_prefix}:", bg=bg_color, fg=fg_color, nl=False)
    click.echo(f" {message}")
    sys.exit(0)


def does_dev_access_account_exist():
    creds = run_command("rcc configure credentials --json")
    creds = json.loads(creds)
    return "DEV" in [ac["account"] for ac in creds]


def check_for_environment_variables():
    variables = OperatingSystem().get_environment_variables()
    env_vars = {
        "RC_API_SECRET_HOST": variables.get("RC_API_SECRET_HOST", None),
        "RC_WORKSPACE_ID": variables.get("RC_WORKSPACE_ID", None),
        "RC_API_SECRET_TOKEN": variables.get("RC_API_SECRET_TOKEN", None),
    }
    return env_vars


def ask_for_access_credentials():
    credentials_url = "https://cloud.robocorp.com/settings/access-credentials"
    open_url = click.confirm(
        f"Open {credentials_url} to add new credential?", default=True
    )
    if open_url:
        click.launch(credentials_url)
    access_credentials = click.prompt(
        "Create access credentials in https://cloud.robocorp.com "
        "and paste that here to create DEV account",
    )
    ret = run_command(f"rcc configure credentials {access_credentials} -a DEV")
    if "Error: " in ret:
        click.echo(ret)
    else:
        click.echo("OK")


def update_env_json(workspace, token):
    response = click.confirm(
        "Do you want to update environment variables in devdata/env.json ?",
        default=True,
    )
    if response:
        content = OperatingSystem().get_file("devdata/env.json")
        if len(content) == 0:
            content = {}
        else:
            try:
                content = json.loads(content)
            except json.decoder.JSONDecodeError:
                output_and_exit(
                    "Can't parse env.json contents. Check the file structure."
                )

        content["RC_WORKSPACE_ID"] = workspace
        content["RC_API_SECRET_TOKEN"] = token
        content["RC_API_SECRET_HOST"] = PROD_API_URL
        with open("devdata/env.json", "w", encoding="utf-8") as fout:
            fout.write(json.dumps(content, sort_keys=False, indent=4))


def create_env_json(workspace, token):
    response = click.confirm(
        "devdata/env.json does not exist - do you want to create it ?", default=True
    )
    if response:
        OperatingSystem().create_file("devdata/env.json")
        content = {}
        content["RC_WORKSPACE_ID"] = workspace
        content["RC_API_SECRET_TOKEN"] = token
        content["RC_API_SECRET_HOST"] = PROD_API_URL
        with open("devdata/env.json", "w", encoding="utf-8") as fout:
            fout.write(json.dumps(content, sort_keys=False, indent=4))


@click.group()
def cli() -> None:
    """
    Set development environment to use Robocorp Vault
    """


@cli.command(name="set")
def set_command():
    """Access Robocorp Vault in development enviroment"""
    click.secho("Use Robocorp Vault", fg="white", bold=True, underline=True)
    dev_account_exist = does_dev_access_account_exist()
    if dev_account_exist:
        click.echo("DEV access account already exists")
    else:
        ask_for_access_credentials()
    env_vars = check_for_environment_variables()
    workspace = click.prompt(
        "What is your workspace ID?",
        default=env_vars["RC_WORKSPACE_ID"],
        show_default=True,
    )

    # token_validity = click.prompt(
    #     "Access token validity time in minutes (max 1440 min = 24 hours)",
    #     default=1440,
    #     type=int,
    # )
    token_validity = 1440
    ret = run_command(f"rcc cloud authorize -a DEV -w {workspace} -m {token_validity}")
    if "Error:" in ret:
        output_and_exit(ret)
    ret = json.loads(ret)
    expiry_time = ret["when"] + timedelta(minutes=token_validity).total_seconds()

    json_exists = FileSystem().does_file_exist("devdata/env.json")
    if json_exists:
        update_env_json(workspace, ret["token"])
    else:
        create_env_json(workspace, ret["token"])

    click.echo(f"Token expires at {datetime.fromtimestamp(expiry_time)}")


@cli.command(name="clear")
def clear_command():
    """Clear DEV access account"""
    dev_account_exist = does_dev_access_account_exist()
    if dev_account_exist:
        response = click.confirm("Do you want to delete DEV account", default=True)
        if response:
            run_command("rcc configure credentials --delete -a DEV")
            click.echo("DEV account deleted")
    else:
        click.echo("DEV access account does not exist.")


@cli.command(name="list")
def list_command():
    """List workspaces"""
    dev_account_exist = does_dev_access_account_exist()
    if dev_account_exist:
        response = run_command("rcc cloud workspace -a DEV")
        response = json.loads(response)
        click.secho("Workspace name / ID", fg="white", bold=True, underline=True)
        for r in response:
            click.secho(f"{r['name']}", fg="bright_blue", nl=False)
            click.echo(" / ", nl=False)
            click.secho(f"{r['id']}", fg="green")
    else:
        output_and_exit(
            "DEV access account does not exist. Cannot list workspaces.", level="warn"
        )


def main():
    cli()


if __name__ == "__main__":
    main()
