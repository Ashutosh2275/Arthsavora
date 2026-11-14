"""
Arthsavora CSV Statement Parser
RFC 4180 compliant CSV parser with delimiter sniffing, encoding detection,
Indian bank header recognition, and configurable column mapping.
"""

import csv
import io
import re
from typing import Any, Dict, List, Optional
from app.domain.import_types import HEADER_SYNONYMS, SourceFormat
from app.services.importers.base import BaseStatementParser, ParsedRow, ParserResult


class CsvStatementParser(BaseStatementParser):
    """Parses bank and financial institution CSV statements."""

    ENCODINGS = ["utf-8-sig", "utf-8", "iso-8859-1", "windows-1252"]

    def parse(
        self,
        content_bytes: bytes,
        column_mapping: Optional[Dict[str, str]] = None,
        sheet_name: Optional[str] = None,
        **kwargs: Any,
    ) -> ParserResult:
        """Parses CSV bytes into a ParserResult with ParsedRows."""
        # 1. Decode text with encoding fallback
        text_content: Optional[str] = None
        used_encoding = "utf-8"
        for enc in self.ENCODINGS:
            try:
                text_content = content_bytes.decode(enc)
                used_encoding = enc
                break
            except UnicodeDecodeError:
                continue

        if text_content is None:
            text_content = content_bytes.decode("utf-8", errors="replace")

        lines = [line.strip() for line in text_content.splitlines() if line.strip()]
        if not lines:
            return ParserResult(
                source_format=SourceFormat.CSV.value,
                rows=[],
                metadata={"encoding": used_encoding, "line_count": 0},
            )

        # 2. Sniff delimiter
        sample = "\n".join(lines[:10])
        delimiter = ","
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
            delimiter = dialect.delimiter
        except Exception:
            # Fallback heuristic
            first_line = lines[0]
            for sep in [",", "\t", ";", "|"]:
                if sep in first_line:
                    delimiter = sep
                    break

        # 3. Locate the header row
        # Skip bank metadata rows until we find a row with standard column keywords
        header_idx = -1
        detected_mapping: Dict[str, str] = {}

        for idx, line in enumerate(lines[:20]):
            reader = csv.reader([line], delimiter=delimiter)
            row_cells = next(reader, [])
            clean_cells = [c.strip().lower() for c in row_cells if c.strip()]
            
            # Check match against HEADER_SYNONYMS
            matches = 0
            temp_mapping: Dict[str, str] = {}
            for col_idx, cell in enumerate(row_cells):
                cell_clean = cell.strip().lower()
                for canonical, synonyms in HEADER_SYNONYMS.items():
                    if any(syn == cell_clean or syn in cell_clean for syn in synonyms):
                        if canonical not in temp_mapping:
                            temp_mapping[canonical] = cell.strip()
                            matches += 1
                            break

            # If at least 'date' and ('description' or 'amount' or 'debit') are found
            if matches >= 2 and "date" in temp_mapping:
                header_idx = idx
                detected_mapping = temp_mapping
                break

        # If no explicit header row was identified, assume row 0 is the header
        if header_idx == -1:
            header_idx = 0

        # Apply user column mapping overrides if provided
        final_mapping = dict(detected_mapping)
        if column_mapping:
            final_mapping.update(column_mapping)

        # 4. Parse transaction rows
        csv_reader = csv.DictReader(lines[header_idx:], delimiter=delimiter)
        # Normalize header keys to strip extra whitespace
        if csv_reader.fieldnames:
            csv_reader.fieldnames = [f.strip() if f else f"col_{i}" for i, f in enumerate(csv_reader.fieldnames)]

        rows: List[ParsedRow] = []
        row_num = 1

        for raw_row in csv_reader:
            if not any(v.strip() for v in raw_row.values() if v):
                continue

            # Resolve mapped columns
            date_val = cls_get_mapped_value(raw_row, final_mapping.get("date"), HEADER_SYNONYMS["date"])
            desc_val = cls_get_mapped_value(raw_row, final_mapping.get("description"), HEADER_SYNONYMS["description"])
            amount_val = cls_get_mapped_value(raw_row, final_mapping.get("amount"), HEADER_SYNONYMS["amount"])
            debit_val = cls_get_mapped_value(raw_row, final_mapping.get("debit"), HEADER_SYNONYMS["debit"])
            credit_val = cls_get_mapped_value(raw_row, final_mapping.get("credit"), HEADER_SYNONYMS["credit"])
            bal_val = cls_get_mapped_value(raw_row, final_mapping.get("balance"), HEADER_SYNONYMS["balance"])
            ref_val = cls_get_mapped_value(raw_row, final_mapping.get("ref_no"), HEADER_SYNONYMS["ref_no"])

            # Skip footer summary rows that contain totals or balance summaries in any cell
            row_text = " ".join(str(v) for v in raw_row.values() if v).upper()
            if any(term in row_text for term in ["TOTAL", "OPENING BALANCE", "CLOSING BALANCE"]):
                continue

            # Ensure row has at least date or some financial content
            if not (date_val or desc_val or amount_val or debit_val or credit_val):
                continue

            rows.append(
                ParsedRow(
                    row_number=row_num,
                    raw_data={k: v.strip() if isinstance(v, str) else str(v) for k, v in raw_row.items() if k},
                    date_str=date_val,
                    description_str=desc_val,
                    amount_str=amount_val,
                    debit_str=debit_val,
                    credit_str=credit_val,
                    balance_str=bal_val,
                    ref_str=ref_val,
                )
            )
            row_num += 1

        return ParserResult(
            source_format=SourceFormat.CSV.value,
            rows=rows,
            column_mapping_used=final_mapping,
            metadata={
                "delimiter": delimiter,
                "encoding": used_encoding,
                "header_line_index": header_idx,
                "total_rows_extracted": len(rows),
            },
        )


def cls_get_mapped_value(
    row: Dict[str, str],
    mapped_header: Optional[str],
    synonyms: List[str],
) -> Optional[str]:
    """Helper to retrieve value using explicit mapped header or synonym fallback."""
    if mapped_header and mapped_header in row and row[mapped_header] is not None:
        return row[mapped_header].strip()

    # Case-insensitive synonym search
    for k, v in row.items():
        if not k:
            continue
        k_clean = k.strip().lower()
        if any(syn == k_clean or syn in k_clean for syn in synonyms):
            return (v or "").strip()

    return None
