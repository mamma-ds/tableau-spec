"""Tableau XML の ElementTree からのデータ抽出のみを担当する。"""

from __future__ import annotations

import re
import urllib.parse
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

_LOD_KEYWORDS = ("FIXED", "INCLUDE", "EXCLUDE")
_FIELD_REF_PATTERN = re.compile(r"\[[^\[\]]+\]")
_FILTER_COLUMN_PATTERN = re.compile(r"^\[(?P<ds>[^\[\]]+)\]\.\[(?P<field>.+)\]$")
_QUALIFIED_FIELD_PATTERN = re.compile(r"\[[^\[\]]+\]\.\[(?P<field>[^\[\]]+)\]")
_BRACKET_REF_PATTERN = re.compile(r"\[([^\[\]]+)\]")

_SHELF_LABELS = {
    "color": "色",
    "size": "サイズ",
    "shape": "形状",
    "text": "ラベル",
    "tooltip": "ツールヒント",
    "detail": "詳細",
    "lod": "詳細",
    "path": "パス",
    "angle": "角度",
    "wedge-size": "ウェッジサイズ",
    "geometry": "ジオメトリ",
}


def _strip_brackets(name: str) -> str:
    if name.startswith("[") and name.endswith("]"):
        return name[1:-1]
    return name


def _caption_or_bare_name(elem: ET.Element) -> str:
    caption = elem.get("caption")
    if caption is not None:
        return caption
    return _strip_brackets(elem.get("name", ""))


@dataclass
class TableInfo:
    name: str
    table: str


@dataclass
class JoinInfo:
    join_type: str
    left_table: str
    right_table: str
    condition: str


@dataclass
class SetInfo:
    name: str
    field: str
    description: str
    datasource: str


@dataclass
class DataSource:
    name: str
    connection_class: str
    tables: list[TableInfo] = field(default_factory=list)
    custom_sql: list[str] = field(default_factory=list)
    joins: list[JoinInfo] = field(default_factory=list)
    all_field_captions: list[str] = field(default_factory=list)


@dataclass
class CalculatedField:
    name: str
    caption: str
    formula: str
    is_lod: bool
    datasource: str
    depends_on: list[str] = field(default_factory=list)


@dataclass
class Parameter:
    name: str
    caption: str
    datatype: str
    current_value: str


@dataclass
class FilterInfo:
    column: str
    filter_class: str


@dataclass
class Sheet:
    name: str
    color: str = ""
    filters: list[FilterInfo] = field(default_factory=list)
    used_fields: list[str] = field(default_factory=list)
    used_calculated_fields: list[str] = field(default_factory=list)
    field_shelves: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class Dashboard:
    name: str
    color: str = ""
    sheets: list[str] = field(default_factory=list)


@dataclass
class WorkbookSpec:
    datasources: list[DataSource] = field(default_factory=list)
    calculated_fields: list[CalculatedField] = field(default_factory=list)
    parameters: list[Parameter] = field(default_factory=list)
    sets: list[SetInfo] = field(default_factory=list)
    sheets: list[Sheet] = field(default_factory=list)
    dashboards: list[Dashboard] = field(default_factory=list)


def analyze(root: ET.Element) -> WorkbookSpec:
    """XML ルート要素から WorkbookSpec を構築する。"""
    datasource_elems = root.findall("./datasources/datasource")

    ds_display_names = {
        ds.get("name", ""): ds.get("caption") or ds.get("name", "") for ds in datasource_elems
    }
    name_to_caption = _build_field_name_map(root, datasource_elems)
    tab_colors = _build_tab_color_map(root)

    datasources: list[DataSource] = []
    calculated_fields: list[CalculatedField] = []
    parameters: list[Parameter] = []
    sets: list[SetInfo] = []

    for ds in datasource_elems:
        raw_name = ds.get("name", "")
        if raw_name == "Parameters":
            parameters.extend(_extract_parameters(ds))
            continue
        display_name = ds_display_names[raw_name]
        datasources.append(_extract_datasource(ds, display_name))
        calculated_fields.extend(_extract_calculated_fields(ds, display_name, name_to_caption))
        sets.extend(_extract_sets(ds, display_name, name_to_caption))

    sheets = [
        _extract_sheet(ws, ds_display_names, name_to_caption, tab_colors)
        for ws in root.findall("./worksheets/worksheet")
    ]
    sheet_names = {s.name for s in sheets}
    dashboards = [
        _extract_dashboard(db, sheet_names, tab_colors)
        for db in root.findall("./dashboards/dashboard")
    ]

    _apply_actions_to_sheets(root, sheets, dashboards, name_to_caption)

    return WorkbookSpec(
        datasources=datasources,
        calculated_fields=calculated_fields,
        parameters=parameters,
        sets=sets,
        sheets=sheets,
        dashboards=dashboards,
    )


def _build_field_name_map(
    root: ET.Element, datasource_elems: list[ET.Element]
) -> dict[str, str]:
    """フィールド・計算フィールド・パラメーター・グループの内部名 → 表示名(caption)の対応表を作る。"""
    name_to_caption: dict[str, str] = {}
    for ds in datasource_elems:
        for elem in list(ds.findall("./column")) + list(ds.findall("./group")):
            name = elem.get("name", "")
            if name:
                name_to_caption[name] = _caption_or_bare_name(elem)

    # column-instance はワークシート側の参照名。実体カラムの表示名に解決する。
    for instance in root.iter("column-instance"):
        instance_name = instance.get("name", "")
        target_column = instance.get("column", "")
        if instance_name and target_column:
            name_to_caption[instance_name] = name_to_caption.get(
                target_column, _strip_brackets(target_column)
            )

    return name_to_caption


def _build_tab_color_map(root: ET.Element) -> dict[str, str]:
    """worksheet/dashboard 名 → タブの色(tab-color)の対応表を作る。"""
    return {
        window.get("name", ""): window.get("tab-color", "")
        for window in root.findall("./windows/window")
        if window.get("tab-color")
    }


def _extract_parameters(datasource: ET.Element) -> list[Parameter]:
    params = []
    for col in datasource.findall("./column"):
        calc = col.find("./calculation")
        current_value = calc.get("formula", "") if calc is not None else ""
        params.append(
            Parameter(
                name=col.get("name", ""),
                caption=_caption_or_bare_name(col),
                datatype=col.get("datatype", ""),
                current_value=current_value,
            )
        )
    return params


def _relation_label(relation: ET.Element) -> str:
    """<relation> 要素の表示ラベルを返す（テーブル名優先、無ければ内部名）。"""
    rel_type = relation.get("type", "")
    if rel_type == "table":
        return relation.get("table") or relation.get("name") or ""
    if rel_type == "text":
        return "(カスタムSQL)"
    if rel_type == "join":
        return "(結合)"
    return relation.get("name") or rel_type or "?"


def _clause_expression_to_str(expr: ET.Element) -> str:
    """結合条件の <expression> 要素を人が読める文字列に変換する。"""
    op = expr.get("op", "")
    children = list(expr)
    if not children:
        return op
    if op.upper() == "AND":
        return " AND ".join(_clause_expression_to_str(c) for c in children)
    if len(children) == 2:
        return f"{_clause_expression_to_str(children[0])} {op} {_clause_expression_to_str(children[1])}"
    return f" {op} ".join(_clause_expression_to_str(c) for c in children)


def _extract_join(relation: ET.Element) -> JoinInfo:
    sides = relation.findall("./relation")
    left = _relation_label(sides[0]) if len(sides) > 0 else "?"
    right = _relation_label(sides[1]) if len(sides) > 1 else "?"
    clause = relation.find("./clause")
    condition = ""
    if clause is not None:
        expr = clause.find("./expression")
        if expr is not None:
            condition = _clause_expression_to_str(expr)
    return JoinInfo(
        join_type=relation.get("join", ""), left_table=left, right_table=right, condition=condition
    )


