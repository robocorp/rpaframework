import argparse
import logging
import sys
import traceback
from RPA.Crypto import Crypto, Hash


DESCRIPTION = """
Command-line utility for generating encryption keys, and
hashing, encrypting, and decrypting data. Commonly
used with the RPA.Crypto library.
"""


def create_parser():
    """Create argument parser with all available subcommands."""
    parser = argparse.ArgumentParser(
        description=DESCRIPTION.strip(), formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="be more talkative"
    )

    subparsers = parser.add_subparsers(title="available commands")
    key_parser(subparsers)
    hash_parser(subparsers)
    encrypt_parser(subparsers)
    decrypt_parser(subparsers)

    return parser


def key_args(parser):
    """Add common argument group for providing encryption keys."""
    key = parser.add_argument_group("encryption key arguments")
    mxg = key.add_mutually_exclusive_group(required=True)
    mxg.add_argument("-t", "--text", help="encryption key as text")
    mxg.add_argument("-f", "--file", help="encryption key as file")
    mxg.add_argument("-s", "--secret", help="encryption key as Robocorp Vault secret")


def load_key(args):
    """Parse encryption key arguments into a Crypto library instance."""
    lib = Crypto()

    if args.text:
        lib.use_encryption_key(args.text)
    elif args.file:
        with open(args.file, encoding="utf-8") as infile:
            lib.use_encryption_key(infile.read())
    elif args.secret:
        name, _, key = args.secret.partition(".")
        lib.use_encryption_key_from_vault(name, key)
    else:
        raise RuntimeError("Unhandled encryption key type")

    return lib


def key_parser(parent):
    """Create parser for 'key' subcommand."""
    parser = parent.add_parser("key", help="generate encryption key")
    parser.set_defaults(func=key_command)


def key_command(args):
    """Execute 'key' subcommand."""
    del args  # unused

    key = Crypto().generate_key()
    print(key)

    logging.warning(
        "\nNOTE: Store the generated key in a secure place!"
        "\nIf the key is lost, the encrypted data can not be recovered."
        "\nIf anyone else gains access to it, they can decrypt your data."
    )


def hash_parser(parent):
    """Create parser for 'hash' subcommand."""
    parser = parent.add_parser("hash", help="calculate hash digest")
    parser.set_defaults(func=hash_command)
    parser.add_argument(
        "input", nargs="?", type=argparse.FileType("r"), default=sys.stdin
    )
    parser.add_argument(
        "-m",
        "--method",
        choices=[h.name for h in Hash],
        default="SHA1",
        help="hashing method (default: %(default)s)",
    )


def hash_command(args):
    """Execute 'hash' subcommand."""
    method = Hash[args.method]
    data = args.input.read()
    digest = Crypto().hash_string(data, method)
    print(digest)


def encrypt_parser(parent):
    """Create parser for 'encrypt' subcommand."""
    parser = parent.add_parser("encrypt", help="encrypt data")
    parser.set_defaults(func=encrypt_command)
    parser.add_argument(
        "input",
        help="path to input file, or stdin",
        nargs="?",
        type=argparse.FileType("rb"),
        default=sys.stdin,
    )
    parser.add_argument(
        "output",
        help="path to output file, or stdout",
        nargs="?",
        type=argparse.FileType("wb"),
        default=sys.stdout.buffer,
    )
    key_args(parser)


def encrypt_command(args):
    """Execute 'encrypt' subcommand."""
    lib = load_key(args)
    token = lib.encrypt_string(args.input.read())
    args.output.write(token)


def decrypt_parser(parent):
    """Create parser for 'decrypt' subcommand."""
    parser = parent.add_parser("decrypt", help="decrypt data")
    parser.set_defaults(func=decrypt_command)
    parser.add_argument(
        "input",
        help="path to input file, or stdin",
        nargs="?",
        type=argparse.FileType("rb"),
        default=sys.stdin,
    )
    parser.add_argument(
        "output",
        help="path to output file, or stdout",
        nargs="?",
        type=argparse.FileType("wb"),
        default=sys.stdout.buffer,
    )
    key_args(parser)


def decrypt_command(args):
    """Execute 'decrypt' subcommand."""
    lib = load_key(args)
    token = lib.decrypt_string(args.input.read(), encoding=None)
    args.output.write(token)


def main():
    parser = create_parser()
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO, format="%(message)s"
    )

    try:
        args.func(args)
    except KeyboardInterrupt:
        logging.warning("Aborted by user")
        sys.exit(1)
    except Exception as exc:  # pylint: disable=broad-except
        logging.debug(traceback.format_exc())
        logging.error("Command failed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
