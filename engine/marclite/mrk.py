from __future__ import annotations

import re
from typing import Iterable, Iterator, List

from pymarc import Field, Record


TAG_RE = re.compile(r"^=(?P<tag>\w{3})")


def parse_mrk_records(text: str) -> Iterator[Record]:
    blocks: List[List[str]] = []
    current: List[str] = []
    for line in text.splitlines():
        if line.strip() == "":
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line.rstrip("\n"))
    if current:
        blocks.append(current)

    if not blocks:
        raise ValueError("No MRK records found.")

    for block in blocks:
        yield parse_mrk_record(block)


def parse_mrk_record(lines: Iterable[str]) -> Record:
    record = Record(force_utf8=True)
    seen_field = False

    for line in lines:
        if not line.startswith("="):
            raise ValueError(f"Invalid MRK line: {line}")
        match = TAG_RE.match(line)
        if not match:
            raise ValueError(f"Invalid MRK tag: {line}")
        tag = match.group("tag")
        rest = line[4:]
        if rest.startswith(" "):
            rest = rest[1:]

        if tag == "LDR":
            record.leader = rest.strip()
            seen_field = True
            continue

        if tag.startswith("00"):
            data = rest.strip()
            record.add_field(Field(tag=tag, data=data))
            seen_field = True
            continue

        if len(rest) < 2:
            raise ValueError(f"Missing indicators for tag {tag}")
        ind1 = rest[0]
        ind2 = rest[1]
        subfield_data = rest[2:]
        subfields: List[str] = []
        for chunk in subfield_data.split("$"):
            if not chunk:
                continue
            code = chunk[0]
            value = chunk[1:]
            subfields.extend([code, value])
        record.add_field(Field(tag=tag, indicators=[ind1, ind2], subfields=subfields))
        seen_field = True

    if not seen_field:
        raise ValueError("Record contained no MARC fields.")

    return record


def write_mrk_records(records: Iterable[Record]) -> str:
    output_lines: List[str] = []
    for record in records:
        output_lines.append(f"=LDR  {record.leader}")
        for field in record.fields:
            if field.is_control_field():
                output_lines.append(f"={field.tag}  {field.data}")
                continue
            ind1 = field.indicators[0] if field.indicators else " "
            ind2 = field.indicators[1] if len(field.indicators) > 1 else " "
            subfields = "".join(
                f"${code}{value}" for code, value in zip(field.subfields[0::2], field.subfields[1::2])
            )
            output_lines.append(f"={field.tag}  {ind1}{ind2}{subfields}")
        output_lines.append("")
    return "\n".join(output_lines).rstrip() + "\n"
