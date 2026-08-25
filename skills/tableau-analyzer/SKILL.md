---
name: tableau-analyzer
description: >
  Tableau XML の ElementTree から データソース・計算フィールド・LOD式・
  フィルター・パラメーター・シート・ダッシュボード情報を抽出するときに使う。
  XPath クエリや新しい Tableau 要素への対応が必要な場合に起動。
---

# Tableau Analyzer スキル

## 責務
- ET.Element を受け取り WorkbookSpec を返す
- ファイルI/O なし、HTML生成なし

## Tableau XML の重要な構造
以下のサイトに構造が定義されている。参照すること。
https://github.com/tableau/tableau-document-schemas


## 注意点
- `datasource[@name='Parameters']` は datasource 一覧から除外する
- LOD式の検出: 数式に FIXED / INCLUDE / EXCLUDE が含まれるか確認
- XPath で `.//@attr/..` は Python 標準 xml.etree では非対応。
  代わりに `for elem in node.iter(): elem.get("attr")` を使う
- データソースの表示名は `caption` 属性を優先する。`caption` が無い場合のみ `name` を使う
  (`federated.0kjmi6s1inqzi21ddic380yes4yq` のような内部IDをそのまま表示しない)
- 計算フィールドの数式内の内部参照（`[Calculation_xxx]`・`[選択月のSales (コピー)_xxx]` など
  任意の `[...]` 内部名）は、ワークブック全体で構築した「内部名 → caption」対応表を使って
  人間が読める名前に置き換える。対応表は以下を統合して作る:
  - 各 datasource 直下の `<column>` と `<group>`（Action フィルター用の自動生成フィールドは
    `<group caption='...' name='[Action (...)]'>` で定義される）
  - `<column-instance name='[derivation:field:key]' column='[field]'>` は参照先 `column` の
    caption に解決する
  - `[Parameters].[パラメーター 1]` のようなパラメーター参照も同じ対応表で解決する
    (Parameters datasource の column も対応表に含める)
  - 対応表に見つからない参照は元の文字列のまま残す(壊れた数式にしない)
- フィルターの `column` 属性（`[ds].[field]`）も同じ対応表を使い、
  「データソース表示名.フィールド表示名」の形式に解決してから WorkbookSpec に格納する
- シートが使用しているフィールド・計算フィールドは、worksheet 内の
  `<datasource-dependencies>` 配下の `<column>` から抽出する。
  `<calculation class='tableau'>` を持つものは計算フィールド、それ以外は通常フィールドとして分類する
- シート・ダッシュボードのタブ色は `<windows><window class='worksheet' name='...' tab-color='#xxxxxx'>`
  および `class='dashboard'` から名前をキーに抽出する(設定されていない場合は空文字)

## テスト方針
- ET.fromstring() でXML文字列を直接渡してファイル不要
- 正常系・空ワークブック・各要素の抽出を個別にテスト