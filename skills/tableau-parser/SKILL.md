---
name: tableau-parser
description: >
  Tableau の .twb または .twbx ファイルを読み込んで XML ElementTree を返す処理を
  扱うときに使う。ファイルI/O、zip展開、XMLパースエラーの処理が含まれる場合に起動。
---

# Tableau Parser スキル

## 責務
- .twb（XML）と .twbx（zip内のXML）の読み込み
- ParseError による明示的なエラーハンドリング
- ビジネスロジックは一切含まない

## コード規約
- 戻り値は常に `ET.Element`（rootノード）
- エラーは `ParseError` を raise する（sys.exit しない）
- ファイルパスは `pathlib.Path` で扱う

## テスト方針
- 正常系: twb/twbx それぞれで ET.Element が返ること
- 異常系: 存在しないファイル、不正なXML、空のtwbx は ParseError
- tmp_path フィクスチャを使い、実ファイルは作らない