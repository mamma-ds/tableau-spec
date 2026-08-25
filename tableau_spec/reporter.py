"""WorkbookSpec から HTML 仕様書文字列を生成する。ファイル書き込みは行わない。"""

from __future__ import annotations

import html
import re
from datetime import datetime

from tableau_spec.analyzer import CalculatedField, WorkbookSpec

_HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{3,8}$")

MENU: tuple[tuple[str, str], ...] = (
    ("overview_datasources", "概要・データソース"),
    ("calculated_parameters", "フィールド・計算フィールド／パラメータ"),
    ("sheets_dashboards", "ダッシュボード一覧／シート一覧"),
    ("dependency_tree", "依存関係ツリー"),
)

_ROOT_VARS = """
:root {
  --bg: #0f172a;
  --bg-panel: #1e293b;
  --fg: #e2e8f0;
  --accent: #38bdf8;
  --accent-lod: #f97316;
  --accent-calc: #a78bfa;
  --accent-param: #facc15;
  --border: #334155;
  --row-alt: #18233a;
}
"""

_COMPONENT_STYLE = """
h1, h2 { color: var(--accent); }
table { border-collapse: collapse; width: 100%; margin-bottom: 1.5rem; }
th, td { border: 1px solid var(--border); padding: 0.4rem 0.6rem; text-align: left; }
tr:nth-child(even) { background: var(--row-alt); }
pre { white-space: pre-wrap; word-break: break-word; margin: 0; }
.badge-lod {
  background: var(--accent-lod);
  color: #0f172a;
  border-radius: 0.3rem;
  padding: 0.1rem 0.4rem;
  font-size: 0.75rem;
  margin-left: 0.4rem;
}
section { background: var(--bg-panel); border-radius: 0.5rem; padding: 1rem 1.5rem; margin-bottom: 1.5rem; }
details summary { cursor: pointer; color: var(--accent); }
.color-swatch {
  display: inline-block;
  width: 0.8rem;
  height: 0.8rem;
  border-radius: 0.2rem;
  margin-right: 0.4rem;
  vertical-align: middle;
}
ul.dep-tree, ul.dep-tree ul {
  list-style: disc;
  margin: 0.2rem 0 0.2rem 1.4rem;
  padding: 0;
}
.dep-sheet { color: var(--accent); font-weight: bold; }
.dep-calc { color: var(--accent-calc); }
.dep-param { color: var(--accent-param); font-style: italic; }
.dep-field { color: var(--fg); }
.dep-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem;
  margin-bottom: 0.8rem;
  font-size: 0.85rem;
  color: var(--fg);
}
.dep-legend-item { display: inline-flex; align-items: center; }
.dep-swatch {
  width: 0.7rem;
  height: 0.7rem;
  border-radius: 50%;
  display: inline-block;
  margin-right: 0.35rem;
  background: currentColor;
}
.dep-label[title] { cursor: help; border-bottom: 1px dotted currentColor; }
.dep-shelf { color: var(--fg); opacity: 0.65; font-size: 0.8rem; margin-left: 0.3rem; }
mark {
  background: var(--accent-param);
  color: #1a1300;
  padding: 0 0.15rem;
  border-radius: 0.15rem;
}
.tw-tabs { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1.5rem; }
.tw-tab-btn {
  background: var(--bg-panel);
  color: var(--fg);
  border: 1px solid var(--border);
  border-radius: 0.4rem;
  padding: 0.5rem 1rem;
  cursor: pointer;
  font-size: 0.95rem;
}
.tw-tab-btn.active { background: var(--accent); color: #0f172a; font-weight: bold; border-color: var(--accent); }
.tw-panel[hidden] { display: none; }
.tw-search {
  display: block;
  width: 100%;
  max-width: 28rem;
  padding: 0.5rem 0.7rem;
  margin-bottom: 1rem;
  border-radius: 0.4rem;
  border: 1px solid var(--border);
  background: var(--bg-panel);
  color: var(--fg);
  font-size: 0.95rem;
}
"""

