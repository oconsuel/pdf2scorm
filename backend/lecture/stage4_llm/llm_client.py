#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Клиент для OpenAI API (GPT-4o).

- OPENAI_API_KEY из переменной окружения (python-dotenv)
- JSON response mode
- Retry при ошибках
"""

import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from openai import OpenAI

DEFAULT_MODEL = "gpt-4o-mini"
MAX_RETRIES = 3
RETRY_DELAY = 2.0


class LLMClient:
    """Клиент для OpenAI API."""

    def __init__(self, api_key: Optional[str] = None, model: str = DEFAULT_MODEL):
        key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = OpenAI(api_key=key) if key else None
        self.model = model
        self._available = self._client is not None
        if not self._available:
            logging.warning("OPENAI_API_KEY не задан — LLM недоступен, будет использован fallback")

    @property
    def available(self) -> bool:
        """Доступен ли LLM (есть ключ)."""
        return self._available

    def _call(
        self,
        messages: List[Dict[str, str]],
        response_format: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        """
        Вызов API с retry.
        
        Args:
            messages: Список сообщений для Chat API
            response_format: {"type": "json_object"} для JSON-ответа
        
        Returns:
            Текст ответа или None при ошибке
        """
        if not self._client:
            return None
        kwargs = {"model": self.model, "messages": messages}
        if response_format:
            kwargs["response_format"] = response_format

        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.chat.completions.create(**kwargs)
                return response.choices[0].message.content
            except Exception as e:
                logging.warning("OpenAI API attempt %d/%d failed: %s", attempt + 1, MAX_RETRIES, e)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY)
                else:
                    logging.error("OpenAI API failed after %d retries", MAX_RETRIES)
                    return None
        return None

    def generate_slide_structure(
        self,
        document_items: List[Dict[str, Any]],
        language: str = "ru",
    ) -> Optional[Dict[str, Any]]:
        """
        Генерирует структуру слайдов из элементов документа.
        
        Args:
            document_items: [{"idx": 0, "type": "paragraph", "text": "...", "page": 1}, ...]
        
        Returns:
            {"slides": [{"title": "...", "paragraph_indices": [0,1], "image_indices": [2]}]}
            или None при ошибке
        """
        items_json = json.dumps(document_items, ensure_ascii=False, indent=0)
        lang_instruction = "Respond in Russian." if language == "ru" else "Respond in English."
        prompt = f"""You are analyzing a SCIENTIFIC ARTICLE and building a LECTURE structure from it.
The input is a structured document with:
- type "section" — section boundary (title). RESPECT section boundaries: do NOT mix content from different sections on the same slide.
- type "paragraph" — text block
- type "image" — figure/diagram

Your task is to create a lecture slide structure that groups content logically within each section.

Input document:
{items_json}

Rules for each slide:
- Short title (one line)
- 2–4 text points maximum (concise)
- Image optional, only if relevant to the slide content
- Maximum 300–400 characters of text per slide
- Do not repeat PDF page structure; merge related content into fewer slides
- Prefer starting new slides at section boundaries (type "section")
- Never put paragraphs from different sections on the same slide

Create at most 3–4 slides per chunk. Fewer slides is better if content fits.

{lang_instruction}
Return JSON only, no other text. Format:
{{
  "slides": [
    {{
      "title": "Slide title",
      "paragraph_indices": [0, 1],
      "image_indices": [2]
    }}
  ]
}}
paragraph_indices = indices of paragraph items (type "paragraph") to include.
image_indices = indices of image items to include.
Use the "idx" field from each input item. Use paragraph indices (type "paragraph") and image indices (type "image"). Do not use section indices (type "section") in paragraph_indices or image_indices."""

        logging.info("LLM generate_slide_structure: отправлено %d элементов", len(document_items))
        response = self._call(
            [{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        if not response:
            return None
        try:
            result = json.loads(response)
            slides_count = len(result.get("slides", [])) if result else 0
            logging.info("LLM generate_slide_structure: получено %d слайдов", slides_count)
            return result
        except json.JSONDecodeError as e:
            logging.error("LLM returned invalid JSON: %s", e)
            return None
