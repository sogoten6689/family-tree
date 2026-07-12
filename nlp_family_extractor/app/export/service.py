from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Tuple


class ExportFormat(str, Enum):
    JSON = "json"
    CSV = "csv"
    GEDCOM = "gedcom"


def _now_gedcom_date() -> str:
    return datetime.now(timezone.utc).strftime("%d %b %Y").upper()


def export_json(doc: Dict[str, Any]) -> Tuple[str, str, str]:
    payload = {
        "id": doc.get("id"),
        "name": doc.get("name"),
        "description": doc.get("description"),
        "nodes": doc.get("nodes", []),
        "exported_at": datetime.now(timezone.utc).isoformat(),
    }
    content = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    filename = f"{doc['id']}.json"
    return content, filename, "application/json; charset=utf-8"


def export_csv(doc: Dict[str, Any]) -> Tuple[str, str, str]:
    nodes = doc.get("nodes", [])
    buffer = io.StringIO()
    buffer.write("\ufeff")  # UTF-8 BOM for Excel VN
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "name",
            "gender",
            "birth_year",
            "death_year",
            "father_id",
            "mother_id",
            "spouse_ids",
            "title",
            "bio",
        ]
    )
    for node in nodes:
        if not isinstance(node, dict):
            continue
        pids = node.get("pids") or []
        spouse_ids = ";".join(str(pid) for pid in pids) if isinstance(pids, list) else ""
        writer.writerow(
            [
                node.get("id", ""),
                node.get("name", ""),
                node.get("gender", ""),
                node.get("birthYear", ""),
                node.get("deathYear", ""),
                node.get("fid", ""),
                node.get("mid", ""),
                spouse_ids,
                node.get("title", ""),
                node.get("bio", ""),
            ]
        )
    filename = f"{doc['id']}.csv"
    return buffer.getvalue(), filename, "text/csv; charset=utf-8"


def _gedcom_escape(value: str) -> str:
    return value.replace("@", "@@")


def _write_individual(lines: List[str], xref: str, node: Dict[str, Any]) -> None:
    lines.append(f"0 {xref} INDI")
    name = str(node.get("name") or "").strip()
    if name:
        lines.append(f"1 NAME {_gedcom_escape(name)}")
    gender = node.get("gender")
    if gender == "male":
        lines.append("1 SEX M")
    elif gender == "female":
        lines.append("1 SEX F")
    birth_year = node.get("birthYear")
    if birth_year is not None:
        lines.append("1 BIRT")
        lines.append(f"2 DATE {int(birth_year)}")
    death_year = node.get("deathYear")
    if death_year is not None:
        lines.append("1 DEAT")
        lines.append(f"2 DATE {int(death_year)}")
    title = node.get("title")
    if isinstance(title, str) and title.strip():
        lines.append(f"1 TITL {_gedcom_escape(title.strip())}")
    bio = node.get("bio")
    if isinstance(bio, str) and bio.strip():
        lines.append(f"1 NOTE {_gedcom_escape(bio.strip())}")


def _write_family(
    lines: List[str],
    fam_xref: str,
    husband_xref: str | None,
    wife_xref: str | None,
    child_xrefs: List[str],
) -> None:
    lines.append(f"0 {fam_xref} FAM")
    if husband_xref:
        lines.append(f"1 HUSB {husband_xref}")
    if wife_xref:
        lines.append(f"1 WIFE {wife_xref}")
    for child in child_xrefs:
        lines.append(f"1 CHIL {child}")


def export_gedcom(doc: Dict[str, Any]) -> Tuple[str, str, str]:
    """GEDCOM 5.5.1 export — UTF-8 names preserved, no latinize (D3)."""
    nodes = [n for n in doc.get("nodes", []) if isinstance(n, dict)]
    by_id = {int(n["id"]): n for n in nodes if n.get("id") is not None}

    lines: List[str] = [
        "0 HEAD",
        "1 SOUR FamilyTree",
        "2 VERS 1.0",
        "1 GEDC",
        "2 VERS 5.5.1",
        "2 FORM LINEAGE-LINKED",
        "1 CHAR UTF-8",
        f"1 DATE {_now_gedcom_date()}",
    ]

    indi_xref: Dict[int, str] = {}
    for node_id in sorted(by_id):
        xref = f"@I{node_id}@"
        indi_xref[node_id] = xref
        _write_individual(lines, xref, by_id[node_id])

    fam_counter = 1
    seen_fams: set[tuple] = set()

    for node_id, node in sorted(by_id.items()):
        pids = node.get("pids") or []
        if not isinstance(pids, list):
            continue
        for pid in pids:
            try:
                spouse_id = int(pid)
            except (TypeError, ValueError):
                continue
            if spouse_id not in by_id or spouse_id <= node_id:
                continue
            pair = (node_id, spouse_id)
            if pair in seen_fams:
                continue
            seen_fams.add(pair)

            a = by_id[node_id]
            b = by_id[spouse_id]
            if a.get("gender") == "female" or b.get("gender") != "female":
                husband_id, wife_id = node_id, spouse_id
                if a.get("gender") == "female" and b.get("gender") == "male":
                    husband_id, wife_id = spouse_id, node_id
            else:
                husband_id, wife_id = node_id, spouse_id

            children = sorted(
                cid
                for cid, child in by_id.items()
                if child.get("fid") == husband_id or child.get("mid") == wife_id
            )
            fam_xref = f"@F{fam_counter}@"
            fam_counter += 1
            _write_family(
                lines,
                fam_xref,
                indi_xref.get(husband_id),
                indi_xref.get(wife_id),
                [indi_xref[cid] for cid in children if cid in indi_xref],
            )
            lines.append(f"1 {indi_xref[husband_id]} FAMS {fam_xref}")
            lines.append(f"1 {indi_xref[wife_id]} FAMS {fam_xref}")
            for cid in children:
                if cid in indi_xref:
                    lines.append(f"1 {indi_xref[cid]} FAMC {fam_xref}")

    lines.append("0 TRLR")
    content = "\r\n".join(lines) + "\r\n"
    filename = f"{doc['id']}.ged"
    return content, filename, "text/plain; charset=utf-8"


class FamilyTreeExportService:
    def export(self, doc: Dict[str, Any], fmt: ExportFormat) -> Tuple[str, str, str]:
        if fmt == ExportFormat.JSON:
            return export_json(doc)
        if fmt == ExportFormat.CSV:
            return export_csv(doc)
        if fmt == ExportFormat.GEDCOM:
            return export_gedcom(doc)
        raise ValueError(f"unsupported export format: {fmt}")
