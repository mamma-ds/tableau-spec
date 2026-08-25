import xml.etree.ElementTree as ET

from tableau_spec.analyzer import analyze

_WORKBOOK_XML = """
<workbook version='18.1' xmlns:user='http://www.tableausoftware.com/xml/user'>
  <datasources>
    <datasource name='Parameters' hasconnection='false' inline='true'>
      <column name='[Parameter 1]' caption='しきい値' datatype='integer' value='10'>
        <calculation class='tableau' formula='10' />
      </column>
    </datasource>
    <datasource name='売上データ' inline='true'>
      <connection class='federated'>
        <named-connections>
          <named-connection name='売上データleaf'>
            <connection class='excel-direct' />
          </named-connection>
        </named-connections>
        <relation name='売上$' table='[売上$]' type='table' />
      </connection>
      <column name='[Number of Records]' user:auto-column='numrec'>
        <calculation class='tableau' formula='1' />
      </column>
      <column name='[利益率]' caption='利益率' role='measure' type='quantitative'>
        <calculation class='tableau' formula='SUM([利益])/SUM([売上])' />
      </column>
      <column name='[Calc_LOD]' caption='固定利益' role='measure' type='quantitative'>
        <calculation class='tableau' formula='{ FIXED [カテゴリ] : SUM([利益]) }' />
      </column>
      <column name='[Calculation_123456789012345]' caption='予算' role='measure' type='quantitative'>
        <calculation class='tableau' formula='100' />
      </column>
      <column name='[Calc_Diff]' caption='予算差分' role='measure' type='quantitative'>
        <calculation class='tableau' formula='SUM([売上])-[Calculation_123456789012345]' />
      </column>
      <column name='[選択月のSales (コピー)_999]' caption='Sales_選択月' role='measure' type='quantitative'>
        <calculation class='tableau' formula='100' />
      </column>
      <column name='[Calc_Ref2]' caption='前年比' role='measure' type='quantitative'>
        <calculation class='tableau' formula='[選択月のSales (コピー)_999] / [Parameters].[Parameter 1]' />
      </column>
      <column name='[売上]' datatype='real' role='measure' type='quantitative' />
    </datasource>
    <datasource name='federated.0kjmi6s1inqzi21ddic380yes4yq' caption='人事データ (人事データ)' inline='true'>
      <connection class='federated' />
    </datasource>
    <datasource name='結合データ' inline='true'>
      <connection class='federated'>
        <relation join='inner' type='join'>
          <relation name='注文' table='[dbo].[注文]' type='table' />
          <relation name='顧客' table='[dbo].[顧客]' type='table' />
          <clause type='join'>
            <expression op='='>
              <expression op='[注文].[顧客ID]' />
              <expression op='[顧客].[顧客ID]' />
            </expression>
          </clause>
        </relation>
      </connection>
      <column caption='顧客名' name='[顧客名]' role='dimension' type='nominal' />
      <column caption='未使用列' name='[未使用列]' role='dimension' type='nominal' />
      <group caption='上位顧客セット' name='[上位顧客セット]' name-style='unqualified' user:ui-builder='filter-group'>
        <groupfilter count='5' end='top' function='end' units='records' user:ui-marker='end'>
          <groupfilter direction='DESC' expression='SUM([売上])' function='order' user:ui-marker='order'>
            <groupfilter function='level-members' level='[顧客名]' user:ui-enumeration='all' user:ui-marker='enumerate' />
          </groupfilter>
        </groupfilter>
      </group>
      <group caption='アクション (Reset)' hidden='true' name='[Action (Reset)]' name-style='unqualified' user:auto-column='sheet_link'>
        <groupfilter function='crossjoin'>
          <groupfilter function='level-members' level='[顧客名]' />
        </groupfilter>
      </group>
    </datasource>
  </datasources>
  <actions>
    <action caption='アクション1' name='[Action1]'>
      <activation type='on-select' />
      <source dashboard='ダッシュボード1' type='sheet' worksheet='シートC' />
      <command command='tsc:tsl-filter'>
        <param name='field-captions' value='担当者' />
        <param name='target' value='ダッシュボード1' />
      </command>
    </action>
    <action caption='アクション2 (全フィールド)' name='[Action2]'>
      <activation type='on-select' />
      <source dashboard='ダッシュボード1' type='sheet' worksheet='シートC' />
      <command command='tsc:tsl-filter'>
        <param name='special-fields' value='all' />
        <param name='target' value='ダッシュボード1' />
      </command>
    </action>
    <action caption='アクション3 (除外指定)' name='[Action3]'>
      <activation type='on-select' />
      <source dashboard='ダッシュボード1' type='sheet'>
        <exclude-sheet name='シートB' />
      </source>
      <command command='tsc:brush'>
        <param name='field-captions' value='地域' />
        <param name='target' value='ダッシュボード1' />
      </command>
    </action>
  </actions>
  <worksheets>
    <worksheet name='シートA'>
      <table>
        <view>
          <filter class='categorical' column='[売上データ].[地域]' />
          <filter class='categorical' column='[売上データ].[yr:オーダー日:ok]' />
          <datasource-dependencies datasource='売上データ'>
            <column caption='地域' name='[地域]' role='dimension' type='nominal' />
            <column caption='利益率' name='[利益率]' role='measure' type='quantitative'>
              <calculation class='tableau' formula='SUM([利益])/SUM([売上])' />
            </column>
            <column-instance column='[オーダー日]' derivation='Year' name='[yr:オーダー日:ok]' pivot='key' type='ordinal' />
            <column-instance column='[地域]' derivation='None' name='[none:地域:nk]' pivot='key' type='nominal' />
            <column-instance column='[利益率]' derivation='User' name='[usr:利益率:qk]' pivot='key' type='quantitative' />
          </datasource-dependencies>
          <datasource-dependencies datasource='結合データ'>
            <column caption='顧客名' name='[顧客名]' role='dimension' type='nominal' />
          </datasource-dependencies>
          <panes>
            <pane>
              <encodings>
                <color column='[売上データ].[none:地域:nk]' />
              </encodings>
            </pane>
          </panes>
        </view>
        <rows>[売上データ].[usr:利益率:qk]</rows>
        <cols>[売上データ].[none:地域:nk]</cols>
      </table>
    </worksheet>
    <worksheet name='シートB'>
      <table>
        <view />
      </table>
    </worksheet>
    <worksheet name='シートC'>
      <table>
        <view>
          <datasource-dependencies datasource='売上データ'>
            <column caption='担当者' name='[担当者]' role='dimension' type='nominal' />
          </datasource-dependencies>
        </view>
      </table>
    </worksheet>
  </worksheets>
  <dashboards>
    <dashboard name='ダッシュボード1'>
      <zones>
        <zone type-v2='layout-basic'>
          <zone name='シートA' />
          <zone name='シートB' />
        </zone>
      </zones>
    </dashboard>
  </dashboards>
  <windows>
    <window class='worksheet' name='シートA' tab-color='#ff0000' />
    <window class='worksheet' name='シートB' />
    <window class='dashboard' name='ダッシュボード1' tab-color='#00ff00' />
  </windows>
</workbook>
"""


