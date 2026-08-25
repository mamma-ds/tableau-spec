from pathlib import Path

import pytest

from tableau_spec.parser import ParseError
from tableau_spec.webapp import _estimate_fragment_height, analyze_upload, generate_html

_SAMPLE_DIR = Path(__file__).resolve().parents[1] / "sample"
_SAMPLE_FILES = sorted(_SAMPLE_DIR.glob("*.twbx"))


@pytest.mark.parametrize("twbx_path", _SAMPLE_FILES, ids=[p.name for p in _SAMPLE_FILES])
def test_generate_html_from_uploaded_bytes(twbx_path):
    html_text = generate_html(twbx_path.read_bytes(), twbx_path.name)

    assert "<html" in html_text
    assert twbx_path.name in html_text


def test_generate_html_raises_parse_error_for_invalid_bytes():
    with pytest.raises(ParseError):
        generate_html(b"not a real workbook", "broken.twbx")


@pytest.mark.parametrize("twbx_path", _SAMPLE_FILES, ids=[p.name for p in _SAMPLE_FILES])
def test_analyze_upload_returns_spec_with_sheets(twbx_path):
    spec = analyze_upload(twbx_path.read_bytes(), twbx_path.name)

    assert len(spec.sheets) > 0


def test_estimate_fragment_height_grows_with_content():
    small = "<section><table><tr><td>a</td></tr></table></section>"
    large = "<section>" + "<table>" + "<tr><td>a</td></tr>" * 50 + "</table></section>"

    assert _estimate_fragment_height(large) > _estimate_fragment_height(small)


def test_estimate_fragment_height_has_a_floor_for_empty_content():
    assert _estimate_fragment_height("") >= 200