_STYLE = (
    _ROOT_VARS
    + "body { background: var(--bg); color: var(--fg); font-family: sans-serif; margin: 2rem; }\n"
    + _COMPONENT_STYLE
)

_EMBED_STYLE = (
    _ROOT_VARS
    + ".tableau-spec-embed { background: var(--bg); color: var(--fg); font-family: sans-serif;"
    " padding: 1.5rem; border-radius: 0.5rem; }\n"
    + _COMPONENT_STYLE
)


def _color_swatch(color: str) -> str:
    if not color or not _HEX_COLOR_PATTERN.match(color):
        return ""
    return f"<span class='color-swatch' style='background:{color}'></span>"


_TAB_SEARCH_INPUTS = {
    "calculated_parameters": (
        "<input type='search' class='tw-search' "
        "placeholder='検索（フィールド／計算フィールド／パラメータ／セット名）' "
        "oninput=\"twFilterFieldTables(this.value)\" />"
    ),
    "dependency_tree": (
        "<input type='search' class='tw-search' "
        "placeholder='検索（シート／フィールド／計算フィールド／パラメータ名）' "
        "oninput=\"twFilterTree(this.value)\" />"
    ),
}

_TAB_SCRIPT = """
function twShowTab(key) {
  document.querySelectorAll('.tw-panel').forEach(function (p) {
    p.hidden = p.id !== 'tw-panel-' + key;
  });
  document.querySelectorAll('.tw-tab-btn').forEach(function (b) {
    b.classList.toggle('active', b.dataset.tab === key);
  });
}
function twFilterFieldTables(query) {
  var q = query.trim().toLowerCase();
  var panel = document.getElementById('tw-panel-calculated_parameters');
  if (!panel) { return; }
  panel.querySelectorAll('table').forEach(function (table) {
    table.querySelectorAll('tr').forEach(function (tr, i) {
      if (i === 0) { return; }
      var cell = tr.cells[0];
      var text = cell ? cell.textContent.toLowerCase() : '';
      tr.style.display = (q === '' || text.indexOf(q) !== -1) ? '' : 'none';
    });
  });
}
function twFilterTree(query) {
  var q = query.trim().toLowerCase();
  var panel = document.getElementById('tw-panel-dependency_tree');
  if (!panel) { return; }
  panel.querySelectorAll('ul.dep-tree > li').forEach(function (li) {
    var text = li.textContent.toLowerCase();
    li.style.display = (q === '' || text.indexOf(q) !== -1) ? '' : 'none';
  });
}
"""


def render(spec: WorkbookSpec, source_name: str) -> str:
    """WorkbookSpec を、タブ切り替え・検索機能付きの単一 HTML 文字列に変換する。"""
    groups = render_groups(spec, source_name)
    nav = "".join(
        f"<button type='button' class='tw-tab-btn{' active' if i == 0 else ''}' "
        f"data-tab='{key}' onclick=\"twShowTab('{key}')\">{html.escape(label)}</button>"
        for i, (key, label) in enumerate(MENU)
    )
    panels = "".join(
        f"<div id='tw-panel-{key}' class='tw-panel'{'' if i == 0 else ' hidden'}>"
        f"{_TAB_SEARCH_INPUTS.get(key, '')}{groups[key]}</div>"
        for i, (key, _label) in enumerate(MENU)
    )
    body = f"<nav class='tw-tabs'>{nav}</nav>\n{panels}"
    return (
        "<!DOCTYPE html>\n"
        "<html lang='ja'>\n<head>\n"
        "<meta charset='utf-8' />\n"
        f"<title>{html.escape(source_name)} 仕様書</title>\n"
        f"<style>{_STYLE}</style>\n"
        f"<script>{_TAB_SCRIPT}</script>\n"
        "</head>\n<body>\n"
        f"{body}\n"
        "</body>\n</html>\n"
    )


def render_groups(
    spec: WorkbookSpec,
    source_name: str,
    dependency_search: str = "",
    fields_search: str = "",
) -> dict[str, str]:
    """メニュー切り替え表示用に、意味のあるまとまりごとの HTML フラグメントを返す。
    dependency_search を指定すると、依存関係ツリーをシート／フィールド／計算フィールド／
    パラメータ名で絞り込む。fields_search を指定すると、フィールド一覧／計算フィールド／
    パラメーター／セットの各表をフィールド名で絞り込む。"""
    return {
        "overview_datasources": (
            _render_overview(spec, source_name) + _render_datasources(spec) + _render_joins(spec)
        ),
        "calculated_parameters": (
            _render_fields(spec, fields_search)
            + _render_calculated_fields(spec, fields_search)
            + _render_parameters(spec, fields_search)
            + _render_sets(spec, fields_search)
            + _render_unused_fields(spec, fields_search)
        ),
        "sheets_dashboards": _render_dashboards(spec) + _render_sheets(spec),
        "dependency_tree": _render_dependency_tree(spec, dependency_search),
    }


def _build_field_usage_map(spec: WorkbookSpec) -> dict[str, list[str]]:
    """フィールド／計算フィールドの表示名 → 使用しているシート名一覧の対応表を作る。"""
    usage: dict[str, list[str]] = {}
    for s in spec.sheets:
        for name in list(s.used_fields) + list(s.used_calculated_fields):
            usage.setdefault(name, []).append(s.name)
    return usage


def embed_style() -> str:
    """render_groups() のフラグメントを他のページに埋め込む際に使う、スコープ付きの<style>タグを返す。"""
    return f"<style>{_EMBED_STYLE}</style>"


def _render_overview(spec: WorkbookSpec, source_name: str) -> str:
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "<section>\n<h1>概要</h1>\n<table>\n"
        f"<tr><th>ファイル名</th><td>{html.escape(source_name)}</td></tr>\n"
        f"<tr><th>生成日時</th><td>{generated_at}</td></tr>\n"
        f"<tr><th>データソース数</th><td>{len(spec.datasources)}</td></tr>\n"
        f"<tr><th>計算フィールド数</th><td>{len(spec.calculated_fields)}</td></tr>\n"
        f"<tr><th>パラメーター数</th><td>{len(spec.parameters)}</td></tr>\n"
        f"<tr><th>シート数</th><td>{len(spec.sheets)}</td></tr>\n"
        f"<tr><th>ダッシュボード数</th><td>{len(spec.dashboards)}</td></tr>\n"
        "</table>\n</section>"
    )


def _render_datasources(spec: WorkbookSpec) -> str:
    rows = []
    for ds in spec.datasources:
        tables = "、".join(html.escape(t.table or t.name) for t in ds.tables) or "-"
        sql_html = "-"
        if ds.custom_sql:
            sql_blocks = "".join(
                f"<details><summary>カスタムSQL {i + 1}</summary><pre>{html.escape(sql)}</pre></details>"
                for i, sql in enumerate(ds.custom_sql)
            )
            sql_html = sql_blocks
        rows.append(
            "<tr>"
            f"<td>{html.escape(ds.name)}</td>"
            f"<td>{html.escape(ds.connection_class)}</td>"
            f"<td>{tables}</td>"
            f"<td>{sql_html}</td>"
            "</tr>"
        )
    table_html = (
        "<table><tr><th>データソース名</th><th>接続種別</th><th>テーブル</th><th>カスタムSQL</th></tr>"
        + "".join(rows)
        + "</table>"
        if rows
        else "<p>データソースはありません。</p>"
    )
    return f"<section>\n<h2>データソース</h2>\n{table_html}\n</section>"