def _analyze_sample():
    root = ET.fromstring(_WORKBOOK_XML)
    return analyze(root)


def test_parameters_excluded_from_datasources():
    spec = _analyze_sample()

    ds_names = [ds.name for ds in spec.datasources]
    assert "Parameters" not in ds_names
    assert "売上データ" in ds_names


def test_parameters_extracted_separately():
    spec = _analyze_sample()

    assert len(spec.parameters) == 1
    assert spec.parameters[0].caption == "しきい値"
    assert spec.parameters[0].current_value == "10"


def test_datasource_table_extraction():
    spec = _analyze_sample()

    ds = next(d for d in spec.datasources if d.name == "売上データ")
    assert ds.connection_class == "federated"
    assert [t.table for t in ds.tables] == ["[売上$]"]


def test_calculated_fields_exclude_auto_column():
    spec = _analyze_sample()

    names = [f.name for f in spec.calculated_fields]
    assert "[Number of Records]" not in names


def test_lod_detection():
    spec = _analyze_sample()

    lod_field = next(f for f in spec.calculated_fields if f.name == "[Calc_LOD]")
    normal_field = next(f for f in spec.calculated_fields if f.name == "[利益率]")
    assert lod_field.is_lod is True
    assert normal_field.is_lod is False


def test_sheet_filters_extracted():
    spec = _analyze_sample()

    sheet_a = next(s for s in spec.sheets if s.name == "シートA")
    sheet_b = next(s for s in spec.sheets if s.name == "シートB")
    assert len(sheet_a.filters) == 2
    assert sheet_a.filters[0].column == "売上データ.地域"
    assert sheet_b.filters == []


def test_sheet_filter_via_column_instance_without_top_level_definition():
    spec = _analyze_sample()

    sheet_a = next(s for s in spec.sheets if s.name == "シートA")
    assert sheet_a.filters[1].column == "売上データ.オーダー日"


def test_datasource_display_name_uses_caption():
    spec = _analyze_sample()

    ds_names = [ds.name for ds in spec.datasources]
    assert "人事データ (人事データ)" in ds_names
    assert "federated.0kjmi6s1inqzi21ddic380yes4yq" not in ds_names


