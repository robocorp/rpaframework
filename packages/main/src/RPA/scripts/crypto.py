import argparse
import locale
import logging
import sys
import traceback
from RPA.Crypto import Crypto, Hash, EncryptionType


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
    mxg.add_argument("-e", "--encryption-type", help="encryption type")


def load_key(args):
    """Parse encryption key arguments into a Crypto library instance."""
    lib = Crypto()

    encryption_type = EncryptionType.FERNET
    if args.encryption_type:
        encryption_type = EncryptionType[args.encryption_type]

    if args.text:
        lib.use_encryption_key(args.text, encryption_type=encryption_type)
    elif args.file:
        with open(args.file, encoding="utf-8") as infile:
            lib.use_encryption_key(infile.read(), encryption_type=encryption_type)
    elif args.secret:
        name, _, key = args.secret.partition(".")
        lib.use_encryption_key_from_vault(name, key, encryption_type=encryption_type)
    else:
        raise RuntimeError("Unhandled encryption key type")

    return lib


def read_input(path, binary=False):
    """Read input from given file path, or from stdin if not defined."""
    if path is None:
        return sys.stdin.read()

    if path == "-":
        return sys.stdin.buffer.read() if binary else sys.stdin.read()

    if binary:
        with open(path, "rb") as infile:
            return infile.read()

    with open(path, encoding=locale.getpreferredencoding(False)) as infile:
        return infile.read()


def write_output(path, data):
    """Write output to given file path, or to stdout if not defined."""
    if path is None or path == "-":
        sys.stdout.buffer.write(data)
        return

    with open(path, "wb") as outfile:
        outfile.write(data)


def key_parser(parent):
    """Create parser for 'key' subcommand."""
    parser = parent.add_parser("key", help="generate encryption key")
    parser.set_defaults(func=key_command)
    parser.add_argument("-e", "--encryption-type", help="encryption type")


def key_command(args):
    """Execute 'key' subcommand."""
    key = Crypto().generate_key(encryption_type=args.encryption_type)
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
    parser.add_argument("input", nargs="?")
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
    data = read_input(args.input)
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
    )
    parser.add_argument(
        "output",
        help="path to output file, or stdout",
        nargs="?",
    )
    key_args(parser)


def encrypt_command(args):
    """Execute 'encrypt' subcommand."""
    lib = load_key(args)
    data = read_input(args.input, binary=True)
    token = lib.encrypt_string(data, encryption_type=args.encryption_type)
    write_output(args.output, token)


def decrypt_parser(parent):
    """Create parser for 'decrypt' subcommand."""
    parser = parent.add_parser("decrypt", help="decrypt data")
    parser.set_defaults(func=decrypt_command)
    parser.add_argument(
        "input",
        help="path to input file, or stdin",
        nargs="?",
    )
    parser.add_argument(
        "output",
        help="path to output file, or stdout",
        nargs="?",
    )
    key_args(parser)


def decrypt_command(args):
    """Execute 'decrypt' subcommand."""
    lib = load_key(args)
    data = read_input(args.input, binary=True)
    token = lib.decrypt_string(
        data, encoding=None, encryption_type=args.encryption_type
    )
    write_output(args.output, token)


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
