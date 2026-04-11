import json
import re
import unicodedata

INPUT_JSON = r"./output/knowledge_triples.json"
OUTPUT_TTL = r"legal_triples.ttl"

BASE = "http://example.org/legal-qa#"

RELATIONS = {
    "quyDinhVe",
    "dinhNghia",
    "baoGom",
    "apDungCho",
    "cam",
    "choPhep",
    "yeuCau",
    "baoDam",
    "mucDich",
    "thucHien",
    "suDung",
    "ketNoi",
}

ENTITY_ALIAS = {
    "đường bộ": "đường bộ",
    "các đường bộ": "đường bộ",
    "bến xe": "bến xe",
    "các bến xe": "bến xe",
    "biển quảng cáo": "biển quảng cáo",
    "các biển quảng cáo": "biển quảng cáo",
    "trạm thu phí": "trạm thu phí",
    "các trạm thu phí": "trạm thu phí",
    "cầu đường bộ": "cầu đường bộ",
    "các cầu đường bộ": "cầu đường bộ",
    "cống đường bộ": "cống đường bộ",
    "các cống đường bộ": "cống đường bộ",
    "hầm đường bộ": "hầm đường bộ",
    "các hầm đường bộ": "hầm đường bộ",
    "bãi đỗ xe": "bãi đỗ xe",
    "các bãi đỗ xe": "bãi đỗ xe",
    "nhà xe": "nhà xe",
    "các nhà xe": "nhà xe",
    "xe đạp": "xe đạp",
    "các xe đạp": "xe đạp",
    "xe máy chuyên dùng": "xe máy chuyên dùng",
    "các xe máy chuyên dùng": "xe máy chuyên dùng",
    "phương tiện giao thông đường bộ": "phương tiện giao thông đường bộ",
    "các phương tiện giao thông đường bộ": "phương tiện giao thông đường bộ",
    "công trình đường bộ": "công trình đường bộ",
    "các công trình đường bộ": "công trình đường bộ",
    "công trình phụ trợ": "công trình phụ trợ",
    "các công trình phụ trợ": "công trình phụ trợ",
    "người tham gia giao thông đường bộ": "người tham gia giao thông đường bộ",
    "các người tham gia giao thông đường bộ": "người tham gia giao thông đường bộ",
    "người điều khiển phương tiện tham gia giao thông đường bộ": "người điều khiển phương tiện tham gia giao thông đường bộ",
    "các người điều khiển phương tiện tham gia giao thông đường bộ": "người điều khiển phương tiện tham gia giao thông đường bộ",
    "công dân": "công dân",
    "các công dân": "công dân",
    "người lao động": "người lao động",
    "các người lao động": "người lao động",
}

LEADING_PATTERNS = [
    r"^các\s+loại\s+",
    r"^các\s+hình\s+thức\s+",
    r"^các\s+loại\s+hình\s+",
    r"^các\s+",
    r"^những\s+",
    r"^mọi\s+",
]

def strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D")

def normalize_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def clean_text(text: str) -> str:
    if text is None:
        return ""
    text = str(text).strip()
    text = re.sub(r"[“”\"'`]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

def normalize_entity(text: str) -> str:
    """
    Chuẩn hóa entity trước khi tạo URI:
    - bỏ khác biệt hoa/thường
    - bỏ từ dẫn như 'các', 'những', 'mọi'
    - map alias tay cho các thực thể phổ biến
    """
    text = clean_text(text)
    if not text:
        return "Unknown"

    lowered = text.lower()
    lowered = normalize_spaces(lowered)

    for pattern in LEADING_PATTERNS:
        lowered = re.sub(pattern, "", lowered)

    lowered = normalize_spaces(lowered)

    lowered = re.sub(r"[;:,.\-–—]+$", "", lowered)
    lowered = normalize_spaces(lowered)

    if lowered in ENTITY_ALIAS:
        lowered = ENTITY_ALIAS[lowered]

    return lowered if lowered else "unknown"

def slugify(text: str) -> str:
    if text is None:
        return "Unknown"

    text = strip_accents(str(text)).strip()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    if not text:
        return "Unknown"

    words = text.split()
    return "".join(w[:1].upper() + w[1:] for w in words)

def escape_literal(text: str) -> str:
    if text is None:
        return ""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
    )

def main():
    with open(INPUT_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    lines = []
    emitted = set()
    entity_labels = {}  

    def emit(line: str):
        if line not in emitted:
            emitted.add(line)
            lines.append(line)

    lines.append(f"@prefix legal: <{BASE}> .")
    lines.append("@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .")
    lines.append("@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .")
    lines.append("@prefix owl: <http://www.w3.org/2002/07/owl#> .")
    lines.append("@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .")
    lines.append("")

    for row in data:
        law = str(row.get("law", "")).strip()
        chapter = str(row.get("chapter", "")).strip()
        article = str(row.get("article", "")).strip()
        subject_raw = str(row.get("subject", "")).strip()
        relation = str(row.get("relation", "")).strip()
        object_raw = str(row.get("object", "")).strip()

        if not law or not chapter or not article or not subject_raw or not relation or not object_raw:
            continue
        if relation not in RELATIONS:
            continue

        subject_norm = normalize_entity(subject_raw)
        object_norm = normalize_entity(object_raw)

        law_uri = f"legal:{slugify(law)}"
        chap_uri = f"legal:{slugify(law)}_Chap_{slugify(chapter)}"
        art_uri = f"legal:{slugify(law)}_Chap_{slugify(chapter)}_Art_{slugify(article)}"

        subj_uri = f"legal:{slugify(subject_norm)}"
        obj_uri = f"legal:{slugify(object_norm)}"

        # Law
        emit(f"{law_uri} rdf:type legal:Law .")
        emit(f'{law_uri} legal:lawCode "{escape_literal(law)}"^^xsd:string .')

        # Chapter
        emit(f"{chap_uri} rdf:type legal:Chapter .")
        emit(f'{chap_uri} legal:chapterCode "{escape_literal(chapter)}"^^xsd:string .')
        emit(f"{law_uri} legal:hasChapter {chap_uri} .")

        # Article
        emit(f"{art_uri} rdf:type legal:Article .")
        emit(f'{art_uri} legal:articleNumber "{escape_literal(article)}"^^xsd:string .')
        emit(f"{chap_uri} legal:hasArticle {art_uri} .")

        # Subject entity
        emit(f"{subj_uri} rdf:type legal:LegalEntity .")
        if subj_uri not in entity_labels:
            entity_labels[subj_uri] = subject_norm
            emit(f'{subj_uri} legal:label "{escape_literal(subject_norm)}"^^xsd:string .')

        # Object entity
        emit(f"{obj_uri} rdf:type legal:LegalEntity .")
        if obj_uri not in entity_labels:
            entity_labels[obj_uri] = object_norm
            emit(f'{obj_uri} legal:label "{escape_literal(object_norm)}"^^xsd:string .')

        emit(f"{subj_uri} legal:{relation} {obj_uri} .")

        # Liên kết article với entity được nhắc đến
        emit(f"{art_uri} legal:mentionsEntity {subj_uri} .")
        emit(f"{art_uri} legal:mentionsEntity {obj_uri} .")

        emit(f'{art_uri} legal:rawSubject "{escape_literal(subject_raw)}"^^xsd:string .')
        emit(f'{art_uri} legal:rawObject "{escape_literal(object_raw)}"^^xsd:string .')

    with open(OUTPUT_TTL, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Done. Wrote {OUTPUT_TTL}")

if __name__ == "__main__":
    main()