def test_calculated_field_formula_humanizes_internal_reference():
    spec = _analyze_sample()

    diff_field = next(f for f in spec.calculated_fields if f.name == "[Calc_Diff]")
    assert diff_field.formula == "SUM([売上])-[予算]"
    assert "Calculation_123456789012345" not in diff_field.formula


def test_calculated_field_formula_humanizes_non_calculation_prefixed_reference():
    spec = _analyze_sample()

    field = next(f for f in spec.calculated_fields if f.name == "[Calc_Ref2]")
    assert "選択月のSales (コピー)_999" not in field.formula
    assert "[Sales_選択月]" in field.formula


def test_calculated_field_formula_humanizes_parameter_reference():
    spec = _analyze_sample()

    field = next(f for f in spec.calculated_fields if f.name == "[Calc_Ref2]")
    assert field.formula == "[Sales_選択月] / [Parameters].[しきい値]"


def test_calculated_field_depends_on_lists_referenced_captions():
    spec = _analyze_sample()

    diff_field = next(f for f in spec.calculated_fields if f.name == "[Calc_Diff]")
    assert diff_field.depends_on == ["売上", "予算"]

    ref2_field = next(f for f in spec.calculated_fields if f.name == "[Calc_Ref2]")
    assert ref2_field.depends_on == ["Sales_選択月", "しきい値"]


def test_sheet_and_dashboard_tab_color():
    spec = _analyze_sample()

    sheet_a = next(s for s in spec.sheets if s.name == "シートA")
    sheet_b = next(s for s in spec.sheets if s.name == "シートB")
    dashboard = spec.dashboards[0]
    assert sheet_a.color == "#ff0000"
    assert sheet_b.color == ""
    assert dashboard.color == "#00ff00"


def test_sheet_used_fields_and_calculated_fields():
    spec = _analyze_sample()

    sheet_a = next(s for s in spec.sheets if s.name == "シートA")
    assert sheet_a.used_fields == ["地域", "顧客名"]
    assert sheet_a.used_calculated_fields == ["利益率"]


def test_sheet_field_shelves_extracted_from_rows_cols_and_encodings():
    spec = _analyze_sample()

    sheet_a = next(s for s in spec.sheets if s.name == "シートA")
    assert sheet_a.field_shelves["利益率"] == ["行"]
    assert sheet_a.field_shelves["地域"] == ["列", "色", "フィルター", "アクション"]


def test_sheet_field_shelves_empty_for_sheet_without_table_view():
    spec = _analyze_sample()

    sheet_b = next(s for s in spec.sheets if s.name == "シートB")
    assert sheet_b.field_shelves == {}


def test_datasource_join_extracted_with_condition():
    spec = _analyze_sample()

    ds = next(d for d in spec.datasources if d.name == "結合データ")
    assert len(ds.joins) == 1
    join = ds.joins[0]
    assert join.join_type == "inner"
    assert {join.left_table, join.right_table} == {"[dbo].[注文]", "[dbo].[顧客]"}
    assert join.condition == "[注文].[顧客ID] = [顧客].[顧客ID]"


def test_datasource_all_field_captions_includes_all_real_columns():
    spec = _analyze_sample()

    ds = next(d for d in spec.datasources if d.name == "結合データ")
    assert set(ds.all_field_captions) == {"顧客名", "未使用列"}


def test_set_extracted_with_field_and_description():
    spec = _analyze_sample()

    assert len(spec.sets) == 1
    set_info = spec.sets[0]
    assert set_info.name == "上位顧客セット"
    assert set_info.field == "顧客名"
    assert set_info.description == "上位 5 件（降順）"
    assert set_info.datasource == "結合データ"


def test_hidden_action_group_is_not_treated_as_a_set():
    spec = _analyze_sample()

    assert all(s.name != "アクション (Reset)" for s in spec.sets)


def test_action_with_field_captions_annotates_source_sheet():
    spec = _analyze_sample()

    sheet_c = next(s for s in spec.sheets if s.name == "シートC")
    assert sheet_c.field_shelves == {"担当者": ["アクション"]}


def test_action_with_exclude_sheet_source_resolves_dashboard_sheets():
    spec = _analyze_sample()

    sheet_a = next(s for s in spec.sheets if s.name == "シートA")
    assert "アクション" in sheet_a.field_shelves["地域"]


def test_dashboard_embedded_sheets():
    spec = _analyze_sample()

    dashboard = spec.dashboards[0]
    assert dashboard.name == "ダッシュボード1"
    assert set(dashboard.sheets) == {"シートA", "シートB"}


def test_empty_workbook_returns_empty_spec():
    root = ET.fromstring("<workbook version='18.1' />")
    spec = analyze(root)

    assert spec.datasources == []
    assert spec.calculated_fields == []
    assert spec.parameters == []
    assert spec.sheets == []
    assert spec.dashboards == []
