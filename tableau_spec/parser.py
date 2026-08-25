"""Tableau .twb / .twbx ファイルの読み込みのみを担当する。"""

from __future__ import annotations

import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


class ParseError(Exception):
    """twb/twbx の読み込み・パースに失敗した場合に発生する例外。"""


def parse(path: Path) -> ET.Element:
    """twb または twbx ファイルを読み込み、XML のルート要素を返す。"""
    path = Path(path)
    if not path.exists():
        raise ParseError(f"ファイルが見つかりません: {path}")

    suffix = path.suffix.lower()
    if suffix == ".twb":
        xml_bytes = _read_twb(path)
    elif suffix == ".twbx":
        xml_bytes = _read_twbx(path)
    else:
        raise ParseError(f"未対応の拡張子です: {path.suffix}")

    try:
        return ET.fromstring(xml_bytes)
    except ET.ParseError as e:
        raise ParseError(f"XMLのパースに失敗しました: {e}") from e


def _read_twb(path: Path) -> bytes:
    try:
        return path.read_bytes()
    except OSError as e:
        raise ParseError(f"ファイルの読み込みに失敗しました: {e}") from e


def _read_twbx(path: Path) -> bytes:
    try:
        with zipfile.ZipFile(path) as z:
            twb_info = next(
                (info for info in z.infolist() if info.filename.endswith(".twb")),
                None,
            )
            if twb_info is None:
                raise ParseError(f"twbxファイル内に.twbが見つかりません: {path}")
            return z.read(twb_info)
    except zipfile.BadZipFile as e:
        raise ParseError(f"twbxファイルの展開に失敗しました: {e}") from e
