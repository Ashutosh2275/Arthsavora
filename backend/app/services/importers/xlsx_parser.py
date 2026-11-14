"""
Arthsavora XLSX Statement Parser
Secure Excel workbook parser with formula execution protection (data_only=True),
bounded memory usage, multi-sheet selection, and header mapping.
"""

from datetime import date, datetime
import io
from typing import Any, Dict, List, Optional
import openpyxl

from app.domain.import_types import HEADER_SYNONYMS, SourceFormat
from app.services.importers.base import BaseStatementParser, ParsedRow, ParserResult


class XlsxStatementParser(BaseStatementParser):
    """Parses Excel XLSX statement workbooks safely."""

    MAX_ROWS = 10000
    MAX_COLS = 50

    def parse(
        self,
        content_bytes: bytes,
        column_mapping: Optional[Dict[str, str]] = None,
        sheet_name: Optional[str] = None,
        **kwargs: Any,
    ) -> ParserResult:
        """Parses XLSX bytes without executing formulas."""
        try:
            wb = openpyxl.load_workbook(
                io.BytesIO(content_bytes),
                data_only=True,   # Critical: reads cached values, never executes formulas/macros
                read_only=True,   # Critical: memory-efficient streaming
            )
        except Exception as err:
            return ParserResult(
                source_format=SourceFormat.XLSX.value,
                rows=[],
                metadata={"error": f"Failed to open XLSX workbook: {str(err)}"},
            )

        available_sheets = wb.sheetnames
        target_sheet_name = sheet_name if sheet_name in available_sheets else (available_sheets[0] if available_sheets else None)

        if not target_sheet_name:
            return ParserResult(
                source_format=SourceFormat.XLSX.value,
                rows=[],
                available_sheets=available_sheets,
                metadata={"error": "No valid sheets found in workbook."},
            )

        sheet = wb[target_sheet_name]

        # Read rows up to bounds
        raw_rows: List[List[str]] = []
        for r_idx, row in enumerate(sheet.iter_rows(values_only=True)):
            if r_idx >= self.MAX_ROWS:
                break
            cell_strs: List[str] = []
            for c_idx, cell in enumerate(row):
                if c_idx >= self.MAX_COLS:
                    break
                if cell is None:
                    cell_strs.append("")
                elif isinstance(cell, (datetime, date)):
                    cell_strs.append(cell.strftime("%Y-%m-%d"))
                else:
                    cell_strs.append(str(cell).strip())
            
            if any(cell_strs):
                raw_rows.append(cell_strs)

        wb.close()

        if not raw_rows:
            return ParserResult(
                source_format=SourceFormat.XLSX.value,
                rows=[],
                sheet_name=target_sheet_name,
                available_sheets=available_sheets,
                metadata={"total_rows_extracted": 0},
            )

        # Locate Header Row
        header_idx = -1
        detected_mapping: Dict[str, str] = {}
        headers: List[str] = []

        for idx, row_cells in enumerate(raw_rows[:20]):
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

            if matches >= 2 and "date" in temp_mapping:
                header_idx = idx
                detected_mapping = temp_mapping
                headers = row_cells
                break

        if header_idx == -1:
            header_idx = 0
            headers = [f"col_{i}" for i in range(len(raw_rows[0]))]

        final_mapping = dict(detected_mapping)
        if column_mapping:
            final_mapping.update(column_mapping)

        # Parse Data Rows
        parsed_rows: List[ParsedRow] = []
        row_num = 1

        for row_cells in raw_rows[header_idx + 1:]:
            row_dict = {}
            for col_idx, cell_val in enumerate(row_cells):
                col_name = headers[col_idx] if col_idx < len(headers) and headers[col_idx] else f"col_{col_idx}"
                row_dict[col_name] = cell_val

            if not any(row_dict.values()):
                continue

            date_val = self._get_val(row_dict, final_mapping.get("date"), HEADER_SYNONYMS["date"])
            desc_val = self._get_val(row_dict, final_mapping.get("description"), HEADER_SYNONYMS["description"])
            amount_val = self._get_val(row_dict, final_mapping.get("amount"), HEADER_SYNONYMS["amount"])
            debit_val = self._get_val(row_dict, final_mapping.get("debit"), HEADER_SYNONYMS["debit"])
            credit_val = self._get_val(row_dict, final_mapping.get("credit"), HEADER_SYNONYMS["credit"])
            bal_val = self._get_val(row_dict, final_mapping.get("balance"), HEADER_SYNONYMS["balance"])
            ref_val = self._get_val(row_dict, final_mapping.get("ref_no"), HEADER_SYNONYMS["ref_no"])

            # Filter totals/footers
            desc_str = (desc_val or "").upper()
            if any(term in desc_str for term in ["TOTAL", "OPENING BALANCE", "CLOSING BALANCE"]):
                continue

            if not (date_val or desc_val or amount_val or debit_val or credit_val):
                continue

            parsed_rows.append(
                ParsedRow(
                    row_number=row_num,
                    raw_data=row_dict,
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
            source_format=SourceFormat.XLSX.value,
            rows=parsed_rows,
            sheet_name=target_sheet_name,
            available_sheets=available_sheets,
            column_mapping_used=final_mapping,
            metadata={
                "sheet_name": target_sheet_name,
                "total_rows_extracted": len(parsed_rows),
            },
        )

    def _get_val(
        self,
        row: Dict[str, str],
        mapped: Optional[str],
        synonyms: List[str],
    ) -> Optional[str]:
        if mapped and mapped in row and row[mapped]:
            return row[mapped].strip()
        for k, v in row.items():
            if not k:
                continue
            k_clean = k.strip().lower()
            if any(syn == k_clean or syn in k_clean for syn in synonyms):
                return (v or "").strip()
        return None
