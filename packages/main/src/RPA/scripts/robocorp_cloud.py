from datetime import datetime, timedelta
import json
import os

import click

from robot.libraries.OperatingSystem import OperatingSystem


def run_command(command):
    ret = OperatingSystem().run(command)
    return ret


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


@click.group()
def cli() -> None:
    """
    Set development environment to use Robocorp Vault
    """


@cli.command(name="set")
def set_command():
    """Access Robocorp Vault in development enviroment """
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
        click.echo(ret)
        return
    ret = json.loads(ret)
    expiry_time = ret["when"] + timedelta(minutes=token_validity).total_seconds()

    try:
        OperatingSystem().count_files_in_directory(
            os.path.join(".", "devdata"), "env.json"
        )
        response = click.confirm(
            "Do you want to update environment variables in devdata/env.json ?",
            default=True,
        )
        if response:
            content = OperatingSystem().get_file("devdata/env.json")
            content = json.loads(content)
            content["RC_WORKSPACE_ID"] = workspace
            content["RC_API_SECRET_TOKEN"] = ret["token"]
            content["RC_API_SECRET_HOST"] = "https://api.eu1.robocloud.eu"
            with open("devdata/env.json", "w") as fout:
                fout.write(json.dumps(content, sort_keys=False, indent=4))
    except RuntimeError:
        response = click.confirm(
            "devdata/env.json does not exist - do you want to create it ?", default=True
        )
        if response:
            env_vars["RC_WORKSPACE_ID"] = workspace
            env_vars["RC_API_SECRET_TOKEN"] = ret["token"]
            env_vars["RC_API_SECRET_HOST"] = "https://api.eu1.robocloud.eu"
            OperatingSystem().create_file(
                os.path.join(".", "devdata/env.json"), json.dumps(env_vars)
            )

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
        click.echo("DEV access account does not exist. Cannot list workspaces.")


def main():
    cli()


if __name__ == "__main__":
    main()
