"""
Arthsavora Document Preprocessing Pipeline
Preserves raw original receipt images and generates enhanced derivative images
for optimal OCR extraction (EXIF correction, grayscale, contrast enhancement, noise reduction).
"""

import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Preprocesses images to maximize OCR character recognition accuracy."""

    @staticmethod
    def preprocess_image(
        input_path: str,
        output_path: Optional[str] = None,
        contrast_factor: float = 1.5,
        apply_noise_filter: bool = True,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Enhances receipt/invoice image and saves derivative.
        Returns (preprocessed_path, metadata_dict).
        """
        src = Path(input_path)
        if not src.exists():
            raise FileNotFoundError(f"Source image not found at {input_path}")

        if not output_path:
            output_path = str(src.parent / f"preprocessed_{src.stem}.png")

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        operations = []
        with Image.open(src) as img:
            original_size = (img.width, img.height)
            original_mode = img.mode

            # 1. EXIF orientation correction
            try:
                transposed = ImageOps.exif_transpose(img)
                if transposed is not None:
                    img = transposed
                    operations.append("exif_transpose")
            except Exception as e:
                logger.warning(f"EXIF transpose failed: {e}")

            # 2. Convert to grayscale for contrast isolation
            if img.mode != "L":
                img = img.convert("L")
                operations.append("grayscale_conversion")

            # 3. Contrast enhancement
            if contrast_factor != 1.0:
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(contrast_factor)
                operations.append(f"contrast_boost_{contrast_factor}")

            # 4. Noise reduction via median filter
            if apply_noise_filter:
                img = img.filter(ImageFilter.MedianFilter(size=3))
                operations.append("median_noise_filter")

            # 5. Save derivative as high-quality PNG
            img.save(out, format="PNG", optimize=True)

        metadata = {
            "original_dimensions": list(original_size),
            "original_mode": original_mode,
            "preprocessed_path": str(out),
            "operations_applied": operations,
        }
        return str(out), metadata
