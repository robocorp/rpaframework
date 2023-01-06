import shutil
from contextlib import contextmanager

import pytest

from RPA.PDF.keywords.document import DocumentKeywords
from RPA.PDF.keywords.model import RobocorpPdfReader

from . import TestFiles, library, temp_filename


@contextmanager
def does_not_raise():
    yield


@pytest.mark.parametrize(
    "file, number_of_pages",
    [
        (TestFiles.invoice_pdf, 1),
        (TestFiles.vero_pdf, 2),
        (TestFiles.pytest_pdf, 9),
    ],
)
def test_get_number_of_pages(library, file, number_of_pages):
    assert library.get_number_of_pages(file) == number_of_pages


@pytest.mark.parametrize(
    "file, pages, encrypted, fields",
    [
        (TestFiles.pytest_pdf, 9, False, False),
        (TestFiles.vero_pdf, 2, False, True),
    ],
)
def test_get_pdf_info(library, file, pages, encrypted, fields):
    info = library.get_pdf_info(file)

    assert info["Pages"] == pages
    assert info["Encrypted"] == encrypted
    assert info["Fields"] == fields


def test_is_pdf_encrypted(library):
    assert not library.is_pdf_encrypted(TestFiles.vero_pdf)


def test_get_text_from_pdf_all_one_page(library):
    pages = library.get_text_from_pdf(TestFiles.loremipsum_pdf)

    assert len(pages) == 1
    assert len(pages[1]) == 3622


def test_get_text_from_pdf_all_two_pages(library):
    pages = library.get_text_from_pdf(TestFiles.vero_pdf)

    assert len(pages) == 2
    assert "Muualle lomakkeeseen kirjoittamaasi tietoa ei käsitellä." in pages[2]


def test_get_text_from_pdf_specific_page(library):
    text = library.get_text_from_pdf(TestFiles.pytest_pdf, pages=[7])

    assert "Plugins for Web Development" in text[7]


def test_extract_pages_from_pdf(library):
    pages = [7, 8]
    with temp_filename() as tmp_file:
        library.extract_pages_from_pdf(TestFiles.pytest_pdf, tmp_file, pages)
        text = library.get_text_from_pdf(tmp_file)

        assert library.get_number_of_pages(tmp_file) == 2
        assert "Plugins for Web Development" in text[1]


@pytest.mark.parametrize(
    "text,encoding",
    [
        ("let's do some testing ÄÄ", "latin-1"),
        ("let's do some testing ÄÄ", "utf-8"),
        ("Who's Poieană?", "latin-1"),
        ("Who's Poieană?", "utf-8"),
        ("Who's Poieană ĄĆĘŁŃÓŚŹŻąćęłńóśźż?", None),
    ],
)
def test_html_to_pdf(library, text, encoding):
    html = (
        f"<html> <body> <b>bold</b> <b><i>{text}</i></b> <i>italic</i> </body></html>"
    )
    with temp_filename() as tmp_file:
        library.html_to_pdf(html, tmp_file, encoding=encoding)
        result = library.get_text_from_pdf(tmp_file)[1]

    assert text in result


def _get_source_pages(pdf_file, page_nums):
    reader = RobocorpPdfReader(pdf_file)
    if not page_nums:
        return reader.pages

    return [reader.pages[page] for page in page_nums]


@pytest.mark.parametrize(
    "pages, internal_pages, clockwise",
    [
        (1, [0], True),
        (1, [0], False),
        (
            0,
            [0, 1],
            True,
        ),  # 0 is considered null, thus all pages are taken into account
        ("1", [0], True),  # string index
        ("1,2", [0, 1], False),  # string range
        ("2", [1], True),  # string index, last page
        (3, [], True),  # no pages to rotate, so all remain the same
        ([2, 1], [0, 1], False),  # list of integers
    ],
)
def test_rotate_page(library, pages, internal_pages, clockwise):
    pages_before_rotation = _get_source_pages(str(TestFiles.vero_pdf), internal_pages)
    before_obtained = [page["/Rotate"] for page in pages_before_rotation]
    before_expected = [0] * (len(internal_pages) or len(pages_before_rotation))
    assert before_obtained == before_expected

    with temp_filename(suffix="-rotated.pdf") as tmp_file:
        library.rotate_page(pages, TestFiles.vero_pdf, tmp_file, clockwise=clockwise)
        pages_after_rotation = _get_source_pages(tmp_file, internal_pages)
        after_obtained = [page["/Rotate"] for page in pages_after_rotation]
        after_expected = (
            [90 * (1 if clockwise else -1)] * len(internal_pages)
            if internal_pages
            else [0] * len(after_obtained)
        )
        assert after_expected  # ensuring we don't end up with an empty list
        assert after_obtained == after_expected


def test_encrypt_pdf(library):
    with temp_filename() as tmp_file:
        library.encrypt_pdf(TestFiles.vero_pdf, tmp_file)

        assert not library.is_pdf_encrypted(TestFiles.vero_pdf)
        assert library.is_pdf_encrypted(tmp_file)


