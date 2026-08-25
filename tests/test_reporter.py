import html

from tableau_spec.analyzer import (
    CalculatedField,
    DataSource,
    Dashboard,
    JoinInfo,
    Parameter,
    SetInfo,
    Sheet,
    TableInfo,
    WorkbookSpec,
)
from tableau_spec.reporter import MENU, embed_style, render, render_groups


def test_render_includes_overview_counts():
    spec = WorkbookSpec(
        datasources=[DataSource(name="ds1", connection_class="federated", tables=[TableInfo(name="t1", table="[t1]")])],
        calculated_fields=[CalculatedField(name="[c1]", caption="計算1", formula="SUM([x])", is_lod=False, datasource="ds1")],
        parameters=[Parameter(name="[p1]", caption="param1", datatype="integer", current_value="1")],
        sheets=[Sheet(name="シート1")],
    )

    html_text = render(spec, "sample.twb")

    assert "sample.twb" in html_text
    assert "<title>sample.twb 仕様書</title>" in html_text
    assert ">1<" in html_text  # データソース数などの件数


def test_render_escapes_html_in_user_content():
    spec = WorkbookSpec(
        calculated_fields=[
            CalculatedField(
                name="[c1]",
                caption="<script>alert(1)</script>",
                formula="IF [x] < 1 THEN '<b>y</b>' END",
                is_lod=False,
                datasource="ds1",
            )
        ],
    )

    html_text = render(spec, "sample.twb")

    assert "<script>alert(1)</script>" not in html_text
    assert "&lt;script&gt;" in html_text


def test_render_marks_lod_fields_with_badge():
    spec = WorkbookSpec(
        calculated_fields=[
            CalculatedField(
                name="[c1]", caption="固定", formula="{FIXED [x]: SUM([y])}", is_lod=True, datasource="ds1"
            ),
            CalculatedField(
                name="[c2]", caption="通常", formula="SUM([y])", is_lod=False, datasource="ds1"
            ),
        ],
    )

    html_text = render(spec, "sample.twb")

    calc_section = html_text.split("<h2>計算フィールド</h2>")[1].split("</section>")[0]
    assert calc_section.count("<span class='badge-lod'>") == 1


def test_render_custom_sql_in_details():
    spec = WorkbookSpec(
        datasources=[
            DataSource(name="ds1", connection_class="sqlserver", custom_sql=["SELECT * FROM foo"])
        ],
    )

    html_text = render(spec, "sample.twb")

    assert "<details>" in html_text
    assert "SELECT * FROM foo" in html_text


def test_calculated_field_column_order_is_name_formula_datasource():
    spec = WorkbookSpec(
        calculated_fields=[
            CalculatedField(name="[c1]", caption="計算1", formula="SUM([x])", is_lod=False, datasource="ds1")
        ],
    )

    html_text = render(spec, "sample.twb")

    header = "<tr><th>フィールド名</th><th>計算式</th><th>データソース</th><th>使用シート</th></tr>"
    assert header in html_text
    name_pos = html_text.index("計算1")
    formula_pos = html_text.index("SUM([x])")
    ds_pos = html_text.index(">ds1<")
    assert name_pos < formula_pos < ds_pos


def test_calculated_field_formula_always_visible_without_toggle():
    spec = WorkbookSpec(
        calculated_fields=[
            CalculatedField(name="[c1]", caption="計算1", formula="SUM([x])", is_lod=False, datasource="ds1")
        ],
    )

    html_text = render(spec, "sample.twb")

    assert "<pre>SUM([x])</pre>" in html_text
    assert "<summary>" not in html_text.split("<h2>計算フィールド</h2>")[1].split("</section>")[0]


def test_calculated_field_used_sheets_column():
    spec = WorkbookSpec(
        calculated_fields=[
            CalculatedField(name="[c1]", caption="利益率", formula="SUM([x])", is_lod=False, datasource="ds1")
        ],
        sheets=[Sheet(name="シート1", used_calculated_fields=["利益率"])],
    )

    html_text = render(spec, "sample.twb")

    assert "シート1" in html_text.split("<h2>計算フィールド</h2>")[1].split("</section>")[0]


