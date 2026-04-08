from __future__ import annotations
import os
from typing import List, Dict
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger(__name__)


DOCUMENTS_PATH = "data/documents"


# helpers
def detect_document_type(filename: str) -> str:
    name = filename.lower()

    if name.startswith("policy_"):
        return "policy"
    elif name.startswith("sop_"):
        return "procedure"
    elif name.startswith("faq_"):
        return "faq"
    return "general"


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = text.encode("utf-8", errors="ignore").decode("utf-8")

    lines = [line.rstrip() for line in text.splitlines()]

    return "\n".join(lines).strip()


def extract_headings(text: str) -> List[str]:
    headings = []

    for line in text.splitlines():
        line = line.strip()
        if line.startswith("#"):
            headings.append(line.replace("#", "").strip())

    return headings


# main loader
def load_documents() -> List[Dict]:
    documents = []

    base_path = Path(DOCUMENTS_PATH)

    if not base_path.exists():
        logger.error(f"[DOC LOADER] Path not found: {DOCUMENTS_PATH}")
        return documents

    files = list(base_path.glob("*.md"))

    logger.info(f"[DOC LOADER] Found {len(files)} markdown files")

    for file_path in files:
        try:
            if file_path.name.startswith("."):
                continue

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                logger.warning(f"[DOC LOADER] Empty file skipped: {file_path.name}")
                continue

            normalized_content = normalize_text(content)

            metadata = {
                "source": file_path.name,
                "path": str(file_path.resolve()),
                "document_type": detect_document_type(file_path.name),
                "headings": extract_headings(normalized_content),
                "file_size": os.path.getsize(file_path),
            }

            documents.append({
                "content": normalized_content,
                "metadata": metadata
            })

            logger.info(f"[DOC LOADER] Loaded: {file_path.name}")

        except Exception as e:
            logger.warning(f"[DOC LOADER] Skipped {file_path.name}: {str(e)}")

    logger.info(f"[DOC LOADER] Successfully loaded {len(documents)} documents")

    if not documents:
        logger.warning("[DOC LOADER] No documents loaded")

    return documents