"""Streamlit を用いた Web UI（アップロード処理・起動）のみを担当する。"""

from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from pathlib import Path

from tableau_spec.analyzer import WorkbookSpec, analyze
from tableau_spec.parser import ParseError, parse
from tableau_spec.reporter import MENU, embed_style, render, render_groups

_ROW_HEIGHT_PX = 42
_TREE_ITEM_HEIGHT_PX = 26
_SECTION_OVERHEAD_PX = 90
_MIN_HEIGHT_PX = 200

_AUTO_RESIZE_SCRIPT = """
<script>
(function () {
  function resize() {
    var height = document.documentElement.scrollHeight;
    try {
      if (window.frameElement) {
        window.frameElement.style.height = height + 'px';
      }
    } catch (e) {}
    try {
      window.parent.postMessage({ type: 'streamlit:setFrameHeight', height: height }, '*');
    } catch (e) {}
  }
  window.addEventListener('load', resize);
  new ResizeObserver(resize).observe(document.body);
  resize();
  setTimeout(resize, 150);
})();
</script>
"""


def _estimate_fragment_height(fragment_html: str) -> int:
    """HTMLフラグメント内の行数・ツリー項目数から、埋め込みiframeの初期高さ(px)を求める。
    実際の高さは _AUTO_RESIZE_SCRIPT が描画後に測定して自動調整するため、これは初期表示のフォールバック値。"""
    sections = len(re.findall(r"<section", fragment_html))
    rows = len(re.findall(r"<tr>", fragment_html))
    tree_items = len(re.findall(r"<li", fragment_html))
    height = sections * _SECTION_OVERHEAD_PX + rows * _ROW_HEIGHT_PX + tree_items * _TREE_ITEM_HEIGHT_PX
    return max(height, _MIN_HEIGHT_PX)


def analyze_upload(file_bytes: bytes, filename: str) -> WorkbookSpec:
    """アップロードされたファイルのバイト列を解析し WorkbookSpec を返す。"""
    suffix = Path(filename).suffix
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = Path(tmp.name)
    try:
        root = parse(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
    return analyze(root)


def generate_html(file_bytes: bytes, filename: str) -> str:
    """アップロードされたファイルのバイト列から HTML 仕様書文字列を生成する。"""
    return render(analyze_upload(file_bytes, filename), filename)


def _run_app() -> None:
    import streamlit as st

    st.set_page_config(page_title="Tableau仕様書生成ツール", layout="wide")
    st.markdown(
        "<style>"
        "[data-testid='StyledFullScreenButton'] { display: none; }"
        "header[data-testid='stHeader'] { display: none; }"
        "#MainMenu { visibility: hidden; }"
        "</style>",
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.title("Tableau仕様書生成ツール")
        uploaded = st.file_uploader(".twb / .twbx をドラッグ＆ドロップ", type=["twb", "twbx"])

        selected_key = MENU[0][0]
        dependency_search = ""
        fields_search = ""
        if uploaded is not None:
            selected_key = st.radio(
                "表示切替",
                [key for key, _ in MENU],
                format_func=dict(MENU).get,
            )
            if selected_key == "dependency_tree":
                dependency_search = st.text_input(
                    "検索（シート／フィールド／計算フィールド／パラメータ名）",
                    placeholder="例: 利益率",
                )
            elif selected_key == "calculated_parameters":
                fields_search = st.text_input(
                    "検索（フィールド／計算フィールド／パラメータ／セット名）",
                    placeholder="例: 利益率",
                )

    if uploaded is None:
        st.info(".twb または .twbx ファイルをサイドバーにドラッグ＆ドロップしてください。")
        return

    try:
        spec = analyze_upload(uploaded.getvalue(), uploaded.name)
    except ParseError as e:
        st.error(f"エラー: {e}")
        return

    st.download_button(
        "HTMLをダウンロード",
        data=render(spec, uploaded.name),
        file_name=Path(uploaded.name).stem + ".html",
        mime="text/html",
    )

    fragment = render_groups(spec, uploaded.name, dependency_search, fields_search)[selected_key]
    page = (
        "<!DOCTYPE html><html><head><meta charset='utf-8' />"
        f"{embed_style()}</head>"
        f"<body style='margin:0'><div class='tableau-spec-embed'>{fragment}</div>"
        f"{_AUTO_RESIZE_SCRIPT}</body></html>"
    )
    st.components.v1.html(page, height=_estimate_fragment_height(fragment), scrolling=True)


def run_web() -> None:
    """`tableau-spec-web` コマンドから呼ばれ、streamlit run でこのファイル自身を起動する。"""
    app_path = Path(__file__).resolve()
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)], check=False)


if __name__ == "__main__":
    _run_app()
