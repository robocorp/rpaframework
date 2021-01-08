import PyPDF2
import pytest

from . import (
    library,
    temp_filename,
    TestFiles,
)

# TODO: add tests to cover more conditions


@pytest.mark.parametrize("file, number_of_pages", [
    (TestFiles.invoice_pdf, 1),
    (TestFiles.vero_pdf, 2),
    (TestFiles.pytest_pdf, 9),
])
def test_get_number_of_pages(library, file, number_of_pages):
    assert library.get_number_of_pages(file) == number_of_pages


@pytest.mark.parametrize("file, pages, encrypted, fields", [
    (TestFiles.pytest_pdf, 9, False, False),
    (TestFiles.vero_pdf, 2, False, True),
])
def test_get_info(library, file, pages, encrypted, fields):
    info = library.get_info(file)

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
        target_pdf = tmp_file
        library.extract_pages_from_pdf(TestFiles.pytest_pdf, target_pdf, pages)
        text = library.get_text_from_pdf(target_pdf)

        assert library.get_number_of_pages(target_pdf) == 2
        assert "Plugins for Web Development" in text[1]


def test_html_to_pdf(library):
    text = "let's do some testing ÄÄ"
    html = f"<html> <body> {text} </body></html>"
    with temp_filename() as tmp_file:
        target_pdf = tmp_file
        library.html_to_pdf(html, target_pdf)
        result = library.get_text_from_pdf(target_pdf)

        assert text in result[1]


def test_page_rotate(library):
    def get_source_page(pdf_file, page_num):
        reader = PyPDF2.PdfFileReader(pdf_file)
        return reader.getPage(int(page_num))

    page_num_to_rotate = 1
    page_before_rotation = get_source_page(str(TestFiles.vero_pdf), page_num_to_rotate)

    assert page_before_rotation["/Rotate"] == 0

    with temp_filename() as tmp_file:
        library.page_rotate(page_num_to_rotate, TestFiles.vero_pdf, tmp_file)
        page_after_rotation = get_source_page(tmp_file, page_num_to_rotate)

        assert page_after_rotation["/Rotate"] == 90


def test_pdf_encrypt(library):
    with temp_filename() as tmp_file:
        library.pdf_encrypt(TestFiles.vero_pdf, tmp_file)

        assert not library.is_pdf_encrypted(TestFiles.vero_pdf)
        assert library.is_pdf_encrypted(tmp_file)


def test_pdf_decrypt(library):
    passw = "secrett"

    with temp_filename() as tmp_file:
        library.pdf_encrypt(TestFiles.vero_pdf, tmp_file, passw)

        assert library.is_pdf_encrypted(tmp_file)

        with temp_filename() as another_file:
            library.pdf_decrypt(tmp_file, another_file, passw)

            assert not library.is_pdf_encrypted(another_file)


def test_replace_text(library):
    new_text = "MORE TAXES"
    library.replace_textbox_text(
        "ILMOITA VERKOSSA\nvero.fi/omavero",
        new_text,
        source_pdf=TestFiles.vero_pdf
    )
    text = library.get_text_from_pdf()

    assert new_text in text[1]


def test_get_all_figures(library):
    pages = library.get_all_figures(source_pdf=TestFiles.vero_pdf)
    figure = pages[1][44]
    details = '<image src="Im0" width="45" height="45" />'

    assert len(pages) == 2
    assert figure.details() == details


def test_add_watermark_image_to_pdf(library):
    source_pdf = str(TestFiles.invoice_pdf)
    figures_before = library.get_all_figures(source_pdf=source_pdf)
    with temp_filename() as tmp_file:
        library.add_watermark_image_to_pdf(
            imagefile=str(TestFiles.seal_of_approval),
            target_pdf=tmp_file,
            source=source_pdf
        )
        figures_after = library.get_all_figures(source_pdf=tmp_file)

        assert len(figures_before[1]) == 1
        assert len(figures_after[1]) == 2


def test_save_pdf(library):
    with temp_filename() as tmp_file:
        library.save_pdf(TestFiles.vero_pdf, tmp_file)
        expected = library.get_text_from_pdf(TestFiles.vero_pdf)
        result = library.get_text_from_pdf(tmp_file)

        assert result == expected
