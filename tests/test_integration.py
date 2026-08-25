from pathlib import Path

import pytest

from tableau_spec.analyzer import analyze
from tableau_spec.parser import parse
from tableau_spec.reporter import render

_SAMPLE_DIR = Path(__file__).resolve().parents[1] / "sample"
_SAMPLE_FILES = sorted(_SAMPLE_DIR.glob("*.twbx"))


@pytest.mark.parametrize("twbx_path", _SAMPLE_FILES, ids=[p.name for p in _SAMPLE_FILES])
def test_pipeline_on_real_sample_twbx(twbx_path):
    root = parse(twbx_path)
    spec = analyze(root)
    html_text = render(spec, twbx_path.name)

    assert root.tag == "workbook"
    assert len(spec.sheets) > 0
    assert "<html" in html_text
    assert twbx_path.name in html_text


def test_sample_directory_has_files():
    if not _SAMPLE_FILES:
        pytest.skip("sample/ 配下に .twbx ファイルがありません（各自ローカルに配置してください）")


def test_datasource_name_uses_caption_not_internal_id():
    twbx_path = next((p for p in _SAMPLE_FILES if "勤怠" in p.name), None)
    if twbx_path is None:
        pytest.skip("sample/ に勤怠管理系の .twbx がありません")

    spec = analyze(parse(twbx_path))

    ds_names = [ds.name for ds in spec.datasources]
    assert any("勤怠data" in name for name in ds_names)
    assert not any(name.startswith("federated.") for name in ds_names)


def test_calculated_field_formula_resolves_internal_reference():
    twbx_path = next((p for p in _SAMPLE_FILES if "基本パターン" in p.name), None)
    if twbx_path is None:
        pytest.skip("sample/ に基本パターン系の .twbx がありません")

    spec = analyze(parse(twbx_path))

    field = next(f for f in spec.calculated_fields if f.caption == "予実差 (売上)")
    assert "Calculation_1180787540913463296" not in field.formula
    assert "予算" in field.formula