def _render_joins(spec: WorkbookSpec) -> str:
    rows = []
    for ds in spec.datasources:
        for j in ds.joins:
            condition = html.escape(j.condition) if j.condition else "-"
            rows.append(
                "<tr>"
                f"<td>{html.escape(ds.name)}</td>"
                f"<td>{html.escape(j.left_table)}</td>"
                f"<td>{html.escape(j.join_type)}</td>"
                f"<td>{html.escape(j.right_table)}</td>"
                f"<td>{condition}</td>"
                "</tr>"
            )
    table_html = (
        "<table><tr><th>データソース</th><th>テーブル1</th><th>結合種別</th>"
        "<th>テーブル2</th><th>結合条件</th></tr>" + "".join(rows) + "</table>"
        if rows
        else "<p>テーブル結合はありません。</p>"
    )
    return f"<section>\n<h2>テーブル結合</h2>\n{table_html}\n</section>"


def _highlight_if_match(name: str, normalized_query: str) -> str:
    escaped = html.escape(name)
    return f"<mark>{escaped}</mark>" if _node_matches(name, normalized_query) else escaped


def _render_fields(spec: WorkbookSpec, search: str = "") -> str:
    normalized_query = search.strip().casefold()
    usage = _build_field_usage_map(spec)
    field_names = sorted({name for s in spec.sheets for name in s.used_fields})
    if normalized_query:
        field_names = [n for n in field_names if _node_matches(n, normalized_query)]
    rows = []
    for name in field_names:
        used_sheets = "、".join(html.escape(s) for s in usage.get(name, [])) or "-"
        rows.append(f"<tr><td>{_highlight_if_match(name, normalized_query)}</td><td>{used_sheets}</td></tr>")
    if rows:
        table_html = "<table><tr><th>フィールド名</th><th>使用シート</th></tr>" + "".join(rows) + "</table>"
    elif normalized_query:
        table_html = "<p>検索条件に一致するフィールドがありません。</p>"
    else:
        table_html = "<p>フィールドはありません。</p>"
    return f"<section>\n<h2>フィールド一覧</h2>\n{table_html}\n</section>"


def _render_calculated_fields(spec: WorkbookSpec, search: str = "") -> str:
    normalized_query = search.strip().casefold()
    usage = _build_field_usage_map(spec)
    calc_fields = spec.calculated_fields
    if normalized_query:
        calc_fields = [f for f in calc_fields if _node_matches(f.caption, normalized_query)]
    rows = []
    for f in calc_fields:
        badge = "<span class='badge-lod'>LOD</span>" if f.is_lod else ""
        used_sheets = "、".join(html.escape(s) for s in usage.get(f.caption, [])) or "-"
        rows.append(
            "<tr>"
            f"<td>{_highlight_if_match(f.caption, normalized_query)}{badge}</td>"
            f"<td><pre>{html.escape(f.formula)}</pre></td>"
            f"<td>{html.escape(f.datasource)}</td>"
            f"<td>{used_sheets}</td>"
            "</tr>"
        )
    if rows:
        table_html = (
            "<table><tr><th>フィールド名</th><th>計算式</th><th>データソース</th><th>使用シート</th></tr>"
            + "".join(rows)
            + "</table>"
        )
    elif normalized_query:
        table_html = "<p>検索条件に一致する計算フィールドがありません。</p>"
    else:
        table_html = "<p>計算フィールドはありません。</p>"
    return f"<section>\n<h2>計算フィールド</h2>\n{table_html}\n</section>"


def _render_parameters(spec: WorkbookSpec, search: str = "") -> str:
    normalized_query = search.strip().casefold()
    params = spec.parameters
    if normalized_query:
        params = [p for p in params if _node_matches(p.caption, normalized_query)]
    rows = [
        "<tr>"
        f"<td>{_highlight_if_match(p.caption, normalized_query)}</td>"
        f"<td>{html.escape(p.datatype)}</td>"
        f"<td>{html.escape(p.current_value)}</td>"
        "</tr>"
        for p in params
    ]
    if rows:
        table_html = (
            "<table><tr><th>パラメーター名</th><th>型</th><th>既定値</th></tr>" + "".join(rows) + "</table>"
        )
    elif normalized_query:
        table_html = "<p>検索条件に一致するパラメーターがありません。</p>"
    else:
        table_html = "<p>パラメーターはありません。</p>"
    return f"<section>\n<h2>パラメーター</h2>\n{table_html}\n</section>"