def _extract_datasource(datasource: ET.Element, display_name: str) -> DataSource:
    connection = datasource.find("./connection")
    connection_class = connection.get("class", "") if connection is not None else ""

    tables: list[TableInfo] = []
    custom_sql: list[str] = []
    joins: list[JoinInfo] = []
    if connection is not None:
        for relation in connection.iter("relation"):
            rel_type = relation.get("type", "")
            if rel_type == "text":
                custom_sql.append((relation.text or "").strip())
            elif rel_type == "table":
                tables.append(
                    TableInfo(name=relation.get("name", ""), table=relation.get("table", ""))
                )
            elif rel_type == "join":
                joins.append(_extract_join(relation))

    all_field_captions: list[str] = []
    for col in datasource.findall("./column"):
        if any(key.endswith("auto-column") for key in col.attrib):
            continue
        caption = _caption_or_bare_name(col)
        if caption not in all_field_captions:
            all_field_captions.append(caption)

    return DataSource(
        name=display_name,
        connection_class=connection_class,
        tables=tables,
        custom_sql=custom_sql,
        joins=joins,
        all_field_captions=all_field_captions,
    )


def _is_set_group(group: ET.Element) -> bool:
    """Tableauの「セット」は <group user:ui-builder='filter-group'> として表現される
    （ダッシュボードアクション用に自動生成される非表示グループとは別物）。"""
    return any(
        key.endswith("ui-builder") and value == "filter-group" for key, value in group.attrib.items()
    )


def _find_set_base_field(groupfilter: ET.Element, name_to_caption: dict[str, str]) -> str:
    """groupfilter ツリーを再帰的に辿り、セットの対象フィールドの表示名を返す。"""
    level = groupfilter.get("level")
    if level:
        return name_to_caption.get(level, _strip_brackets(level))
    for child in groupfilter:
        found = _find_set_base_field(child, name_to_caption)
        if found:
            return found
    return ""


def _describe_set(group: ET.Element, name_to_caption: dict[str, str]) -> str:
    """セットの定義内容を簡潔な日本語で要約する（完全な条件の再現は行わない）。"""
    top = group.find("./groupfilter")
    if top is None:
        return "条件ベース"
    function = top.get("function", "")
    if function == "end" and top.get("end") == "top":
        raw_count = top.get("count", "")
        count_refs = _resolve_field_captions(raw_count, name_to_caption)
        count_display = count_refs[0] if count_refs else raw_count
        order = top.find("./groupfilter[@function='order']")
        direction = order.get("direction", "") if order is not None else ""
        direction_label = {"DESC": "降順", "ASC": "昇順"}.get(direction, "")
        suffix = f"（{direction_label}）" if direction_label else ""
        return f"上位 {count_display} 件{suffix}"
    if function == "member":
        return "メンバー指定"
    if function == "union":
        return "複数条件の組み合わせ（OR）"
    if function == "intersection":
        return "複数条件の組み合わせ（AND）"
    return "条件ベース"


def _extract_sets(
    datasource: ET.Element, ds_display_name: str, name_to_caption: dict[str, str]
) -> list[SetInfo]:
    sets = []
    for group in datasource.findall("./group"):
        if not _is_set_group(group):
            continue
        caption = _caption_or_bare_name(group)
        base_field = _find_set_base_field(group, name_to_caption)
        description = _describe_set(group, name_to_caption)
        sets.append(
            SetInfo(name=caption, field=base_field, description=description, datasource=ds_display_name)
        )
    return sets


def _extract_calculated_fields(
    datasource: ET.Element, ds_display_name: str, name_to_caption: dict[str, str]
) -> list[CalculatedField]:
    fields = []
    for col in datasource.findall("./column"):
        if any(key.endswith("auto-column") for key in col.attrib):
            continue
        calc = col.find("./calculation")
        if calc is None or calc.get("class") != "tableau":
            continue
        formula = calc.get("formula", "")
        if not formula:
            continue
        name = col.get("name", "")
        caption = _caption_or_bare_name(col)
        is_lod = any(keyword in formula for keyword in _LOD_KEYWORDS)
        humanized_formula, depends_on = _humanize_formula(formula, name_to_caption)
        fields.append(
            CalculatedField(
                name=name,
                caption=caption,
                formula=humanized_formula,
                is_lod=is_lod,
                datasource=ds_display_name,
                depends_on=depends_on,
            )
        )
    return fields


