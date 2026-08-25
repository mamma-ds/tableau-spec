import xml.etree.ElementTree as ET
import zipfile

import pytest

from tableau_spec.parser import ParseError, parse

_SIMPLE_TWB = "<workbook version='18.1'><datasources /></workbook>"


def _make_twbx(tmp_path, twb_filename="workbook.twb", twb_content=_SIMPLE_TWB):
    twbx_path = tmp_path / "sample.twbx"
    with zipfile.ZipFile(twbx_path, "w") as z:
        z.writestr(twb_filename, twb_content)
    return twbx_path


def test_parse_twb_returns_root_element(tmp_path):
    twb_path = tmp_path / "sample.twb"
    twb_path.write_text(_SIMPLE_TWB, encoding="utf-8")

    root = parse(twb_path)

    assert isinstance(root, ET.Element)
    assert root.tag == "workbook"


def test_parse_twbx_returns_root_element(tmp_path):
    twbx_path = _make_twbx(tmp_path)

    root = parse(twbx_path)

    assert isinstance(root, ET.Element)
    assert root.tag == "workbook"


def test_parse_nonexistent_file_raises_parse_error(tmp_path):
    missing = tmp_path / "missing.twb"

    with pytest.raises(ParseError):
        parse(missing)


def test_parse_invalid_xml_raises_parse_error(tmp_path):
    twb_path = tmp_path / "broken.twb"
    twb_path.write_text("<workbook><unclosed>", encoding="utf-8")

    with pytest.raises(ParseError):
        parse(twb_path)


def test_parse_empty_twbx_raises_parse_error(tmp_path):
    twbx_path = tmp_path / "empty.twbx"
    with zipfile.ZipFile(twbx_path, "w") as z:
        z.writestr("Data/sample.hyper", b"")

    with pytest.raises(ParseError):
        parse(twbx_path)


def test_parse_unsupported_extension_raises_parse_error(tmp_path):
    other = tmp_path / "sample.txt"
    other.write_text("not a workbook", encoding="utf-8")

    with pytest.raises(ParseError):
        parse(other)