def test_decrypt_pdf(library):
    passw = "secrett"
    assert not library.is_pdf_encrypted(TestFiles.vero_pdf)

    with temp_filename(suffix="-enc.pdf") as encrypted_pdf:
        library.encrypt_pdf(TestFiles.vero_pdf, encrypted_pdf, passw)
        assert library.is_pdf_encrypted(encrypted_pdf)

        with temp_filename(suffix="-dec.pdf") as decrypted_pdf:
            with pytest.raises(ValueError):
                library.decrypt_pdf(encrypted_pdf, decrypted_pdf, passw + "extra")

            library.decrypt_pdf(encrypted_pdf, decrypted_pdf, passw)
            assert not library.is_pdf_encrypted(decrypted_pdf)
            assert (
                not library.is_pdf_encrypted()
            )  # the very same active document as above
            assert library.is_pdf_encrypted(encrypted_pdf)


@pytest.mark.skip(reason="replacing text in PDF is missing")
def test_replace_text(library):
    new_text = "a company name"
    library.replace_text("Test Business", new_text, source_path=TestFiles.invoice_pdf)
    # TODO: this should replace text in the original PDF
    # file without breaking anything.


def test_get_all_figures(library):
    pages = library.get_all_figures(source_path=TestFiles.vero_pdf)
    figure = pages[1][44]
    details = '<image src="Im0" width="45" height="45" />'

    assert len(pages) == 2
    assert str(figure) == details


@pytest.mark.parametrize(
    "watermark_image",
    [
        (TestFiles.seal_of_approval),
        (TestFiles.big_nope),
    ],
)
def test_add_watermark_image_to_pdf(library, watermark_image):
    source_path = str(TestFiles.invoice_pdf)
    figures_before = library.get_all_figures(source_path=source_path)
    with temp_filename() as tmp_file:
        library.add_watermark_image_to_pdf(
            image_path=str(watermark_image),
            output_path=tmp_file,
            source_path=source_path,
        )
        figures_after = library.get_all_figures(source_path=tmp_file)

        assert len(figures_before[1]) == 1
        assert len(figures_after[1]) == 2


def test_add_watermark_image_to_same_pdf(library):
    with temp_filename(suffix="-receipt.pdf") as receipt_pdf:
        shutil.copyfile(TestFiles.receipt_pdf, receipt_pdf)
        library.add_watermark_image_to_pdf(
            image_path=TestFiles.robot_png,
            # Use same file source for both input and output.
            output_path=receipt_pdf,
            source_path=receipt_pdf,
        )
        figures = library.get_all_figures(source_path=receipt_pdf)
        assert len(figures[1]) == 1  # means watermarking finished successfully


@pytest.mark.parametrize(
    "width, height, exp_width, exp_height",
    [
        (50, 50, 50, 50),
        (200, 50, 119, 29),
        (100, 200, 84, 168),
        (200, 200, 119, 119),
        (150, 1000, 25, 168),
        (1000, 200, 119, 23),
        (1500, 100, 119, 7),
        (100, 1000, 16, 168),
        (200, 2000, 16, 168),
    ],
)
def test_fit_dimensions_to_box(width, height, exp_width, exp_height):
    max_width = 119
    max_height = 168
    fitted_width, fitted_height = DocumentKeywords.fit_dimensions_to_box(
        width, height, max_width, max_height
    )

    def assert_ratios_more_or_less_the_same():
        ratio = width / height
        fitted_ratio = fitted_width / fitted_height
        accepted_error = 0.2

        assert abs(1 - ratio / fitted_ratio) < accepted_error

    assert_ratios_more_or_less_the_same()
    assert fitted_width <= max_width
    assert fitted_height <= max_height
    assert fitted_width == exp_width
    assert fitted_height == exp_height


def test_close_pdf(library):
    library.open_pdf(TestFiles.vero_pdf)

    assert library.active_pdf_document

    library.close_pdf(TestFiles.vero_pdf)

    assert not library.active_pdf_document


def test_close_all_pdfs(library):
    library.open_pdf(TestFiles.vero_pdf)

    assert library.active_pdf_document.path == str(TestFiles.vero_pdf)

    library.open_pdf(TestFiles.loremipsum_pdf)

    assert library.active_pdf_document.path == str(TestFiles.loremipsum_pdf)

    library.close_all_pdfs()

    assert not library.active_pdf_document


@pytest.mark.parametrize(
    "pages, reader, expected_value, expected_behaviour",
    [
        ([1], None, [1], does_not_raise()),
        ([1, 2, 3], None, [1, 2, 3], does_not_raise()),
        (1, None, [1], does_not_raise()),
        ("1", None, [1], does_not_raise()),
        ("1,2,3", None, [1, 2, 3], does_not_raise()),
        (
            None,
            RobocorpPdfReader(str(TestFiles.loremipsum_pdf)),
            [1],
            does_not_raise(),
        ),
        (None, None, None, pytest.raises(ValueError)),
    ],
)
def test_get_page_numbers(pages, reader, expected_value, expected_behaviour):
    with expected_behaviour:
        result = DocumentKeywords._get_page_numbers(pages, reader)

        assert result == expected_value


def test_get_text_from_pdf_all_one_page_after_line_margin_is_set(library):
    library.set_convert_settings(line_margin=0.00000001)
    pages = library.get_text_from_pdf(TestFiles.loremipsum_pdf)

    assert len(pages) == 1
    assert len(pages[1]) == 3556
