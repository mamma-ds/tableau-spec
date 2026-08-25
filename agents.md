# サブエージェント定義

## orchestrator（オーケストレーター）
- ユーザーのリクエストを受け取り、適切なサブエージェントに割り振る
- 各エージェントの結果を統合して最終アウトプットを返す
- コードは書かない。指示と統合のみ

## parser-agent
- 担当: tableau_spec/parser.py と tests/test_parser.py
- 使用スキル: skills/tableau-parser/SKILL.md
- できること: twb/twbxの読み込み方法の改善、エラーハンドリングの強化

## analyzer-agent
- 担当: tableau_spec/analyzer.py と tests/test_analyzer.py
- 使用スキル: skills/tableau-analyzer/SKILL.md
- できること: 新しいTableau要素の抽出ロジック追加

## reporter-agent
- 担当: tableau_spec/reporter.py と tests/test_reporter.py
- 使用スキル: skills/tableau-reporter/SKILL.md
- できること: HTML出力のデザイン改善、新セクション追加

## test-agent
- 担当: tests/ 配下全体
- できること: テストの追加・修正、カバレッジ向上
- ルール: 実装コードは変更しない
- テスト種別:
  - 単体テスト: 各モジュールのSKILL.md方針に従い、合成データ（ET.fromstring・tmp_path等）で実ファイル不要
  - 結合テスト: tests/test_integration.py で sample/ 配下の実twbxファイルを使い、parser→analyzer→reporter の一連の流れを検証する