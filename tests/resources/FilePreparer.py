import argparse
import os
from pathlib import Path


class FilePreparer:
    def fp_touch_file(self, path):
        Path(path).touch()

    def fp_change_dir(self, path):
        os.chdir(r"%s" % path)

    def fp_make_dirs(self, path):
        os.makedirs(path, exist_ok=True)

    def fp_write_file(self, path, content):
        try:
            if isinstance(content, str):
                content = content.encode("utf-8")
            with open(path, "wb") as fd:
                fd.write(content)
        except FileExistsError:
            pass

    def fp_prepare(self):
        self.fp_make_dirs("subfolder/first")
        self.fp_make_dirs("subfolder/second")
        self.fp_make_dirs("another/first")
        self.fp_make_dirs("another/second")
        self.fp_make_dirs("empty")

        self.fp_touch_file("emptyfile")
        self.fp_touch_file("notemptyfile")
        self.fp_touch_file("sorted1.test")
        self.fp_touch_file("sorted2.test")
        self.fp_touch_file("sorted3.test")
        self.fp_touch_file("subfolder/first/stuff.ext")
        self.fp_touch_file("subfolder/second/stuff.ext")
        self.fp_touch_file("another/first/noext")
        self.fp_touch_file("another/second/one")
        self.fp_touch_file("another/second/two")
        self.fp_touch_file("another/second/three")
        self.fp_touch_file("another/second/.dotfile")

        self.fp_write_file("notemptyfile", "some content here")
        self.fp_write_file("somebytes", b"\x00\x66\x6f\x6f\x00")

    def prepare_files_for_tests(self, root=os.getcwd()):
        self.fp_make_dirs(root)
        self.fp_change_dir(root)
        self.fp_prepare()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root", default=os.getcwd(), help="Root directory for mock files"
    )
    args = parser.parse_args()

    preparer = FilePreparer()
    preparer.fp_make_dirs(args.root)
    preparer.fp_change_dir(args.root)

    preparer.fp_prepare()
