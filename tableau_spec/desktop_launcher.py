"""PyInstaller でexe化する際の起動エントリポイント。streamlit run を内部的に呼び出す。"""

from __future__ import annotations

import sys
import webbrowser
from pathlib import Path
from threading import Timer

# webapp.py を streamlit run 対象のファイルとして同梱するため、
# 依存モジュールをPyInstallerの静的解析に辿らせる目的でここでimportしておく。
import tableau_spec.webapp  # noqa: F401


def _bundle_root() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parent.parent


def main() -> None:
    from streamlit.web import cli as stcli

    app_path = _bundle_root() / "tableau_spec" / "webapp.py"

    Timer(2.0, lambda: webbrowser.open("http://localhost:8501")).start()

    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--global.developmentMode=false",
        "--server.headless=false",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
