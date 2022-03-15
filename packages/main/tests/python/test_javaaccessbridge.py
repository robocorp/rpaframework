from pathlib import Path
import pytest
import subprocess
from time import sleep

from RPA.JavaAccessBridge import JavaAccessBridge


def open_test_application():
    TESTAPP_DIR = Path(__file__).resolve().parent / ".." / "resources" / "test-app"
    subprocess.Popen(
        ["java", "-jar", TESTAPP_DIR / "BasicSwing.jar"],
        shell=True,
        cwd=TESTAPP_DIR,
        close_fds=True,
    )


@pytest.mark.skip(reason="requires windows and java with UI")
def test_typing_text():
    jab = JavaAccessBridge()
    open_test_application()
    jab.select_window("Chat Frame")
    jab.type_text("role:text", "text for the textarea", enter=True)
    jab.type_text("role:text", "text for the input field", index=1, clear=True)
    jab.click_element("role:push button and name:Send")


if __name__ == "__main__":
    javalib = JavaAccessBridge()
    sleep(5)
    javalib.select_window("Chat Frame")
    sleep(5)
    javalib.close_java_window()
