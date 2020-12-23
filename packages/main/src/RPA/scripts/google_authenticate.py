import argparse
import base64
import os
import pickle
import sys

from RPA.Cloud import Google


DESCRIPTION = """
Command-line utility for converting Google OAuth
authorization credentials to an access token, which can be kept
in a secret storage such as Robocorp Vault. This allows calling Google
APIs without user interaction.

example usage:
> rpa-google-oauth --credentials drive_credentials.json --service drive
"""

CREDENTIALS = """
Copy these credentials into Robocorp Vault:

-------------------------------------------
{}
-------------------------------------------
"""

SERVICE_SCOPES = {
    "drive": ["drive.appdata", "drive.file", "drive.install", "drive"],
    "apps-script": ["script.projects"],
}


def create_parser():
    parser = argparse.ArgumentParser(
        description=DESCRIPTION.strip(), formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--credentials",
        dest="credentials_file",
        default="credentials.json",
        help="project credentials file (default: %(default)s)",
    )
    parser.add_argument(
        "--scopes",
        dest="scopes",
        help="authentication scopes as comma separated list",
    )
    parser.add_argument(
        "--service",
        dest="service",
        choices=SERVICE_SCOPES.keys(),
        help="set authentication scopes for the given service",
    )
    parser.add_argument(
        "--console",
        dest="console_flow",
        action="store_true",
        help="run console based auth flow (default: %(default)s)",
    )
    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    def error(msg):
        parser.print_help()
        print(f"\nERROR: {msg}\n")
        sys.exit(1)

    if Google.GOOGLECLOUD_IMPORT_ERROR:
        error(
            "Please install the 'google' optional extra to use this script:\n"
            "> pip install rpaframework[google]"
        )

    if (
        not os.path.exists(args.credentials_file)
        or os.stat(args.credentials_file).st_size == 0
    ):
        error(f"Credentials file '{args.credentials_file}' does not exist or is empty")

    scopes = []
    if args.service and args.service in SERVICE_SCOPES:
        scopes.extend(SERVICE_SCOPES[args.service])
    if args.scopes:
        scopes.extend(args.scopes.split(","))

    if not scopes:
        error("No authentication scopes have been defined")

    uris = [f"https://www.googleapis.com/auth/{scope}" for scope in scopes]
    print("Google OAuth Flow for scopes: {}".format(", ".join(scopes)))

    flow = Google.InstalledAppFlow.from_client_secrets_file(args.credentials_file, uris)
    if args.console_flow:
        credentials = flow.run_console()
    else:
        credentials = flow.run_local_server()

    serialized = base64.b64encode(pickle.dumps(credentials)).decode("utf-8")
    print(CREDENTIALS.format(serialized))


if __name__ == "__main__":
    main()