def test_sheet_table_includes_used_fields_and_calculated_fields():
    spec = WorkbookSpec(
        sheets=[
            Sheet(
                name="シート1",
                used_fields=["地域", "売上"],
                used_calculated_fields=["利益率"],
            )
        ],
    )

    html_text = render(spec, "sample.twb")

    assert "<th>使用フィールド</th>" in html_text
    assert "<th>使用計算フィールド</th>" in html_text
    assert "地域、売上" in html_text
    assert "利益率" in html_text


def test_sheet_and_dashboard_color_swatch_rendered():
    spec = WorkbookSpec(
        sheets=[Sheet(name="シート1", color="#ff0000")],
        dashboards=[Dashboard(name="ダッシュボード1", color="#00ff00")],
    )

    html_text = render(spec, "sample.twb")

    assert "<span class='color-swatch' style='background:#ff0000'></span>シート1" in html_text
    assert "<span class='color-swatch' style='background:#00ff00'></span>ダッシュボード1" in html_text


def test_invalid_color_value_is_not_rendered():
    spec = WorkbookSpec(
        sheets=[Sheet(name="シート1", color="red; } body { display:none; } .x {")],
    )

    html_text = render(spec, "sample.twb")

    assert "<span class='color-swatch'" not in html_text
    assert "display:none" not in html_text


def test_render_groups_splits_into_four_menu_sections():
    spec = WorkbookSpec(
        datasources=[DataSource(name="ds1", connection_class="federated")],
        calculated_fields=[
            CalculatedField(name="[c1]", caption="計算1", formula="SUM([x])", is_lod=False, datasource="ds1")
        ],
        parameters=[Parameter(name="[p1]", caption="param1", datatype="integer", current_value="1")],
        sheets=[Sheet(name="シート1", used_calculated_fields=["計算1"])],
        dashboards=[Dashboard(name="ダッシュボード1")],
    )

    groups = render_groups(spec, "sample.twb")

    assert set(groups.keys()) == {
        "overview_datasources",
        "calculated_parameters",
        "sheets_dashboards",
        "dependency_tree",
    }
    assert "データソース" in groups["overview_datasources"]
    assert "計算1" in groups["calculated_parameters"]
    assert "param1" in groups["calculated_parameters"]
    assert "シート1" in groups["sheets_dashboards"]
    assert "ダッシュボード1" in groups["sheets_dashboards"]
    assert "シート1" in groups["dependency_tree"]
    assert "計算1" in groups["dependency_tree"]
    for fragment in groups.values():
        assert "<html" not in fragment


def test_render_fields_lists_plain_fields_with_used_sheets():
    spec = WorkbookSpec(
        sheets=[
            Sheet(name="シート1", used_fields=["地域"]),
            Sheet(name="シート2", used_fields=["地域"]),
        ],
    )

    html_text = render(spec, "sample.twb")

    fields_section = html_text.split("<h2>フィールド一覧</h2>")[1].split("</section>")[0]
    assert "地域" in fields_section
    assert "シート1、シート2" in fields_section


def test_fields_search_filters_fields_calculated_fields_and_parameters():
    spec = WorkbookSpec(
        calculated_fields=[
            CalculatedField(name="[c1]", caption="利益率", formula="SUM([利益])/SUM([売上])", is_lod=False, datasource="ds1"),
            CalculatedField(name="[c2]", caption="達成率", formula="1", is_lod=False, datasource="ds1"),
        ],
        parameters=[
            Parameter(name="[p1]", caption="利益しきい値", datatype="integer", current_value="0"),
            Parameter(name="[p2]", caption="表示件数", datatype="integer", current_value="10"),
        ],
        sheets=[Sheet(name="シート1", used_fields=["利益額", "地域"])],
    )

    groups = render_groups(spec, "sample.twb", fields_search="利益")

    fragment = groups["calculated_parameters"]
    assert "<mark>利益額</mark>" in fragment
    assert "地域" not in fragment
    assert "<mark>利益率</mark>" in fragment
    assert "達成率" not in fragment
    assert "<mark>利益しきい値</mark>" in fragment
    assert "表示件数" not in fragment