def _humanize_formula(formula: str, name_to_caption: dict[str, str]) -> tuple[str, list[str]]:
    """数式内のフィールド内部参照（[Calculation_xxx]・[none:地域:nk] など）を表示名に置き換え、
    参照先の表示名一覧（依存フィールド）も合わせて返す。"""
    depends_on: list[str] = []

    def replace(match: re.Match[str]) -> str:
        ref = match.group(0)
        caption = name_to_caption.get(ref)
        if caption is None:
            return ref
        if caption not in depends_on:
            depends_on.append(caption)
        return f"[{caption}]"

    humanized = _FIELD_REF_PATTERN.sub(replace, formula)
    return humanized, depends_on


def _resolve_filter_column(
    raw_column: str, ds_display_names: dict[str, str], name_to_caption: dict[str, str]
) -> str:
    """フィルターの column 属性（[ds].[field]）を「データソース名.フィールド名」の表示形式に解決する。"""
    match = _FILTER_COLUMN_PATTERN.match(raw_column)
    if not match:
        return raw_column
    ds_raw = match.group("ds")
    field_raw = match.group("field")
    ds_display = ds_display_names.get(ds_raw, ds_raw)
    field_display = name_to_caption.get(f"[{field_raw}]", field_raw)
    return f"{ds_display}.{field_display}"


def _resolve_field_captions(text: str, name_to_caption: dict[str, str]) -> list[str]:
    """"[データソース].[フィールド]" 形式の参照から表示名一覧を重複なく返す。"""
    captions: list[str] = []
    for m in _QUALIFIED_FIELD_PATTERN.finditer(text):
        field_ref = f"[{m.group('field')}]"
        caption = name_to_caption.get(field_ref, m.group("field"))
        if caption not in captions:
            captions.append(caption)
    return captions


def _add_shelf(field_shelves: dict[str, list[str]], caption: str, role: str) -> None:
    roles = field_shelves.setdefault(caption, [])
    if role not in roles:
        roles.append(role)


def _extract_field_shelves(
    worksheet: ET.Element, name_to_caption: dict[str, str]
) -> dict[str, list[str]]:
    """ワークシート内でフィールド／計算フィールドがどの棚（行・列・色など）に
    使われているかの対応表（表示名 → 棚名一覧）を作る。"""
    field_shelves: dict[str, list[str]] = {}

    for rows_elem in worksheet.findall("./table/rows"):
        for caption in _resolve_field_captions(rows_elem.text or "", name_to_caption):
            _add_shelf(field_shelves, caption, "行")
    for cols_elem in worksheet.findall("./table/cols"):
        for caption in _resolve_field_captions(cols_elem.text or "", name_to_caption):
            _add_shelf(field_shelves, caption, "列")

    for pane in worksheet.iter("pane"):
        encodings = pane.find("./encodings")
        if encodings is None:
            continue
        for enc in encodings:
            col = enc.get("column")
            if not col:
                continue
            role = _SHELF_LABELS.get(enc.tag, enc.tag)
            for caption in _resolve_field_captions(col, name_to_caption):
                _add_shelf(field_shelves, caption, role)

    return field_shelves