def _render_sets(spec: WorkbookSpec, search: str = "") -> str:
    normalized_query = search.strip().casefold()
    sets = spec.sets
    if normalized_query:
        sets = [s for s in sets if _node_matches(s.name, normalized_query)]
    rows = [
        "<tr>"
        f"<td>{_highlight_if_match(s.name, normalized_query)}</td>"
        f"<td>{html.escape(s.field)}</td>"
        f"<td>{html.escape(s.description)}</td>"
        f"<td>{html.escape(s.datasource)}</td>"
        "</tr>"
        for s in sets
    ]
    if rows:
        table_html = (
            "<table><tr><th>セット名</th><th>対象フィールド</th><th>定義</th><th>データソース</th></tr>"
            + "".join(rows)
            + "</table>"
        )
    elif normalized_query:
        table_html = "<p>検索条件に一致するセットがありません。</p>"
    else:
        table_html = "<p>セットはありません。</p>"
    return f"<section>\n<h2>セット</h2>\n{table_html}\n</section>"


def _compute_all_used_captions(spec: WorkbookSpec) -> set[str]:
    """全シートで実際に使われている（または使われている計算フィールドの数式から
    参照される）フィールド／計算フィールドの表示名集合を返す。"""
    calc_by_caption = {f.caption: f for f in spec.calculated_fields}
    used: set[str] = set()
    for s in spec.sheets:
        used.update(s.used_fields)
        used.update(s.used_calculated_fields)
    queue = [c for c in used if c in calc_by_caption]
    while queue:
        caption = queue.pop()
        for dep in calc_by_caption[caption].depends_on:
            if dep not in used:
                used.add(dep)
                if dep in calc_by_caption:
                    queue.append(dep)
    return used


def _render_unused_fields(spec: WorkbookSpec, search: str = "") -> str:
    normalized_query = search.strip().casefold()
    used = _compute_all_used_captions(spec)
    unused = [
        (caption, ds.name)
        for ds in spec.datasources
        for caption in ds.all_field_captions
        if caption not in used
    ]
    if normalized_query:
        unused = [(c, d) for c, d in unused if _node_matches(c, normalized_query)]
    rows = [
        f"<tr><td>{_highlight_if_match(c, normalized_query)}</td><td>{html.escape(d)}</td></tr>"
        for c, d in unused
    ]
    if rows:
        table_html = "<table><tr><th>フィールド名</th><th>データソース</th></tr>" + "".join(rows) + "</table>"
    elif normalized_query:
        table_html = "<p>検索条件に一致する未使用フィールドがありません。</p>"
    else:
        table_html = "<p>未使用フィールドはありません。</p>"
    return f"<section>\n<h2>未使用フィールド</h2>\n{table_html}\n</section>"


def _render_sheets(spec: WorkbookSpec) -> str:
    rows = []
    for s in spec.sheets:
        filters = "、".join(html.escape(f.column) for f in s.filters) if s.filters else "-"
        used_fields = "、".join(html.escape(f) for f in s.used_fields) if s.used_fields else "-"
        used_calc_fields = (
            "、".join(html.escape(f) for f in s.used_calculated_fields)
            if s.used_calculated_fields
            else "-"
        )
        rows.append(
            "<tr>"
            f"<td>{_color_swatch(s.color)}{html.escape(s.name)}</td>"
            f"<td>{filters}</td>"
            f"<td>{used_fields}</td>"
            f"<td>{used_calc_fields}</td>"
            "</tr>"
        )
    table_html = (
        "<table><tr><th>シート名</th><th>フィルター</th><th>使用フィールド</th><th>使用計算フィールド</th></tr>"
        + "".join(rows)
        + "</table>"
        if rows
        else "<p>シートはありません。</p>"
    )
    return f"<section>\n<h2>シート一覧</h2>\n{table_html}\n</section>"


