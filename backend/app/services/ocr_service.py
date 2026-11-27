"""OCR adapter that fails explicitly rather than fabricating document text."""
from pathlib import Path
import tempfile
from loguru import logger
from ..core.config import settings


class OCRService:
    def __init__(self):
        self._ocr = None
        self._initialized = False

    def _init_ocr(self):
        if self._initialized:
            if self._ocr is None:
                raise RuntimeError("OCR dependency is unavailable")
            return
        self._initialized = True
        try:
            from paddleocr import PaddleOCR
            self._ocr = PaddleOCR(use_angle_cls=True, lang=settings.ocr_lang,
                                  use_gpu=settings.ocr_use_gpu, show_log=False)
        except Exception as exc:
            logger.warning("OCR initialization failed ({})", type(exc).__name__)
            raise RuntimeError("OCR dependency is unavailable") from exc

    def extract_text(self, file_path: str) -> str:
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError("Uploaded document is unavailable")
        ext = path.suffix.lower()
        if ext == ".txt":
            return path.read_text(encoding="utf-8", errors="replace").strip()
        self._init_ocr()
        if ext == ".pdf":
            return self._extract_pdf(path)
        if ext in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
            return self._flatten(self._ocr.ocr(str(path), cls=True))
        raise ValueError("Unsupported document type")

    def _extract_pdf(self, path: Path) -> str:
        try:
            from pdf2image import convert_from_path
            pages = convert_from_path(str(path), dpi=180, first_page=1, last_page=20)
            texts = []
            for page in pages:
                temp_path = None
                try:
                    with tempfile.NamedTemporaryFile(suffix=".png", dir=path.parent, delete=False) as temp:
                        temp_path = Path(temp.name)
                    page.save(str(temp_path), "PNG")
                    texts.append(self._flatten(self._ocr.ocr(str(temp_path), cls=True)))
                finally:
                    if temp_path:
                        temp_path.unlink(missing_ok=True)
            return "\n\n--- Page break ---\n\n".join(t for t in texts if t).strip()
        except Exception as exc:
            logger.warning("PDF OCR failed ({})", type(exc).__name__)
            raise RuntimeError("PDF OCR failed; verify PDF support and file readability") from exc

    @staticmethod
    def _flatten(result) -> str:
        lines = []
        for page in result or []:
            for line in page or []:
                if line and len(line) >= 2:
                    value = line[1][0] if isinstance(line[1], (list, tuple)) else str(line[1])
                    if value:
                        lines.append(str(value))
        return "\n".join(lines).strip()


ocr_service = OCRService()
