# Tableau仕様書生成ツール

## プロジェクト概要
Tableau の .twb / .twbx ファイルを解析して HTML 仕様書を生成する CLI ツール。

## アーキテクチャ
責務分離のため6つのモジュールに分割している。
変更時は対応するモジュールのみ修正し、他に影響しないか確認すること。

| モジュール | ファイル | 責務 |
|---|---|---|
| パーサー | tableau_spec/parser.py | ファイルI/O・XML読み込みのみ |
| 解析 | tableau_spec/analyzer.py | XPath・データ抽出のみ |
| レポート | tableau_spec/reporter.py | HTML生成のみ |
| Excelレポート | tableau_spec/excel_reporter.py | Excel(.xlsx)生成のみ |
| CLI | tableau_spec/cli.py | 引数処理・終了コードのみ |
| Web UI | tableau_spec/webapp.py | Streamlit UI・アップロードファイルの一時保存のみ |

webapp.py は parser/analyzer/reporter/excel_reporter をそのまま呼び出すだけで、
XML解析やHTML/Excel生成のロジックは持たない。

reporter.py と excel_reporter.py はどちらも WorkbookSpec から独立して自分の出力形式を
組み立てるだけで、互いには依存しない（usage map計算などの小さなロジックは意図的に
それぞれで持つ。詳細は各ファイル冒頭のdocstring参照）。依存関係ツリーはツリー構造で
表形式に馴染まないため、Excel出力の対象外。

tableau_spec/desktop_launcher.py はPyInstallerでexe化する際の起動エントリポイントのみを担当する
（`streamlit run` を内部的に呼び出すラッパー）。ビジネスロジックは持たない。

## 開発ルール
- 各モジュールの責務を超えた実装をしない
  - parser.py にビジネスロジックを書かない
  - analyzer.py にファイルI/Oを書かない
  - reporter.py にXMLパースを書かない
  - excel_reporter.py にXMLパースを書かない
- 変更後は必ず `python -m pytest tests/ -v` を実行して全テストが通ることを確認する
- 新機能追加時は対応するテストも追加する

## よく使うコマンド
\```bash
# テスト実行
python -m pytest tests/ -v

# カバレッジ確認
python -m pytest tests/ --cov=tableau_spec --cov-report=term-missing

# ツール実行
tableau-spec sample.twb -o output.html --open

# Web UI起動（要: pip install -e .[web]）
tableau-spec-web

# exe化（要: pip install -e .[build]）
pyinstaller TableauSpecWeb.spec --noconfirm
\```

## 現在の既知の制限
- Tableau XMLの名前空間（twb:）がある場合は未対応
- カスタムSQL抽出はrelation type="text" のみ対応
- テーブル結合は2テーブルのpairwise joinを前提に表示（3テーブル以上のネストした結合は「(結合)」とだけ表示され、内訳までは展開しない）
- セットの定義説明は簡略化しており、「上位N件」「メンバー指定」等の大まかな分類のみ。複雑な条件ベースのセットは「条件ベース」とだけ表示される
- ダウンロードしたHTML単体（Streamlit非経由）の検索・絞り込みはクライアントサイドJS（`.tw-name`要素を対象にした`<mark>`ハイライト）による実装。Streamlit版と見た目は同等だが、実装は別（Python側の`_highlight_if_match`/`_highlight_substring` vs JS側の`twHighlightText`）なので、検索対象カラムを変更する際は両方の修正が必要
- テーブル毎のフィールド一覧は`<connection><metadata-records><metadata-record class='column'>`から抽出しており、この要素が無いデータソース（またはTableau Cloud/Serverの「リレーションシップ」データモデルなど未検証の構造）では列名が空になる場合がある。`parent-name`は`relation`の`table`属性ではなく`name`属性（を角括弧で囲んだ形）に一致することがあるため、両方で照合している