def test_fields_search_no_match_shows_messages():
    spec = WorkbookSpec(
        calculated_fields=[
            CalculatedField(name="[c1]", caption="達成率", formula="1", is_lod=False, datasource="ds1")
        ],
        parameters=[Parameter(name="[p1]", caption="表示件数", datatype="integer", current_value="10")],
        sheets=[Sheet(name="シート1", used_fields=["地域"])],
    )

    fragment = render_groups(spec, "sample.twb", fields_search="存在しない名前")["calculated_parameters"]

    assert "検索条件に一致するフィールドがありません。" in fragment
    assert "検索条件に一致する計算フィールドがありません。" in fragment
    assert "検索条件に一致するパラメーターがありません。" in fragment


def test_render_dependency_tree_nests_calc_field_dependencies():
    spec = WorkbookSpec(
        calculated_fields=[
            CalculatedField(
                name="[c1]",
                caption="予実差",
                formula="SUM([予算])-SUM([実績])",
                is_lod=False,
                datasource="ds1",
                depends_on=["予算"],
            )
        ],
        sheets=[Sheet(name="シート1", used_calculated_fields=["予実差"])],
    )

    html_text = render(spec, "sample.twb")

    tree_section = html_text.split("<h2>依存関係ツリー（シート起点）</h2>")[1]
    assert "class='dep-sheet'>シート1" in tree_section
    assert "class='dep-calc'>" in tree_section
    assert ">予実差</span>" in tree_section
    assert "class='dep-field'>予算" in tree_section


def test_render_dependency_tree_shows_formula_as_tooltip_on_calc_field():
    spec = WorkbookSpec(
        calculated_fields=[
            CalculatedField(
                name="[c1]", caption="予実差", formula="SUM([予算])-SUM([実績])", is_lod=False, datasource="ds1"
            )
        ],
        sheets=[Sheet(name="シート1", used_calculated_fields=["予実差"])],
    )

    html_text = render(spec, "sample.twb")

    assert "title='SUM([予算])-SUM([実績])'" in html_text


def test_render_dependency_tree_includes_legend():
    spec = WorkbookSpec(sheets=[Sheet(name="シート1")])

    html_text = render(spec, "sample.twb")

    legend_section = html_text.split("<h2>依存関係ツリー（シート起点）</h2>")[1]
    assert "dep-legend" in legend_section
    assert "計算フィールド" in legend_section
    assert "パラメーター" in legend_section
    assert "フィールド" in legend_section


def test_render_dependency_tree_hides_shelfless_field_already_nested_under_calc_field():
    spec = WorkbookSpec(
        calculated_fields=[
            CalculatedField(
                name="[c1]",
                caption="over 45",
                formula="AVG([時間外勤務(h)])>45",
                is_lod=False,
                datasource="ds1",
                depends_on=["時間外勤務(h)"],
            )
        ],
        sheets=[
            Sheet(
                name="45時間超",
                used_calculated_fields=["over 45"],
                used_fields=["時間外勤務(h)", "氏名"],
                field_shelves={"氏名": ["行"]},
            )
        ],
    )

    html_text = render(spec, "sample.twb")

    tree_section = html_text.split("<h2>依存関係ツリー（シート起点）</h2>")[1].split("</section>")[0]
    # 「時間外勤務(h)」は over 45 の依存先として一度だけ現れ（数式ツールチップにも1回出現）、
    # シート直下には重複表示されない
    assert tree_section.count("時間外勤務(h)") == 2
    assert "class='dep-field'>氏名" in tree_section


def test_render_dependency_tree_keeps_shelfless_field_when_it_also_has_its_own_shelf():
    spec = WorkbookSpec(
        calculated_fields=[
            CalculatedField(
                name="[c1]",
                caption="over 45",
                formula="AVG([時間外勤務(h)])>45",
                is_lod=False,
                datasource="ds1",
                depends_on=["時間外勤務(h)"],
            )
        ],
        sheets=[
            Sheet(
                name="45時間超",
                used_calculated_fields=["over 45"],
                used_fields=["時間外勤務(h)"],
                field_shelves={"時間外勤務(h)": ["行"]},
            )
        ],
    )

    html_text = render(spec, "sample.twb")

    tree_section = html_text.split("<h2>依存関係ツリー（シート起点）</h2>")[1].split("</section>")[0]
    # 自身も棚（行）を持つ場合は重複除去せず、シート直下にも表示する（数式ツールチップの1回を含め計3回）
    assert tree_section.count("時間外勤務(h)") == 3


