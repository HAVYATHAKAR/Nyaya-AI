"""OCR service wrapping PaddleOCR.

Falls back to a Tesseract-free stub when PaddleOCR is unavailable (e.g. on
machines where the paddle wheel isn't built). The stub returns the file
basename + a hint so the demo pipeline can still proceed.
"""
import os
from pathlib import Path
from typing import List, Optional
from loguru import logger

from ..core.config import settings


class OCRService:
    def __init__(self):
        self._ocr = None
        self._initialized = False
        self._stub = False

    def _init_ocr(self):
        if self._initialized:
            return
        try:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang=settings.ocr_lang,
                use_gpu=settings.ocr_use_gpu,
                show_log=False,
            )
            self._initialized = True
            logger.info(f"PaddleOCR initialized (lang={settings.ocr_lang})")
        except Exception as e:
            logger.warning(
                f"PaddleOCR unavailable ({e}); falling back to stub OCR. "
                "Install paddleocr to enable real OCR."
            )
            self._stub = True
            self._initialized = True

    def extract_text(self, file_path: str) -> str:
        """Extract text from an image (PNG/JPG) or PDF (page-by-page)."""
        self._init_ocr()
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(file_path)

        if self._stub:
            return self._stub_text(path)

        ext = path.suffix.lower()
        try:
            if ext in {".pdf"}:
                return self._extract_pdf(path)
            elif ext in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
                return self._extract_image(path)
            else:
                # Try as text file
                try:
                    return path.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    return self._stub_text(path)
        except Exception as e:
            logger.error(f"OCR failed for {file_path}: {e}")
            return self._stub_text(path)

    def _extract_image(self, path: Path) -> str:
        result = self._ocr.ocr(str(path), cls=True)
        return self._flatten(result)

    def _extract_pdf(self, path: Path) -> str:
        # Convert PDF pages to images first
        try:
            from pdf2image import convert_from_path
            images = convert_from_path(str(path), dpi=200)
            texts = []
            for i, img in enumerate(images):
                tmp = path.parent / f"_page_{i}.png"
                img.save(tmp, "PNG")
                r = self._ocr.ocr(str(tmp), cls=True)
                texts.append(self._flatten(r))
                tmp.unlink(missing_ok=True)
            return "\n\n--- Page break ---\n\n".join(texts)
        except Exception as e:
            logger.error(f"PDF OCR failed: {e}")
            return self._stub_text(path)

    def _flatten(self, result) -> str:
        """Flatten PaddleOCR result list into a single string."""
        if not result:
            return ""
        lines = []
        for page in result:
            if not page:
                continue
            for line in page:
                if line and len(line) >= 2:
                    txt = line[1][0] if isinstance(line[1], (list, tuple)) else str(line[1])
                    lines.append(txt)
        return "\n".join(lines)

    def _stub_text(self, path: Path) -> str:
        return (
            f"[OCR stub] Could not run PaddleOCR on {path.name}. "
            f"Install paddleocr with: pip install paddleocr paddlepaddle. "
            f"In demo mode, this document's text is the filename only."
        )


# Singleton
ocr_service = OCRService()