def _render_dashboards(spec: WorkbookSpec) -> str:
    rows = []
    for d in spec.dashboards:
        sheets = "、".join(html.escape(s) for s in d.sheets) if d.sheets else "-"
        rows.append(
            f"<tr><td>{_color_swatch(d.color)}{html.escape(d.name)}</td><td>{sheets}</td></tr>"
        )
    table_html = (
        "<table><tr><th>ダッシュボード名</th><th>含まれるシート</th></tr>" + "".join(rows) + "</table>"
        if rows
        else "<p>ダッシュボードはありません。</p>"
    )
    return f"<section>\n<h2>ダッシュボード一覧</h2>\n{table_html}\n</section>"


_DEP_LEGEND = (
    "<div class='dep-legend'>"
    "<span class='dep-legend-item'><span class='dep-swatch dep-sheet'></span>シート</span>"
    "<span class='dep-legend-item'><span class='dep-swatch dep-calc'></span>計算フィールド"
    "（マウスオーバーで数式を表示）</span>"
    "<span class='dep-legend-item'><span class='dep-swatch dep-param'></span>パラメーター</span>"
    "<span class='dep-legend-item'><span class='dep-swatch dep-field'></span>フィールド</span>"
    "<span class='dep-legend-item'>（行・列・色・フィルター・アクション等はシート直下のフィールドに注記）</span>"
    "</div>"
)


def _node_matches(name: str, normalized_query: str) -> bool:
    return bool(normalized_query) and normalized_query in name.casefold()


def _calc_field_li_html(
    calc: CalculatedField, children_html: str, highlight: bool = False, shelf_html: str = ""
) -> str:
    badge = "<span class='badge-lod'>LOD</span>" if calc.is_lod else ""
    title = html.escape(calc.formula)
    caption_html = html.escape(calc.caption)
    if highlight:
        caption_html = f"<mark>{caption_html}</mark>"
    label = f"<span class='dep-label' title='{title}'>{caption_html}</span>"
    return f"<li class='dep-calc'>{label}{badge}{shelf_html}{children_html}</li>"


def _shelf_html(caption: str, shelves: dict[str, list[str]] | None) -> str:
    """フィールドが使われている棚（行・列・色など）の注記HTMLを返す。
    shelves が None の場合（計算フィールドの依存先をたどっている場合）は棚の概念がないため空文字を返す。"""
    if shelves is None:
        return ""
    roles = shelves.get(caption)
    if not roles:
        return ""
    return f"<span class='dep-shelf'>（{'・'.join(html.escape(r) for r in roles)}）</span>"


def _dependency_children_html(
    captions: list[str],
    calc_by_caption: dict[str, CalculatedField],
    param_captions: set[str],
    visited: frozenset[str],
    normalized_query: str,
    shelves: dict[str, list[str]] | None = None,
) -> tuple[str, bool]:
    """このレベルのHTMLと、いずれかのノードが検索条件に一致したかを返す。
    normalized_query が空文字の場合は絞り込みを行わず全件を返す。
    shelves はシート直下のフィールドにのみ渡し、計算フィールドの依存先（数式参照）には渡さない。"""
    items = []
    any_match = False
    for caption in captions:
        if caption in visited:
            if not normalized_query:
                items.append(f"<li class='dep-field'>{html.escape(caption)}（循環参照のため省略）</li>")
            continue
        shelf_html = _shelf_html(caption, shelves)
        calc = calc_by_caption.get(caption)
        if calc is not None:
            self_match = _node_matches(caption, normalized_query)
            # 自身が検索に一致した場合、その配下は絞り込まず全て表示する
            child_query = "" if self_match else normalized_query
            children_html, child_match = "", False
            if calc.depends_on:
                children_html, child_match = _dependency_children_html(
                    calc.depends_on, calc_by_caption, param_captions, visited | {caption}, child_query
                )
            if normalized_query and not (self_match or child_match):
                continue
            any_match = any_match or self_match or child_match
            wrapped_children = f"<ul>{children_html}</ul>" if children_html else ""
            items.append(
                _calc_field_li_html(calc, wrapped_children, highlight=self_match, shelf_html=shelf_html)
            )
        elif caption in param_captions:
            self_match = _node_matches(caption, normalized_query)
            if normalized_query and not self_match:
                continue
            any_match = any_match or self_match
            label = f"<mark>{html.escape(caption)}</mark>" if self_match else html.escape(caption)
            items.append(f"<li class='dep-param'>{label}（パラメーター）{shelf_html}</li>")
        else:
            self_match = _node_matches(caption, normalized_query)
            if normalized_query and not self_match:
                continue
            any_match = any_match or self_match
            label = f"<mark>{html.escape(caption)}</mark>" if self_match else html.escape(caption)
            items.append(f"<li class='dep-field'>{label}{shelf_html}</li>")
    return "".join(items), any_match


