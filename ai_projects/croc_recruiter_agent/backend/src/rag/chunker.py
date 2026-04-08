from __future__ import annotations
from typing import List, Dict
import re
from src.utils.logger import get_logger

logger = get_logger(__name__)


# config
MAX_TOKENS = 250
MIN_TOKENS = 30
OVERLAP_RATIO = 0.2


# token estimation
def estimate_tokens(text: str) -> int:
    return int(len(text.split()) * 1.3)


# normalization
def normalize_chunk_text(text: str) -> str:
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


# split headings
def split_by_headings(content: str) -> List[Dict]:
    sections = []
    current_section = {"title": "General", "content": []}

    for line in content.splitlines():
        if line.strip().startswith("#"):
            if current_section["content"]:
                sections.append({
                    "title": current_section["title"],
                    "content": "\n".join(current_section["content"]).strip()
                })

            current_section = {
                "title": line.replace("#", "").strip(),
                "content": []
            }
        else:
            current_section["content"].append(line)

    if current_section["content"]:
        sections.append({
            "title": current_section["title"],
            "content": "\n".join(current_section["content"]).strip()
        })

    return sections


# split text
def split_text(text: str) -> List[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    if len(paragraphs) <= 1:
        paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    return paragraphs


# build chunks
def build_chunks(paragraphs: List[str]) -> List[str]:
    chunks = []
    current_chunk = []
    current_tokens = 0

    for paragraph in paragraphs:
        paragraph_tokens = estimate_tokens(paragraph)

        if current_tokens + paragraph_tokens > MAX_TOKENS:
            if current_chunk:
                chunks.append("\n\n".join(current_chunk))
                current_chunk = []
                current_tokens = 0

        current_chunk.append(paragraph)
        current_tokens += paragraph_tokens

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks


# apply overlap
def apply_overlap(chunks: List[str]) -> List[str]:
    if len(chunks) <= 1:
        return chunks

    overlapped = []

    for i, chunk in enumerate(chunks):
        if i == 0:
            overlapped.append(chunk)
            continue

        prev_chunk = chunks[i - 1]

        prev_words = prev_chunk.split()
        overlap_size = max(1, int(len(prev_words) * OVERLAP_RATIO))

        overlap_text = " ".join(prev_words[-overlap_size:])

        new_chunk = overlap_text + "\n\n" + chunk

        overlapped.append(new_chunk)

    return overlapped


# main function
def chunk_documents(documents: List[Dict]) -> List[Dict]:
    all_chunks = []

    for doc in documents:
        content = doc.get("content", "")
        metadata = doc.get("metadata", {}) or {}

        source = metadata.get("source", "unknown")

        # unique chunk id per document
        doc_chunk_counter = 0

        sections = split_by_headings(content)

        for section in sections:
            section_title = section["title"]
            section_content = section["content"]

            paragraphs = split_text(section_content)
            base_chunks = build_chunks(paragraphs)
            final_chunks = apply_overlap(base_chunks)

            for chunk in final_chunks:
                chunk = normalize_chunk_text(chunk)
                tokens = estimate_tokens(chunk)

                if tokens < MIN_TOKENS:
                    logger.debug(f"[CHUNKER] Small chunk kept ({tokens} tokens)")

                # unique chunk id per document
                chunk_id = doc_chunk_counter
                doc_chunk_counter += 1

                enriched_content = (
                    f"[{metadata.get('document_type', 'general').upper()} | {section_title}]\n\n{chunk}"
                )

                all_chunks.append({
                    "content": enriched_content,
                    "metadata": {
                        **metadata,
                        "source": source,
                        "section": section_title,
                        "chunk_id": chunk_id,
                        "tokens": tokens
                    }
                })

    logger.info(f"[CHUNKER] Generated {len(all_chunks)} chunks")

    return all_chunks