"""
Arthsavora PDF Statement Parser
High-fidelity digital statement parser using pdfplumber with table extraction,
statement metadata detection (opening/closing balances), and scanned fallback detection.
"""

from decimal import Decimal
import io
import re
from typing import Any, Dict, List, Optional
import pdfplumber

from app.domain.import_types import HEADER_SYNONYMS, SourceFormat
from app.services.importers.base import BaseStatementParser, ParsedRow, ParserResult


class PdfStatementParser(BaseStatementParser):
    """Parses digital bank statement PDFs with table and text extraction."""

    def parse(
        self,
        content_bytes: bytes,
        column_mapping: Optional[Dict[str, str]] = None,
        sheet_name: Optional[str] = None,
        **kwargs: Any,
    ) -> ParserResult:
        """Extracts tabular records and balance metadata from PDF."""
        extracted_rows: List[ParsedRow] = []
        total_text_length = 0
        account_number: Optional[str] = None
        opening_balance: Optional[Decimal] = None
        closing_balance: Optional[Decimal] = None
        metadata: Dict[str, Any] = {}

        try:
            with pdfplumber.open(io.BytesIO(content_bytes)) as pdf:
                page_count = len(pdf.pages)
                metadata["page_count"] = page_count

                # Pass 1: Extract Text & Metadata from first page
                if page_count > 0:
                    first_page_text = pdf.pages[0].extract_text() or ""
                    total_text_length += len(first_page_text)
                    
                    # Detect Account Number
                    acct_match = re.search(r"(?:Account\s*No|A/C\s*No|Account\s*Number)[:\s]+([A-Z0-9X\*\-]+)", first_page_text, re.IGNORECASE)
                    if acct_match:
                        account_number = acct_match.group(1).strip()

                    # Detect Opening Balance (prefer delimiter/colon or currency marker, avoid date match)
                    open_matches = list(re.finditer(
                        r"(?:Opening\s*Balance|Open\s*Bal)(?:\s*[:=\-]\s*|\s+(?:Rs\.?|INR|₹)\s*)([0-9,]+(?:\.[0-9]{2})?)(?![/])",
                        first_page_text,
                        re.IGNORECASE,
                    ))
                    if not open_matches:
                        open_matches = list(re.finditer(
                            r"(?:Opening\s*Balance|Open\s*Bal)\s+([0-9,]+(?:\.[0-9]{2})?)(?![/])",
                            first_page_text,
                            re.IGNORECASE,
                        ))
                    if open_matches:
                        try:
                            clean_amt = open_matches[0].group(1).replace(",", "")
                            opening_balance = Decimal(clean_amt)
                        except Exception:
                            pass

                    # Detect Closing Balance (check last page, prefer summary footer with colon/delimiter)
                    last_page_text = pdf.pages[-1].extract_text() or ""
                    close_matches = list(re.finditer(
                        r"(?:Closing\s*Balance|Close\s*Bal)(?:\s*[:=\-]\s*|\s+(?:Rs\.?|INR|₹)\s*)([0-9,]+(?:\.[0-9]{2})?)(?![/])",
                        last_page_text,
                        re.IGNORECASE,
                    ))
                    if not close_matches:
                        close_matches = list(re.finditer(
                            r"(?:Closing\s*Balance|Close\s*Bal)\s+([0-9,]+(?:\.[0-9]{2})?)(?![/])",
                            last_page_text,
                            re.IGNORECASE,
                        ))
                    if close_matches:
                        try:
                            # Use the last occurrence on the page (summary footer)
                            clean_amt = close_matches[-1].group(1).replace(",", "")
                            closing_balance = Decimal(clean_amt)
                        except Exception:
                            pass

                # Pass 2: Extract Tables across all pages
                row_counter = 1
                headers: List[str] = []
                detected_mapping: Dict[str, str] = {}

                for p_idx, page in enumerate(pdf.pages):
                    page_text = page.extract_text() or ""
                    total_text_length += len(page_text)

                    tables = page.extract_tables()
                    if not tables:
                        # Fallback attempt for borderless tables using text coordinates
                        try:
                            tables = page.extract_tables(table_settings={"vertical_strategy": "text", "horizontal_strategy": "text"})
                        except Exception:
                            tables = []

                    for table in tables:
                        if not table or len(table) < 2:
                            continue

                        # Check if first row is header
                        potential_headers = [str(c).strip() if c else "" for c in table[0]]
                        header_matches = 0
                        temp_map: Dict[str, str] = {}

                        for c_idx, cell in enumerate(potential_headers):
                            cell_clean = cell.lower()
                            for canonical, synonyms in HEADER_SYNONYMS.items():
                                if any(syn == cell_clean or syn in cell_clean for syn in synonyms):
                                    if canonical not in temp_map:
                                        temp_map[canonical] = cell
                                        header_matches += 1
                                        break

                        data_start_idx = 1
                        if header_matches >= 2 and "date" in temp_map:
                            headers = potential_headers
                            detected_mapping = temp_map
                        elif not headers:
                            # Not a recognized financial table
                            continue
                        else:
                            # Table continues from previous page
                            data_start_idx = 0

                        # Apply user column mapping overrides if provided
                        final_mapping = dict(detected_mapping)
                        if column_mapping:
                            final_mapping.update(column_mapping)

                        for row_data in table[data_start_idx:]:
                            if not any(row_data):
                                continue

                            row_dict = {}
                            for col_idx, cell_val in enumerate(row_data):
                                col_name = headers[col_idx] if col_idx < len(headers) and headers[col_idx] else f"col_{col_idx}"
                                row_dict[col_name] = str(cell_val).strip() if cell_val else ""

                            date_val = self._get_val(row_dict, final_mapping.get("date"), HEADER_SYNONYMS["date"])
                            desc_val = self._get_val(row_dict, final_mapping.get("description"), HEADER_SYNONYMS["description"])
                            amount_val = self._get_val(row_dict, final_mapping.get("amount"), HEADER_SYNONYMS["amount"])
                            debit_val = self._get_val(row_dict, final_mapping.get("debit"), HEADER_SYNONYMS["debit"])
                            credit_val = self._get_val(row_dict, final_mapping.get("credit"), HEADER_SYNONYMS["credit"])
                            bal_val = self._get_val(row_dict, final_mapping.get("balance"), HEADER_SYNONYMS["balance"])
                            ref_val = self._get_val(row_dict, final_mapping.get("ref_no"), HEADER_SYNONYMS["ref_no"])

                            # Skip total rows
                            row_text = " ".join(str(v) for v in row_dict.values() if v).upper()
                            if any(term in row_text for term in ["TOTAL", "OPENING BALANCE", "CLOSING BALANCE"]):
                                continue

                            if not (date_val or desc_val or amount_val or debit_val or credit_val):
                                continue

                            extracted_rows.append(
                                ParsedRow(
                                    row_number=row_counter,
                                    raw_data=row_dict,
                                    date_str=date_val,
                                    description_str=desc_val,
                                    amount_str=amount_val,
                                    debit_str=debit_val,
                                    credit_str=credit_val,
                                    balance_str=bal_val,
                                    ref_str=ref_val,
                                    confidence_score=Decimal("1.00"),
                                )
                            )
                            row_counter += 1

        except Exception as err:
            return ParserResult(
                source_format=SourceFormat.PDF_TEXT.value,
                rows=[],
                metadata={"error": f"PDF parse exception: {str(err)}"},
            )

        # Check if PDF contains virtually no digital text (scanned PDF image)
        is_scanned = total_text_length < 50 and len(extracted_rows) == 0

        metadata.update({
            "total_text_length": total_text_length,
            "is_scanned": is_scanned,
            "total_rows_extracted": len(extracted_rows),
        })

        return ParserResult(
            source_format=SourceFormat.PDF_TEXT.value,
            rows=extracted_rows,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            account_number=account_number,
            column_mapping_used=detected_mapping,
            metadata=metadata,
            is_ocr=is_scanned,
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
