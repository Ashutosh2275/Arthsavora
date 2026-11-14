# ARTHSAVORA — PDF BANK STATEMENT PROCESSING & OCR ADAPTATION

## 1. Overview & Dual Extraction Engine

Bank statements delivered in PDF format present unique engineering challenges due to mixed document structures: digitally generated vector PDFs (containing structured font tables and layout rectangles) versus scanned raster images (e.g., photocopies or mobile phone scans).

Arthsavora employs a two-tier extraction architecture:
1. **Tier 1 (Digital Vector PDF)**: `PdfStatementParser` using `pdfplumber` for zero-loss text extraction, cell boundary detection, and balance metadata extraction.
2. **Tier 2 (Scanned Raster PDF)**: `OcrStatementAdapter` using `pytesseract` and Tesseract OCR engine when digital text content is less than 50 characters across the entire document.

---

## 2. Digital PDF Extraction (`PdfStatementParser`)

### 2.1 Table Detection Strategy
The parser analyzes every page of the uploaded PDF:
- **Vector Line Mode**: Attempts extraction using PDF line art rectangles (`page.extract_tables()`).
- **Text Coordinate Fallback**: If no grid lines exist (borderless layout tables), the parser falls back to text coordinate analysis:
  ```python
  page.extract_tables(table_settings={"vertical_strategy": "text", "horizontal_strategy": "text"})
  ```

### 2.2 Header Detection & Page Spanning
- Inspects the top row of extracted tables for canonical header synonyms (`Date`, `Narration`, `Withdrawal`, `Deposit`, `Balance`).
- When a statement spans multiple pages, subsequent page tables inherit the column mapping established on page 1 without expecting repeated header rows.

### 2.3 Statement Metadata Regex Extraction
Before processing transaction rows, the parser scans page 1 and the final page for key banking metadata:
- **Account Number**:
  ```regex
  (?:Account\s*No|A/C\s*No|Account\s*Number)[:\s]+([A-Z0-9X\*\-]+)
  ```
- **Opening Balance**:
  ```regex
  (?:Opening\s*Balance|Open\s*Bal)(?:\s*[:=\-]\s*|\s+(?:Rs\.?|INR|₹)\s*)([0-9,]+(?:\.[0-9]{2})?)(?![/])
  ```
- **Closing Balance**:
  ```regex
  (?:Closing\s*Balance|Close\s*Bal)(?:\s*[:=\-]\s*|\s+(?:Rs\.?|INR|₹)\s*)([0-9,]+(?:\.[0-9]{2})?)(?![/])
  ```
Negative lookahead `(?![/])` guarantees that dates such as `14/11/2026` are never misclassified as closing balances.

---

## 3. Scanned PDF & OCR Processing (`OcrStatementAdapter`)

### 3.1 Scanned Document Detection
If the total digital text length extracted from all pages is below 50 characters, `PdfStatementParser` flags `is_scanned = True` and activates `OcrStatementAdapter`.

### 3.2 Image Pre-processing
When image extraction is triggered:
1. Converts PDF pages into high-resolution images ($300\text{ DPI}$).
2. Converts to 8-bit grayscale.
3. Applies Otsu's thresholding to remove paper shadows and crease artifacts.

### 3.3 Confidence Tracking
Unlike digital extraction (assigned baseline confidence `1.00`), OCR extracted candidates are assigned confidence `0.70`. 
This confidence score is stored directly on `ImportCandidate.confidence_score` and displayed in the review UI with a visual confidence badge, alerting users to inspect OCR-extracted figures closely.

---

## 4. Password-Protected Statements

Indian banks commonly distribute PDF statements encrypted with user birth dates, PAN card numbers, or mobile numbers (e.g., standard SBI/HDFC 8-character passwords).
- The import system detects `pypdf.errors.FileNotDecryptedError`.
- Returns an explicit `ValidationException("Statement is password-protected. Please provide the statement password.")`.
- Allows re-submission with `password` parameter passed securely in memory without persisting the cleartext password to disk.
