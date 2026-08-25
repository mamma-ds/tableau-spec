"""引数処理と終了コードのみを担当する。"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path

from tableau_spec.analyzer import analyze
from tableau_spec.parser import ParseError, parse
from tableau_spec.reporter import render


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="tableau-spec",
        description="Tableau の .twb / .twbx ファイルを解析して HTML 仕様書を生成する",
    )
    p.add_argument("input", type=Path, help="入力する .twb または .twbx ファイル")
    p.add_argument(
        "-o", "--output", type=Path, default=Path("output.html"), help="出力するHTMLファイルのパス"
    )
    p.add_argument("--open", action="store_true", help="生成後にブラウザで開く")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        root = parse(args.input)
    except ParseError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1

    spec = analyze(root)
    html_text = render(spec, args.input.name)

    try:
        args.output.write_text(html_text, encoding="utf-8")
    except OSError as e:
        print(f"エラー: 出力に失敗しました: {e}", file=sys.stderr)
        return 1

    print(f"仕様書を出力しました: {args.output}")

    if args.open:
        webbrowser.open(args.output.resolve().as_uri())

    return 0


if __name__ == "__main__":
    sys.exit(main())
