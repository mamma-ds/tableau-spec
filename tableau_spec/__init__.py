"""tableau-spec パッケージの初期化のみを担当する。バージョン情報のみを公開する。"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("tableau-spec")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"
