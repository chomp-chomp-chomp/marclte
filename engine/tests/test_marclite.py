from __future__ import annotations

from pathlib import Path

from pymarc import Field, Record

from marclite.formats import detect_format, read_records, write_records

FIXTURES = Path(__file__).parent / "fixtures"


def make_mrc(tmp_path: Path) -> Path:
    record1 = Record(force_utf8=True)
    record1.add_field(Field(tag="001", data="0001"))
    record1.add_field(Field(tag="245", indicators=["1", "0"], subfields=["a", "First record"]))
    record2 = Record(force_utf8=True)
    record2.add_field(Field(tag="001", data="0002"))
    record2.add_field(Field(tag="245", indicators=["1", "0"], subfields=["a", "Second record"]))
    out_path = tmp_path / "tiny.mrc"
    write_records([record1, record2], out_path, "mrc")
    return out_path


def test_detect_formats(tmp_path: Path) -> None:
    mrk_path = FIXTURES / "tiny.mrk"
    xml_path = FIXTURES / "tiny.xml"
    mrc_path = make_mrc(tmp_path)

    assert detect_format(mrk_path) == "mrk"
    assert detect_format(xml_path) == "marcxml"
    assert detect_format(mrc_path) == "mrc"


def test_count_records(tmp_path: Path) -> None:
    mrc_path = make_mrc(tmp_path)
    result = read_records(mrc_path)
    assert len(result.records) == 2


def test_split_and_merge(tmp_path: Path) -> None:
    mrc_path = make_mrc(tmp_path)
    result = read_records(mrc_path)
    out_dir = tmp_path / "parts"
    out_dir.mkdir()

    part1 = out_dir / "part1.mrc"
    part2 = out_dir / "part2.mrc"
    write_records(result.records[:1], part1, "mrc")
    write_records(result.records[1:], part2, "mrc")

    merged = tmp_path / "merged.mrc"
    write_records(result.records, merged, "mrc")

    merged_result = read_records(merged)
    assert len(merged_result.records) == 2


def test_convert_outputs(tmp_path: Path) -> None:
    mrk_path = FIXTURES / "tiny.mrk"
    result = read_records(mrk_path)
    out_xml = tmp_path / "out.xml"
    out_mrc = tmp_path / "out.mrc"

    write_records(result.records, out_xml, "marcxml")
    write_records(result.records, out_mrc, "mrc")

    assert read_records(out_xml).records
    assert read_records(out_mrc).records
