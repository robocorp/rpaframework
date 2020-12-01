import argparse
import base64
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow


SERVICE_SCOPES = {
    "drive": ["drive.appdata", "drive.file", "drive.install", "drive"],
    "apps-script": ["script.projects"],
}


def get_arguments(parser):
    parser.add_argument(
        "--credentials",
        dest="credentials_file",
        default="credentials.json",
        help="project credentials file, by default tries to access file "
        "from current directory",
    )
    parser.add_argument(
        "--scopes",
        dest="scopes",
        default=None,
        help="authentication scopes as comma separated list",
    )
    parser.add_argument(
        "--service",
        dest="service",
        default=None,
        help="set authentication scopes for the given service, "
        "supported services: drive,apps-script",
    )
    parser.add_argument(
        "--console",
        dest="console_flow",
        action="store_true",
        default=False,
        help="use to run console based auth flow",
    )
    return parser.parse_args()


def start():
    parser = argparse.ArgumentParser(description="Getting Google OAuth token")
    args = get_arguments(parser)
    if (
        not os.path.exists(args.credentials_file)
        or os.stat(args.credentials_file).st_size == 0
    ):
        print(
            "WARNING: Credentials file '%s' does not exist or is empty\n"
            % args.credentials_file
        )
        parser.print_help()
        return
    auth_scopes = []
    if args.service and args.service in SERVICE_SCOPES.keys():
        auth_scopes.extend(SERVICE_SCOPES[args.service])
    if args.scopes:
        auth_scopes.extend(args.scopes.split(","))
    if not auth_scopes:
        print("WARNING: No authentication scopes have been defined!\n")
        parser.print_help()
        return
    googlescopes = [f"https://www.googleapis.com/auth/{scope}" for scope in auth_scopes]
    print("Google OAuth Flow for scopes: %s" % (",".join(auth_scopes)))
    flow = InstalledAppFlow.from_client_secrets_file(
        args.credentials_file, googlescopes
    )
    if args.console_flow:
        credentials = flow.run_console()
    else:
        credentials = flow.run_local_server()
    print(
        "\nCopy these credentials into Robocloud Vault:\n%s%s%s"
        % (
            (40 * "-") + "\n",
            str(base64.b64encode(pickle.dumps(credentials)), "utf-8"),
            "\n" + (40 * "-") + "\n",
        )
    )
