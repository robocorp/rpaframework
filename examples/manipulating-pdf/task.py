import logging
from pathlib import Path
import re
import sys

from RPA.PDF import PDF

library = None
stdout = logging.StreamHandler(sys.stdout)

logging.basicConfig(
    level=logging.INFO,
    format="[{%(filename)s:%(lineno)d} %(levelname)s - %(message)s",
    handlers=[stdout],
)

LOGGER = logging.getLogger(__name__)


def get_values_from_box():
    values = library.get_value_from_anchor(
        "coords:345,645,520,725", direction="box", only_closest=False
    )
    for item in values:
        LOGGER.info("%s %s" % (item.text, item.bbox))


def get_values_by_label():
    LOGGER.info("Invoice Date: %s" % library.get_value_from_anchor("Invoice Date"))
    LOGGER.info("Order Number: %s" % library.get_value_from_anchor("text:Order Number"))
    LOGGER.info(
        "Rate/Price: %s"
        % library.get_value_from_anchor("text:Rate/Price", direction="down")
    )
    LOGGER.info("Total: %s" % library.get_value_from_anchor("text:Total"))


def get_text_from_pdf():
    regex = r".*\@.*\..*"
    pages = library.get_text_from_pdf(details=True)
    for page in pages:
        for item in pages[page]:
            matches = re.findall(regex, item.text)
            if len(matches) > 0:
                LOGGER.info(matches)


def main():
    filename = Path(__file__).parent / "invoice.pdf"
    library.open_pdf_document(filename)
    get_values_from_box()
    get_values_by_label()
    get_text_from_pdf()


if __name__ == "__main__":
    library = PDF()
    try:
        main()
    finally:
        library.close_all_pdf_documents()
