import io

from docx import Document

from resume import extract_resume_text


def test_txt_resume_is_read():
    text = extract_resume_text(
        "cv.txt",
        b"B.Tech ECE student. Skills: Python, React. Interested in AI.",
    )

    assert "B.Tech ECE" in text
    assert "Python" in text


def test_docx_resume_is_read():
    document = Document()
    document.add_paragraph(
        "B.Tech Computer Science student with Python and machine learning "
        "experience."
    )
    buffer = io.BytesIO()
    document.save(buffer)

    text = extract_resume_text("cv.docx", buffer.getvalue())

    assert "Computer Science" in text
    assert "machine learning" in text


def test_unsupported_file_is_rejected():
    try:
        extract_resume_text("photo.png", b"not a resume")
    except ValueError as error:
        assert "PDF, DOCX, or TXT" in str(error)
    else:
        raise AssertionError("Unsupported file was accepted.")


def test_short_text_is_rejected():
    try:
        extract_resume_text("cv.txt", b"too short")
    except ValueError as error:
        assert "not contain enough readable text" in str(error)
    else:
        raise AssertionError("Short text was accepted.")