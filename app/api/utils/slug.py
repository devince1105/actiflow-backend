# app/api/utils/slug.py
import re
from unidecode import unidecode

def generate_slug(name: str) -> str:
    slug = unidecode(name)            # 中文 → 拼音 / 英文
    slug = slug.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug
