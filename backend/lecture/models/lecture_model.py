#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Модель лекции для промежуточной структуры контента.

Определяет структуру данных для представления лекции с разделами,
страницами и блоками контента перед генерацией SCORM пакета.
"""

from dataclasses import dataclass, field
from typing import Literal, Any, Optional, List, Tuple
from enum import Enum


@dataclass
class DocumentBlock:
    """Блок документа, извлечённый при layout parsing. Минимальная единица — строка (line)."""
    id: str
    type: Literal["TEXT", "IMAGE"]
    page_number: int
    bbox: Tuple[float, float, float, float]  # (x0, y0, x1, y1)
    text: str = ""
    font_size: float = 12.0
    is_bold: bool = False
    image_path: Optional[str] = None


@dataclass
class ParagraphBlock:
    """Абзац — объединённые строки текста после нормализации."""
    id: str
    text: str
    page_number: int
    bbox: Tuple[float, float, float, float]
    font_size: float = 12.0
    is_bold: bool = False
    lines_count: int = 1
    header_level: int = 0  # 0 = не заголовок, 1 = H1, 2 = H2, 3 = H3
    element_type: str = "paragraph"  # header | paragraph | caption (от unstructured)
    is_header: bool = False  # заголовок раздела (после header_normalizer)


@dataclass
class DocumentSection:
    """Раздел документа после section_builder (до слайдов)."""
    id: str
    title: str
    paragraphs: List["ParagraphBlock"] = field(default_factory=list)
    images: List = field(default_factory=list)  # LinkedImage после image_linker
    page_numbers: List[int] = field(default_factory=list)


@dataclass
class LinkedImage:
    """Изображение с привязкой к контексту."""
    image_path: str
    caption: str = ""
    position: int = 0  # порядок вставки
    linked_paragraph_id: Optional[str] = None
    page_number: int = 0
    bbox: Tuple[float, float, float, float] = (0, 0, 0, 0)
    context_paragraph_ids: List[str] = field(default_factory=list)  # абзацы до/после в документе


@dataclass
class Slide:
    """Слайд в новой модели."""
    id: str
    title: str
    text_blocks: List[str] = field(default_factory=list)
    images: List[LinkedImage] = field(default_factory=list)
    source_pages: List[int] = field(default_factory=list)
    paragraph_ids: List[str] = field(default_factory=list)  # для привязки изображений


@dataclass
class Section:
    """Раздел лекции (новая модель)."""
    id: str
    title: str
    slides: List[Slide] = field(default_factory=list)
    order: int = 0


class ContentBlockType(str, Enum):
    """Типы блоков контента"""
    TEXT = "text"
    IMAGE = "image"
    LIST = "list"
    TABLE = "table"


@dataclass
class ContentBlock:
    """Базовый класс для блока контента"""
    type: str
    content: Any
    params: dict = field(default_factory=dict)
    
    def __post_init__(self):
        """Валидация типа блока"""
        valid_types = [ContentBlockType.TEXT, ContentBlockType.IMAGE, 
                      ContentBlockType.LIST, ContentBlockType.TABLE]
        if self.type not in [t.value for t in valid_types]:
            raise ValueError(f"Invalid content block type: {self.type}")


@dataclass
class TextBlock(ContentBlock):
    """Блок текстового контента"""
    def __init__(self, content: str = "", params: Optional[dict] = None):
        if params is None:
            params = {
                "font_size": None,
                "font_family": None,
                "alignment": "left",
                "bold": False,
                "italic": False,
            }
        super().__init__(
            type=ContentBlockType.TEXT.value,
            content=content,
            params=params
        )


@dataclass
class ImageBlock(ContentBlock):
    """Блок изображения"""
    def __init__(self, content: str = "", params: Optional[dict] = None):
        if params is None:
            params = {
                "alt": "",
                "width": None,
                "height": None,
                "caption": "",
            }
        super().__init__(
            type=ContentBlockType.IMAGE.value,
            content=content,  # Путь к файлу изображения или base64
            params=params
        )


@dataclass
class ListBlock(ContentBlock):
    """Блок списка"""
    def __init__(self, content: Optional[List[str]] = None, params: Optional[dict] = None):
        if content is None:
            content = []
        if params is None:
            params = {
                "ordered": False,  # True для нумерованного списка
                "style": "disc",  # Стиль маркера для ненумерованного списка
            }
        super().__init__(
            type=ContentBlockType.LIST.value,
            content=content,  # Список элементов
            params=params
        )


@dataclass
class TableBlock(ContentBlock):
    """Блок таблицы"""
    def __init__(self, content: Optional[List[List[str]]] = None, params: Optional[dict] = None):
        if content is None:
            content = []
        if params is None:
            params = {
                "headers": [],  # Заголовки столбцов
                "has_header_row": False,
                "alignment": "left",
            }
        super().__init__(
            type=ContentBlockType.TABLE.value,
            content=content,  # Двумерный список (строки → ячейки)
            params=params
        )


@dataclass
class LecturePage:
    """Страница лекции"""
    id: str
    title: str
    content_blocks: List[ContentBlock] = field(default_factory=list)
    order: int = 0  # Порядок страницы в разделе
    
    def add_block(self, block: ContentBlock):
        """Добавить блок контента на страницу"""
        self.content_blocks.append(block)
    
    def get_blocks_by_type(self, block_type: str) -> List[ContentBlock]:
        """Получить все блоки определенного типа"""
        return [block for block in self.content_blocks if block.type == block_type]


@dataclass
class LectureSection:
    """Раздел лекции"""
    id: str
    title: str
    pages: List[LecturePage] = field(default_factory=list)
    order: int = 0  # Порядок раздела в лекции
    description: Optional[str] = None
    
    def add_page(self, page: LecturePage):
        """Добавить страницу в раздел"""
        self.pages.append(page)
    
    def get_page_by_id(self, page_id: str) -> Optional[LecturePage]:
        """Найти страницу по ID"""
        for page in self.pages:
            if page.id == page_id:
                return page
        return None
    
    def get_total_pages(self) -> int:
        """Получить общее количество страниц в разделе"""
        return len(self.pages)


@dataclass
class Lecture:
    """Модель лекции"""
    title: str
    description: str = ""
    language: str = "ru"
    sections: List[LectureSection] = field(default_factory=list)
    metadata: dict = field(default_factory=lambda: {
        "author": "",
        "created_at": "",
        "version": "1.0",
        "keywords": [],  # Ключевые слова
    })
    
    def add_section(self, section: LectureSection):
        """Добавить раздел в лекцию"""
        self.sections.append(section)
    
    def get_section_by_id(self, section_id: str) -> Optional[LectureSection]:
        """Найти раздел по ID"""
        for section in self.sections:
            if section.id == section_id:
                return section
        return None
    
    def get_total_pages(self) -> int:
        """Получить общее количество страниц во всех разделах"""
        return sum(section.get_total_pages() for section in self.sections)
    
    def get_all_pages(self) -> List[LecturePage]:
        """Получить все страницы из всех разделов"""
        pages = []
        for section in self.sections:
            pages.extend(section.pages)
        return pages
    
    def to_dict(self) -> dict:
        """Преобразовать лекцию в словарь для сериализации"""
        return {
            "title": self.title,
            "description": self.description,
            "language": self.language,
            "sections": [
                {
                    "id": section.id,
                    "title": section.title,
                    "order": section.order,
                    "description": section.description,
                    "pages": [
                        {
                            "id": page.id,
                            "title": page.title,
                            "order": page.order,
                            "content_blocks": [
                                {
                                    "type": block.type,
                                    "content": block.content,
                                    "params": block.params,
                                }
                                for block in page.content_blocks
                            ]
                        }
                        for page in section.pages
                    ]
                }
                for section in self.sections
            ],
            "metadata": self.metadata,
        }