def test_render_dependency_tree_annotates_sheet_level_field_shelves():
    spec = WorkbookSpec(
        calculated_fields=[
            CalculatedField(
                name="[c1]",
                caption="予実差",
                formula="SUM([予算])-SUM([実績])",
                is_lod=False,
                datasource="ds1",
                depends_on=["予算"],
            )
        ],
        sheets=[
            Sheet(
                name="シート1",
                used_calculated_fields=["予実差"],
                used_fields=["地域"],
                field_shelves={"予実差": ["列"], "地域": ["行", "フィルター"]},
            )
        ],
    )

    html_text = render(spec, "sample.twb")

    tree_section = html_text.split("<h2>依存関係ツリー（シート起点）</h2>")[1]
    assert "予実差</span><span class='dep-shelf'>（列）</span>" in tree_section
    assert "class='dep-field'>地域<span class='dep-shelf'>（行・フィルター）</span>" in tree_section
    # 数式内の依存先（予算）は棚の概念がないため注記が付かない
    assert "予算<span class='dep-shelf'" not in tree_section


def test_render_dependency_tree_lists_orphan_calculated_fields():
    spec = WorkbookSpec(
        calculated_fields=[
            CalculatedField(name="[c1]", caption="未使用計算", formula="1", is_lod=False, datasource="ds1")
        ],
        sheets=[Sheet(name="シート1")],
    )

    html_text = render(spec, "sample.twb")

    assert "どのシートにも使用されていない計算フィールド" in html_text
    assert "未使用計算" in html_text.split("どのシートにも使用されていない計算フィールド")[1]


def test_dependency_tree_search_excludes_unrelated_sheets():
    spec = WorkbookSpec(
        calculated_fields=[
            CalculatedField(name="[c1]", caption="利益率", formula="SUM([利益])/SUM([売上])", is_lod=False, datasource="ds1")
        ],
        sheets=[
            Sheet(name="売上シート", used_calculated_fields=["利益率"]),
            Sheet(name="人事シート", used_fields=["氏名"]),
        ],
    )

    groups = render_groups(spec, "sample.twb", dependency_search="利益率")

    tree = groups["dependency_tree"]
    assert "売上シート" in tree
    assert "人事シート" not in tree
    assert "<mark>利益率</mark>" in tree


def test_dependency_tree_search_keeps_sheet_when_descendant_calc_field_matches():
    spec = WorkbookSpec(
        calculated_fields=[
            CalculatedField(
                name="[c1]",
                caption="予実差",
                formula="SUM([予算])-SUM([実績])",
                is_lod=False,
                datasource="ds1",
                depends_on=["予算"],
            )
        ],
        sheets=[Sheet(name="シート1", used_calculated_fields=["予実差"])],
    )

    groups = render_groups(spec, "sample.twb", dependency_search="予算")

    tree = groups["dependency_tree"]
    assert "シート1" in tree
    assert "<mark>予算</mark>" in tree
    assert ">予実差</span>" in tree
    assert "<mark>予実差</mark>" not in tree


def test_dependency_tree_search_no_match_shows_message():
    spec = WorkbookSpec(sheets=[Sheet(name="シート1", used_fields=["地域"])])

    groups = render_groups(spec, "sample.twb", dependency_search="存在しない名前")

    assert "検索条件に一致するシート・フィールドがありません。" in groups["dependency_tree"]


def test_dependency_tree_search_filters_orphan_calculated_fields():
    spec = WorkbookSpec(
        calculated_fields=[
            CalculatedField(name="[c1]", caption="未使用A", formula="1", is_lod=False, datasource="ds1"),
            CalculatedField(name="[c2]", caption="未使用B", formula="2", is_lod=False, datasource="ds1"),
        ],
        sheets=[Sheet(name="シート1")],
    )

    groups = render_groups(spec, "sample.twb", dependency_search="未使用A")

    tree = groups["dependency_tree"]
    assert "未使用A" in tree
    assert "未使用B" not in tree


