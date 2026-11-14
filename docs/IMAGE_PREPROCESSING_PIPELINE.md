# Image Preprocessing Pipeline

## 1. Principles of Non-Destructive Processing

When processing physical receipts, thermal paper prints, and camera photos, raw image quality directly impacts optical character recognition precision. Arthsavora implements a dedicated image enhancement stage that strictly preserves raw image provenance.

### Core Invariants
1. **Raw File Invariant**: The uploaded original file (`original.jpg`, `original.png`) is written to disk immutable and byte-for-byte identical to what the user submitted.
2. **Derivative Isolation**: Preprocessing produces an isolated derivative image (`preprocessed_{stem}.png`).
3. **Audit Trail**: Preprocessing operations, original image dimensions, and original color modes are saved in `financial_documents.preprocessing_metadata`.

---

## 2. Pipeline Sequence

The `ImagePreprocessor.preprocess_image()` pipeline applies sequential transformations optimized for receipt text recognition:

### Step 1: EXIF Orientation Transpose
- **Problem**: Mobile photos taken on smartphones (iOS/Android) embed orientation metadata in EXIF headers (e.g., orientation 6 = 90 deg clockwise). Unprocessed raster loaders render these rotated, causing OCR engines to scan upside down or sideways.
- **Solution**: `PIL.ImageOps.exif_transpose(img)` analyzes EXIF flags and physically transposes pixel arrays to standard upright orientation before stripping EXIF.

### Step 2: Grayscale Conversion
- **Problem**: Background colors, watermarks, colored borders, and paper tints introduce color noise.
- **Solution**: Converts mode (`RGB`, `RGBA`) to luminance channel (`L`), isolating character darkness from chromatic variance.

### Step 3: Contrast Enhancement
- **Problem**: Faded thermal receipts and low-light mobile photography have poor text-to-background contrast.
- **Solution**: `PIL.ImageEnhance.Contrast(img).enhance(1.5)` expands the dynamic range, rendering faint characters darker and light paper brighter.

### Step 4: Noise Filtering
- **Problem**: Salt-and-pepper noise and paper texture artifacts confuse character segmentation.
- **Solution**: `PIL.ImageFilter.MedianFilter(size=3)` eliminates isolated noise pixels while preserving sharp alphanumeric edges.

### Step 5: High-Quality Lossless Derivative
- The resulting image is exported as an uncompressed 24-bit/8-bit PNG for OCR engine consumption.

---

## 3. Metadata Structure

Upon completion, `financial_documents.preprocessing_metadata` contains:

```json
{
  "original_dimensions": [1200, 1850],
  "original_mode": "RGB",
  "preprocessed_path": "storage/documents/ws-1/doc-1/preprocessed_receipt.png",
  "operations_applied": [
    "exif_transpose",
    "grayscale_conversion",
    "contrast_boost_1.5",
    "median_noise_filter"
  ]
}
```