def _extract_sheet(
    worksheet: ET.Element,
    ds_display_names: dict[str, str],
    name_to_caption: dict[str, str],
    tab_colors: dict[str, str],
) -> Sheet:
    field_shelves = _extract_field_shelves(worksheet, name_to_caption)

    filters: list[FilterInfo] = []
    for f in worksheet.iter("filter"):
        raw_column = f.get("column", "")
        filters.append(
            FilterInfo(
                column=_resolve_filter_column(raw_column, ds_display_names, name_to_caption),
                filter_class=f.get("class", ""),
            )
        )
        for caption in _resolve_field_captions(raw_column, name_to_caption):
            _add_shelf(field_shelves, caption, "フィルター")

    used_fields: list[str] = []
    used_calculated_fields: list[str] = []
    for dependencies in worksheet.iter("datasource-dependencies"):
        for col in dependencies.findall("./column"):
            caption = _caption_or_bare_name(col)
            calc = col.find("./calculation")
            target = (
                used_calculated_fields
                if calc is not None and calc.get("class") == "tableau"
                else used_fields
            )
            if caption not in target:
                target.append(caption)

    name = worksheet.get("name", "")
    return Sheet(
        name=name,
        color=tab_colors.get(name, ""),
        filters=filters,
        used_fields=used_fields,
        used_calculated_fields=used_calculated_fields,
        field_shelves=field_shelves,
    )


def _extract_dashboard(
    dashboard: ET.Element, sheet_names: set[str], tab_colors: dict[str, str]
) -> Dashboard:
    embedded: list[str] = []
    for zone in dashboard.iter("zone"):
        zone_name = zone.get("name")
        if zone_name and zone_name in sheet_names and zone_name not in embedded:
            embedded.append(zone_name)
    name = dashboard.get("name", "")
    return Dashboard(name=name, color=tab_colors.get(name, ""), sheets=embedded)


def _extract_action_source_sheets(
    action: ET.Element, dashboard_sheets: dict[str, list[str]]
) -> list[str]:
    """アクションの発生元（ソース）となるワークシート名一覧を返す。
    <source worksheet='X'> なら単一シート、<exclude-sheet> 指定ならダッシュボード内の
    それ以外の全シートが対象になる。"""
    source = action.find("./source")
    if source is None:
        return []
    worksheet = source.get("worksheet")
    if worksheet:
        return [worksheet]
    dashboard = source.get("dashboard", "")
    excluded = {ex.get("name", "") for ex in source.findall("./exclude-sheet")}
    return [s for s in dashboard_sheets.get(dashboard, []) if s not in excluded]


def _extract_action_field_captions(action: ET.Element, name_to_caption: dict[str, str]) -> list[str]:
    """アクションが対象とする具体的なフィールドの表示名一覧を返す。
    「すべてのフィールド」を対象とするアクション（special-fields=all）など、
    具体的なフィールドを特定できない場合は空リストを返す。"""
    command = action.find("./command")
    if command is None:
        return []

    for param in command.findall("./param"):
        if param.get("name") == "field-captions":
            value = param.get("value", "")
            return [c for c in value.split(",") if c]

    link = action.find("./link")
    if link is not None:
        decoded = urllib.parse.unquote(link.get("expression", ""))
        captions: list[str] = []
        for m in _BRACKET_REF_PATTERN.finditer(decoded):
            caption = name_to_caption.get(f"[{m.group(1)}]")
            if caption and caption not in captions:
                captions.append(caption)
        return captions

    return []


def _apply_actions_to_sheets(
    root: ET.Element,
    sheets: list[Sheet],
    dashboards: list[Dashboard],
    name_to_caption: dict[str, str],
) -> None:
    """<actions> 内のフィルター／ハイライトアクションを解析し、発生元シートの対象フィールドに
    「アクション」の棚情報を追記する（対象フィールドを具体的に特定できるものだけ）。"""
    sheets_by_name = {s.name: s for s in sheets}
    dashboard_sheets = {d.name: d.sheets for d in dashboards}

    for action in root.findall("./actions/action"):
        source_sheet_names = _extract_action_source_sheets(action, dashboard_sheets)
        if not source_sheet_names:
            continue
        captions = _extract_action_field_captions(action, name_to_caption)
        if not captions:
            continue
        for sheet_name in source_sheet_names:
            sheet = sheets_by_name.get(sheet_name)
            if sheet is None:
                continue
            known = set(sheet.used_fields) | set(sheet.used_calculated_fields)
            for caption in captions:
                if caption in known:
                    _add_shelf(sheet.field_shelves, caption, "アクション")
