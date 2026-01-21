from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List

from marclite.formats import SUPPORTED_FORMATS, detect_format, emit_event, read_records, write_records


def _format_or_detect(path: Path) -> str:
    return detect_format(path)


def cmd_count(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    emit_event({"event": "start", "operation": "count", "input": str(input_path)})
    try:
        result = read_records(input_path)
    except Exception as exc:  # noqa: BLE001
        emit_event({"event": "error", "message": str(exc)})
        return 1

    emit_event(
        {
            "event": "done",
            "operation": "count",
            "input": str(input_path),
            "format": _format_or_detect(input_path),
            "records": len(result.records),
            "dropped": result.dropped,
            "warnings": result.warnings,
        }
    )
    return 0


def cmd_split(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    out_dir = Path(args.out_dir)
    every = args.every
    out_dir.mkdir(parents=True, exist_ok=True)

    emit_event(
        {
            "event": "start",
            "operation": "split",
            "input": str(input_path),
            "every": every,
            "out_dir": str(out_dir),
        }
    )

    try:
        result = read_records(input_path)
    except Exception as exc:  # noqa: BLE001
        emit_event({"event": "error", "message": str(exc)})
        return 1

    fmt = args.to or _format_or_detect(input_path)
    if fmt not in SUPPORTED_FORMATS:
        emit_event({"event": "error", "message": f"Unsupported output format: {fmt}"})
        return 1

    files_written: List[str] = []
    total_records = len(result.records)
    for idx, start in enumerate(range(0, total_records, every), start=1):
        chunk = result.records[start : start + every]
        filename = f"{input_path.stem}_part{idx:03d}.{fmt if fmt != 'marcxml' else 'xml'}"
        out_path = out_dir / filename
        write_records(chunk, out_path, fmt)
        files_written.append(str(out_path))
        emit_event({"event": "progress", "records_read": min(start + len(chunk), total_records)})

    emit_event(
        {
            "event": "done",
            "operation": "split",
            "files": files_written,
            "records": total_records,
            "dropped": result.dropped,
            "warnings": result.warnings,
        }
    )
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    inputs = [Path(p) for p in args.inputs]
    output_path = Path(args.output)
    fmt = args.to

    emit_event(
        {
            "event": "start",
            "operation": "merge",
            "inputs": [str(p) for p in inputs],
            "output": str(output_path),
            "format": fmt,
        }
    )

    all_records = []
    warnings: List[str] = []
    dropped = 0

    for input_path in inputs:
        try:
            result = read_records(input_path)
        except Exception as exc:  # noqa: BLE001
            emit_event({"event": "error", "message": str(exc)})
            return 1
        all_records.extend(result.records)
        warnings.extend(result.warnings)
        dropped += result.dropped
        emit_event({"event": "progress", "records_read": len(all_records)})

    try:
        write_records(all_records, output_path, fmt)
    except Exception as exc:  # noqa: BLE001
        emit_event({"event": "error", "message": str(exc)})
        return 1

    emit_event(
        {
            "event": "done",
            "operation": "merge",
            "output": str(output_path),
            "records": len(all_records),
            "dropped": dropped,
            "warnings": warnings,
        }
    )
    return 0


def cmd_convert(args: argparse.Namespace) -> int:
    input_path = Path(args.input)
    output_path = Path(args.output)
    fmt = args.to

    emit_event(
        {
            "event": "start",
            "operation": "convert",
            "input": str(input_path),
            "output": str(output_path),
            "format": fmt,
        }
    )

    try:
        result = read_records(input_path)
    except Exception as exc:  # noqa: BLE001
        emit_event({"event": "error", "message": str(exc)})
        return 1

    try:
        write_records(result.records, output_path, fmt)
    except Exception as exc:  # noqa: BLE001
        emit_event({"event": "error", "message": str(exc)})
        return 1

    emit_event(
        {
            "event": "done",
            "operation": "convert",
            "output": str(output_path),
            "records": len(result.records),
            "dropped": result.dropped,
            "warnings": result.warnings,
        }
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="marclite", description="MarcEdit-lite utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)

    count_parser = subparsers.add_parser("count", help="Count records in a MARC file")
    count_parser.add_argument("input")
    count_parser.set_defaults(func=cmd_count)

    split_parser = subparsers.add_parser("split", help="Split a MARC file into chunks")
    split_parser.add_argument("--every", type=int, required=True)
    split_parser.add_argument("input")
    split_parser.add_argument("--out-dir", required=True)
    split_parser.add_argument("--to", choices=sorted(SUPPORTED_FORMATS))
    split_parser.set_defaults(func=cmd_split)

    merge_parser = subparsers.add_parser("merge", help="Merge MARC files")
    merge_parser.add_argument("inputs", nargs="+")
    merge_parser.add_argument("-o", "--output", required=True)
    merge_parser.add_argument("--to", required=True, choices=sorted(SUPPORTED_FORMATS))
    merge_parser.set_defaults(func=cmd_merge)

    convert_parser = subparsers.add_parser("convert", help="Convert MARC files")
    convert_parser.add_argument("input")
    convert_parser.add_argument("-o", "--output", required=True)
    convert_parser.add_argument("--to", required=True, choices=sorted(SUPPORTED_FORMATS))
    convert_parser.set_defaults(func=cmd_convert)

    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