def test_embed_style_has_no_body_selector():
    style = embed_style()

    assert "<style>" in style
    assert "body {" not in style
    assert ".tableau-spec-embed" in style


def test_render_empty_spec_shows_placeholders():
    spec = WorkbookSpec()

    html_text = render(spec, "empty.twb")

    assert "データソースはありません。" in html_text
    assert "テーブル結合はありません。" in html_text
    assert "計算フィールドはありません。" in html_text
    assert "パラメーターはありません。" in html_text
    assert "セットはありません。" in html_text
    assert "未使用フィールドはありません。" in html_text
    assert "シートはありません。" in html_text
    assert "ダッシュボードはありません。" in html_text


def test_render_joins_shows_table_pair_and_condition():
    spec = WorkbookSpec(
        datasources=[
            DataSource(
                name="ds1",
                connection_class="federated",
                joins=[
                    JoinInfo(
                        join_type="inner",
                        left_table="[dbo].[注文]",
                        right_table="[dbo].[顧客]",
                        condition="[注文].[顧客ID] = [顧客].[顧客ID]",
                    )
                ],
            )
        ],
    )

    html_text = render(spec, "sample.twb")

    joins_section = html_text.split("<h2>テーブル結合</h2>")[1].split("</section>")[0]
    assert "[dbo].[注文]" in joins_section
    assert "[dbo].[顧客]" in joins_section
    assert "inner" in joins_section
    assert "[注文].[顧客ID] = [顧客].[顧客ID]" in joins_section


def test_render_sets_lists_name_field_and_description():
    spec = WorkbookSpec(
        sets=[SetInfo(name="上位顧客", field="顧客名", description="上位 5 件（降順）", datasource="ds1")],
    )

    html_text = render(spec, "sample.twb")

    sets_section = html_text.split("<h2>セット</h2>")[1].split("</section>")[0]
    assert "上位顧客" in sets_section
    assert "顧客名" in sets_section
    assert "上位 5 件（降順）" in sets_section


def test_sets_search_filters_and_highlights():
    spec = WorkbookSpec(
        sets=[
            SetInfo(name="上位顧客", field="顧客名", description="上位 5 件", datasource="ds1"),
            SetInfo(name="低利益商品", field="商品名", description="条件ベース", datasource="ds1"),
        ],
    )

    fragment = render_groups(spec, "sample.twb", fields_search="上位")["calculated_parameters"]

    assert "<mark>上位顧客</mark>" in fragment
    assert "低利益商品" not in fragment


def test_render_unused_fields_excludes_used_and_transitively_used_fields():
    spec = WorkbookSpec(
        datasources=[
            DataSource(
                name="ds1",
                connection_class="federated",
                all_field_captions=["直接使用", "数式内で使用", "未使用"],
            )
        ],
        calculated_fields=[
            CalculatedField(
                name="[c1]",
                caption="計算1",
                formula="1",
                is_lod=False,
                datasource="ds1",
                depends_on=["数式内で使用"],
            )
        ],
        sheets=[
            Sheet(name="シート1", used_fields=["直接使用"], used_calculated_fields=["計算1"]),
        ],
    )

    html_text = render(spec, "sample.twb")

    unused_section = html_text.split("<h2>未使用フィールド</h2>")[1].split("</section>")[0]
    assert "未使用" in unused_section
    assert "直接使用" not in unused_section
    assert "数式内で使用" not in unused_section


def test_render_produces_tabbed_document_with_search_scripts():
    spec = WorkbookSpec(sheets=[Sheet(name="シート1")])

    html_text = render(spec, "sample.twb")

    for key, label in MENU:
        assert f"data-tab='{key}'" in html_text
        assert html.escape(label) in html_text
        assert f"id='tw-panel-{key}'" in html_text
    assert "function twShowTab" in html_text
    assert "function twFilterFieldTables" in html_text
    assert "function twFilterTree" in html_text
    assert html_text.count(" hidden>") == len(MENU) - 1
