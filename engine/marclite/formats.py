from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, List, Optional

from pymarc import Field, MARCReader, MARCWriter, Record, marcxml

from marclite.mrk import parse_mrk_records, write_mrk_records


SUPPORTED_FORMATS = {"mrc", "mrk", "marcxml"}


@dataclass
class ReadResult:
    records: List[Record]
    warnings: List[str]
    dropped: int


def detect_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".xml":
        return "marcxml"
    if suffix in {".mrk", ".txt"}:
        return "mrk"
    if suffix == ".mrc":
        return "mrc"

    with path.open("rb") as handle:
        sample = handle.read(2048)

    try:
        text_sample = sample.decode("utf-8", errors="ignore")
    except UnicodeDecodeError:
        text_sample = ""

    if text_sample.lstrip().startswith("<?xml") or "<record" in text_sample[:500]:
        return "marcxml"

    if len(sample) > 6 and sample[:5].isdigit() and b"\x1d" in sample:
        return "mrc"

    for line in text_sample.splitlines()[:20]:
        if line.startswith("=LDR") or re.match(r"^=\d{3}", line):
            return "mrk"

    raise ValueError(f"Unable to detect MARC format for {path.name}.")


def read_records(path: Path, fmt: Optional[str] = None) -> ReadResult:
    fmt = fmt or detect_format(path)
    warnings: List[str] = []
    records: List[Record] = []
    dropped = 0

    if fmt == "mrc":
        with path.open("rb") as handle:
            reader = MARCReader(handle, to_unicode=True, force_utf8=True, utf8_handling="ignore")
            for idx, record in enumerate(reader, start=1):
                try:
                    if record is None:
                        raise ValueError("Empty record")
                    records.append(record)
                except Exception as exc:  # noqa: BLE001
                    dropped += 1
                    warnings.append(f"Dropped record {idx}: {exc}")
        return ReadResult(records, warnings, dropped)

    if fmt == "marcxml":
        try:
            records = marcxml.parse_xml_to_array(str(path))
        except Exception as exc:  # noqa: BLE001
            raise ValueError(f"Failed to parse MARCXML: {exc}") from exc
        return ReadResult(records, warnings, dropped)

    if fmt == "mrk":
        text = path.read_text(encoding="utf-8", errors="replace")
        try:
            records = list(parse_mrk_records(text))
        except ValueError as exc:
            raise ValueError(f"Failed to parse MRK: {exc}") from exc
        return ReadResult(records, warnings, dropped)

    raise ValueError(f"Unsupported format: {fmt}")


def write_records(records: Iterable[Record], path: Path, fmt: str) -> None:
    if fmt == "mrc":
        with path.open("wb") as handle:
            writer = MARCWriter(handle)
            for record in records:
                writer.write(record)
            writer.close()
        return

    if fmt == "marcxml":
        with path.open("wb") as handle:
            writer = marcxml.XMLWriter(handle)
            for record in records:
                writer.write(record)
            writer.close()
        return

    if fmt == "mrk":
        text = write_mrk_records(records)
        path.write_text(text, encoding="utf-8")
        return

    raise ValueError(f"Unsupported output format: {fmt}")


def emit_event(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False))
