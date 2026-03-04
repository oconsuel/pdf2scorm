#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Экспорт промежуточных результатов пайплайна в CSV."""

import csv
from pathlib import Path
from typing import List, Optional

from .models.lecture_model import (
    DocumentBlock,
    ParagraphBlock,
    LinkedImage,
    Section,
    Lecture,
)


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_csv(filepath: Path, rows: List[dict], fieldnames: List[str]) -> None:
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def export_stage_1_layout_parsing(blocks: List[DocumentBlock], output_dir: Path) -> None:
    rows = []
    for b in blocks:
        rows.append({
            "id": b.id,
            "type": b.type,
            "page_number": b.page_number,
            "bbox": str(b.bbox),
            "text": (b.text or "")[:500],
            "font_size": b.font_size,
            "is_bold": b.is_bold,
            "image_path": b.image_path or "",
        })
    _write_csv(
        output_dir / "01_layout_parsing.csv",
        rows,
        ["id", "type", "page_number", "bbox", "text", "font_size", "is_bold", "image_path"],
    )


def export_stage_2_block_normalization(paragraphs: List[ParagraphBlock], output_dir: Path) -> None:
    rows = []
    for p in paragraphs:
        rows.append({
            "id": p.id,
            "text": (p.text or "")[:1000],
            "page_number": p.page_number,
            "bbox": str(p.bbox),
            "font_size": p.font_size,
            "is_bold": p.is_bold,
            "lines_count": p.lines_count,
            "header_level": getattr(p, "header_level", 0),
        })
    _write_csv(
        output_dir / "02_block_normalization.csv",
        rows,
        ["id", "text", "page_number", "bbox", "font_size", "is_bold", "lines_count", "header_level"],
    )


def export_stage_3_header_detection(paragraphs: List[ParagraphBlock], output_dir: Path) -> None:
    rows = []
    for p in paragraphs:
        rows.append({
            "id": p.id,
            "text": (p.text or "")[:1000],
            "page_number": p.page_number,
            "font_size": p.font_size,
            "header_level": getattr(p, "header_level", 0),
            "header_label": ["", "H1", "H2", "H3"][getattr(p, "header_level", 0)] if getattr(p, "header_level", 0) <= 3 else "",
        })
    _write_csv(
        output_dir / "03_header_detection.csv",
        rows,
        ["id", "text", "page_number", "font_size", "header_level", "header_label"],
    )


def export_stage_4_image_linking(
    paragraphs: List[ParagraphBlock],
    linked_images: List[LinkedImage],
    output_dir: Path,
) -> None:
    rows = []
    for p in paragraphs:
        rows.append({
            "row_type": "paragraph",
            "id": p.id,
            "text": (p.text or "")[:500],
            "page_number": p.page_number,
            "header_level": getattr(p, "header_level", 0),
            "image_path": "",
            "caption": "",
            "position": "",
            "linked_paragraph_id": "",
            "context_paragraph_ids": "",
        })
    for img in linked_images:
        rows.append({
            "row_type": "image",
            "id": "",
            "text": "",
            "page_number": img.page_number,
            "header_level": "",
            "image_path": img.image_path,
            "caption": (img.caption or "")[:200],
            "position": img.position,
            "linked_paragraph_id": img.linked_paragraph_id or "",
            "context_paragraph_ids": ";".join(img.context_paragraph_ids) if img.context_paragraph_ids else "",
        })
    _write_csv(
        output_dir / "04_image_linking.csv",
        rows,
        ["row_type", "id", "text", "page_number", "header_level", "image_path", "caption", "position", "linked_paragraph_id", "context_paragraph_ids"],
    )


def export_stage_5_slide_builder(sections: List[Section], output_dir: Path) -> None:
    rows = []
    for sec in sections:
        for idx, slide in enumerate(sec.slides):
            text_preview = " | ".join((t[:80] + "…" if len(t) > 80 else t for t in slide.text_blocks[:3]))
            rows.append({
                "section_order": sec.order,
                "section_id": sec.id,
                "section_title": sec.title[:100] if sec.title else "",
                "slide_order": idx + 1,
                "slide_id": slide.id,
                "slide_title": (slide.title or "")[:100],
                "text_blocks_count": len(slide.text_blocks),
                "images_count": len(slide.images),
                "text_preview": text_preview[:200],
                "paragraph_ids": ";".join(slide.paragraph_ids[:5]),
            })
    _write_csv(
        output_dir / "05_slide_builder.csv",
        rows,
        ["section_order", "section_id", "section_title", "slide_order", "slide_id", "slide_title", "text_blocks_count", "images_count", "text_preview", "paragraph_ids"],
    )


def export_stage_6_lecture(lecture: Lecture, output_dir: Path) -> None:
    rows = []
    for sec in lecture.sections:
        for page in sec.pages:
            content_preview = []
            for b in page.content_blocks[:5]:
                if b.type == "text":
                    content_preview.append((b.content or "")[:60] + ("…" if len(str(b.content or "")) > 60 else ""))
                else:
                    content_preview.append(f"[image: {str(b.content)[:50]}]")
            rows.append({
                "section_order": sec.order,
                "section_id": sec.id,
                "section_title": sec.title[:80] if sec.title else "",
                "page_order": page.order,
                "page_id": page.id,
                "page_title": (page.title or "")[:80],
                "content_blocks_count": len(page.content_blocks),
                "content_preview": " | ".join(content_preview)[:200],
            })
    _write_csv(
        output_dir / "06_lecture.csv",
        rows,
        ["section_order", "section_id", "section_title", "page_order", "page_id", "page_title", "content_blocks_count", "content_preview"],
    )