def _collect_formula_descendants(
    captions: list[str], calc_by_caption: dict[str, CalculatedField], visited: frozenset[str]
) -> set[str]:
    """captions に含まれる計算フィールドの数式が参照する依存先を再帰的に集める（孫以降も含む）。
    シート直下の一覧から、数式内でしか使われていない（＝棚には無い）重複ノードを除くために使う。"""
    descendants: set[str] = set()
    for caption in captions:
        if caption in visited:
            continue
        calc = calc_by_caption.get(caption)
        if calc is None or not calc.depends_on:
            continue
        descendants.update(calc.depends_on)
        descendants |= _collect_formula_descendants(calc.depends_on, calc_by_caption, visited | {caption})
    return descendants


def _render_dependency_tree(spec: WorkbookSpec, search: str = "") -> str:
    normalized_query = search.strip().casefold()
    calc_by_caption = {f.caption: f for f in spec.calculated_fields}
    param_captions = {p.caption for p in spec.parameters}

    sheet_items = []
    for s in spec.sheets:
        self_match = _node_matches(s.name, normalized_query)
        child_query = "" if self_match else normalized_query
        captions = list(s.used_calculated_fields) + list(s.used_fields)
        formula_descendants = _collect_formula_descendants(captions, calc_by_caption, frozenset())
        captions = [
            c for c in captions if not (c in formula_descendants and not s.field_shelves.get(c))
        ]
        children, child_match = _dependency_children_html(
            captions, calc_by_caption, param_captions, frozenset(), child_query, shelves=s.field_shelves
        )
        if normalized_query and not (self_match or child_match):
            continue
        children_html = f"<ul>{children}</ul>" if children else ""
        name_html = f"<mark>{html.escape(s.name)}</mark>" if self_match else html.escape(s.name)
        sheet_items.append(f"<li class='dep-sheet'>{name_html}{children_html}</li>")

    if sheet_items:
        tree_html = f"<ul class='dep-tree'>{''.join(sheet_items)}</ul>"
    elif normalized_query:
        tree_html = "<p>検索条件に一致するシート・フィールドがありません。</p>"
    else:
        tree_html = "<p>シートがないため依存関係を表示できません。</p>"

    used_calc_captions = {c for s in spec.sheets for c in s.used_calculated_fields}
    orphan_calcs = [f for f in spec.calculated_fields if f.caption not in used_calc_captions]
    if normalized_query:
        orphan_calcs = [f for f in orphan_calcs if _node_matches(f.caption, normalized_query)]
    orphan_html = ""
    if orphan_calcs:
        orphan_items = "".join(
            _calc_field_li_html(f, "", highlight=bool(normalized_query)) for f in orphan_calcs
        )
        orphan_html = (
            "<h2>どのシートにも使用されていない計算フィールド</h2>"
            f"<ul class='dep-tree'>{orphan_items}</ul>"
        )

    return (
        f"<section>\n<h2>依存関係ツリー（シート起点）</h2>\n{_DEP_LEGEND}\n{tree_html}\n</section>"
        + (f"<section>\n{orphan_html}\n</section>" if orphan_html else "")
    )
