from contextlib import contextmanager

import PyPDF2
import pytest

from RPA.PDF.keywords.document import DocumentKeywords
from . import library, temp_filename, TestFiles


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


def test_rotate_page(library):
    def get_source_page(pdf_file, page_num):
        reader = PyPDF2.PdfFileReader(pdf_file)
        return reader.getPage(int(page_num))

    page_num_to_rotate = 1
    page_before_rotation = get_source_page(str(TestFiles.vero_pdf), page_num_to_rotate)

    assert page_before_rotation["/Rotate"] == 0

    with temp_filename() as tmp_file:
        library.rotate_page(page_num_to_rotate, TestFiles.vero_pdf, tmp_file)
        page_after_rotation = get_source_page(tmp_file, page_num_to_rotate)

        assert page_after_rotation["/Rotate"] == 90


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
            PyPDF2.PdfFileReader(str(TestFiles.loremipsum_pdf)),
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
