# Tableau仕様書生成ツール

## プロジェクト概要
Tableau の .twb / .twbx ファイルを解析して HTML 仕様書を生成する CLI ツール。

## アーキテクチャ
責務分離のため5つのモジュールに分割している。
変更時は対応するモジュールのみ修正し、他に影響しないか確認すること。

| モジュール | ファイル | 責務 |
|---|---|---|
| パーサー | tableau_spec/parser.py | ファイルI/O・XML読み込みのみ |
| 解析 | tableau_spec/analyzer.py | XPath・データ抽出のみ |
| レポート | tableau_spec/reporter.py | HTML生成のみ |
| CLI | tableau_spec/cli.py | 引数処理・終了コードのみ |
| Web UI | tableau_spec/webapp.py | Streamlit UI・アップロードファイルの一時保存のみ |

webapp.py は parser/analyzer/reporter をそのまま呼び出すだけで、XML解析やHTML生成のロジックは持たない。

## 開発ルール
- 各モジュールの責務を超えた実装をしない
  - parser.py にビジネスロジックを書かない
  - analyzer.py にファイルI/Oを書かない
  - reporter.py にXMLパースを書かない
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
\```

## 現在の既知の制限
- Tableau XMLの名前空間（twb:）がある場合は未対応
- カスタムSQL抽出はrelation type="text" のみ対応
- テーブル結合は2テーブルのpairwise joinを前提に表示（3テーブル以上のネストした結合は「(結合)」とだけ表示され、内訳までは展開しない）
- セットの定義説明は簡略化しており、「上位N件」「メンバー指定」等の大まかな分類のみ。複雑な条件ベースのセットは「条件ベース」とだけ表示される
- ダウンロードしたHTML単体（Streamlit非経由）の検索・絞り込みはクライアントサイドJSによる簡易実装で、行の表示/非表示のみ（Streamlit版のような`<mark>`ハイライトはしない）