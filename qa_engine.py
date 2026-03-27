import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from SPARQLWrapper import JSON, SPARQLWrapper
from unidecode import unidecode

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "mapping.json"

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    CONFIG = json.load(f)

PREFIX = f"""
PREFIX legal: <{CONFIG['namespace']}>
PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
"""

FUSEKI_QUERY = CONFIG["fuseki"]["default_query_endpoint"]
FUSEKI_INF_QUERY = CONFIG["fuseki"]["inference_query_endpoint"]
INTENT_REL_MAP = CONFIG["intent_relations"]


def normalize_text(text: str) -> str:
    text = unidecode(text or "")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def detect_intent(question: str) -> str:
    q = normalize_text(question)
    if any(p in q for p in ["phat bao nhieu", "muc phat", "bi phat bao nhieu"]):
        return "ASK_PENALTY"
    if re.search(r"dieu\s+\d+", q) and any(p in q for p in ["noi gi", "noi dung", "quy dinh gi"]):
        return "ASK_ARTICLE_CONTENT"
    if any(p in q for p in ["la gi", "la nhu the nao", "duoc hieu nhu the nao", "dinh nghia la gi"]):
        return "ASK_DEFINITION"
    if any(p in q for p in ["bao gom gi", "bao gom nhung gi", "gom nhung gi"]):
        return "ASK_INCLUDES"
    if any(p in q for p in ["bi cam khong", "co bi cam khong", "nghiem cam gi", "hanh vi nao bi cam", "cam nhung gi"]):
        return "ASK_PROHIBITION"
    if any(p in q for p in ["duoc phep khong", "co duoc khong", "co duoc phep khong"]):
        return "ASK_PERMISSION"
    if any(p in q for p in ["yeu cau gi", "phai lam gi", "can gi", "can phai gi"]):
        return "ASK_REQUIREMENT"
    if any(p in q for p in ["co trach nhiem gi", "trach nhiem gi", "thuc hien gi", "to chuc thuc hien gi"]):
        return "ASK_RESPONSIBILITY"
    if any(p in q for p in ["ap dung cho ai", "ap dung cho doi tuong nao", "doi tuong ap dung la ai"]):
        return "ASK_APPLIES_TO"
    if any(p in q for p in ["muc dich la gi", "de lam gi", "nham muc dich gi"]):
        return "ASK_PURPOSE"
    if any(p in q for p in ["ket noi voi gi", "ket noi nhu the nao"]):
        return "ASK_CONNECTION"
    if any(p in q for p in ["su dung de lam gi", "duoc su dung de lam gi"]):
        return "ASK_USAGE"
    if any(p in q for p in ["dieu nao", "thuoc dieu nao", "quy dinh o dau", "can cu phap ly nao"]):
        return "ASK_LEGAL_BASIS"
    if any(p in q for p in ["co vi pham khong", "co phai vi pham khong"]):
        return "ASK_VIOLATION_CHECK"
    if any(p in q for p in ["nhung hanh vi nao", "cac hanh vi nao", "danh sach hanh vi"]):
        return "ASK_LIST_VIOLATIONS"
    if any(p in q for p in ["tai pham", "xu nang hon", "nang hon khong", "nghiem trong khong"]):
        return "ASK_AGGRAVATION"
    return "UNKNOWN"


def _build_index(group_name: str):
    index = []
    for key, info in CONFIG.get(group_name, {}).items():
        for phrase in set([key] + info.get("synonyms", [])):
            index.append((normalize_text(phrase), key, info))
    index.sort(key=lambda x: len(x[0]), reverse=True)
    return index


ENTITY_INDEX = _build_index("entities")
SUBJECT_INDEX = _build_index("subjects")
CONDITION_INDEX = _build_index("conditions")


def _first_match(index_data, normalized_question: str):
    for phrase, key, info in index_data:
        if phrase and phrase in normalized_question:
            return {
                "key": key,
                "label": info.get("label", key),
                "hints": info.get("hints", []),
                "domain": info.get("domain"),
            }
    return None


def extract_entities(question: str) -> dict[str, Any]:
    q = normalize_text(question)
    entities: dict[str, Any] = {"question_norm": q}

    entity_match = _first_match(ENTITY_INDEX, q)
    if entity_match:
        entities["entity_key"] = entity_match["key"]
        entities["entity_label"] = entity_match["label"]
        entities["entity_hints"] = entity_match.get("hints", [])
        entities["domain"] = entity_match.get("domain")

    subject_match = _first_match(SUBJECT_INDEX, q)
    if subject_match:
        entities["subject_key"] = subject_match["key"]
        entities["subject_label"] = subject_match["label"]

    condition_match = _first_match(CONDITION_INDEX, q)
    if condition_match:
        entities["condition_key"] = condition_match["key"]
        entities["condition_label"] = condition_match["label"]

    law_match = re.search(r"\b(luat lao dong|luat duong bo|luat trat tu an toan giao thong duong bo)\b", q)
    if law_match:
        law_map = {
            "luat lao dong": "LLD",
            "luat duong bo": "LDB",
            "luat trat tu an toan giao thong duong bo": "TTATGTDB",
        }
        entities["law"] = law_map[law_match.group(1)]

    article = re.search(r"dieu\s+(\d+)", q)
    if article:
        entities["article"] = article.group(1)
    clause = re.search(r"khoan\s+(\d+)", q)
    if clause:
        entities["clause"] = clause.group(1)
    point = re.search(r"diem\s+([a-z])", q)
    if point:
        entities["point"] = point.group(1)
    return entities


def analyze_question(question: str) -> dict[str, Any]:
    return {
        "question": question,
        "intent": detect_intent(question),
        "entities": extract_entities(question),
    }


def escape_sparql_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _entity_filter_block(entities: dict[str, Any], entity_var: str = "?entity", label_var: str = "?entityLabel") -> str:
    label = entities.get("entity_label")
    hints = entities.get("entity_hints", [])
    hint_conditions = [f'STRENDS(STR({entity_var}), "#{escape_sparql_string(h)}")' for h in hints]
    label_conditions: list[str] = []
    if label:
        esc = escape_sparql_string(label)
        label_conditions.append(f'LCASE(STR({label_var})) = LCASE("{esc}")')
        label_conditions.append(f'STRSTARTS(LCASE(STR({label_var})), LCASE("{esc}"))')
        label_conditions.append(f'CONTAINS(LCASE(STR({label_var})), LCASE("{esc}"))')
    conditions = hint_conditions + (label_conditions[:2] if hint_conditions else label_conditions)
    return "FILTER(" + " || ".join(conditions) + ")" if conditions else ""


def generate_sparql(intent: str, entities: dict[str, Any]) -> str:
    if intent == "ASK_PENALTY":
        return ""

    if intent == "ASK_ARTICLE_CONTENT":
        article = entities.get("article")
        if not article:
            return ""
        clause = entities.get("clause")
        point = entities.get("point")
        clause_filter = f'FILTER(?clauseNumber = "{escape_sparql_string(clause)}")' if clause else ""
        point_filter = f'FILTER(LCASE(STR(?pointNumber)) = "{escape_sparql_string(point.lower())}")' if point else ""
        return PREFIX + f"""
SELECT DISTINCT ?articleNumber ?articleLabel ?lawCode ?entityLabel ?rawS ?rawO ?clauseNumber ?pointNumber
WHERE {{
    ?article rdf:type legal:Article ;
             legal:articleNumber ?articleNumber .
    FILTER(?articleNumber = \"{escape_sparql_string(article)}\")

    OPTIONAL {{ ?article legal:label ?articleLabel . }}
    OPTIONAL {{ ?article legal:rawSubject ?rawS . }}
    OPTIONAL {{ ?article legal:rawObject ?rawO . }}
    OPTIONAL {{ ?article legal:clauseNumber ?clauseNumber . }}
    OPTIONAL {{ ?article legal:pointNumber ?pointNumber . }}
    OPTIONAL {{ ?law legal:hasArticle ?article ; legal:lawCode ?lawCode . }}
    OPTIONAL {{
        ?article legal:mentionsEntity ?entity .
        ?entity legal:label ?entityLabel .
    }}

    {clause_filter}
    {point_filter}
}}
LIMIT 100
"""

    if intent == "ASK_LEGAL_BASIS":
        if not entities.get("entity_label"):
            return ""
        entity_filter = _entity_filter_block(entities, entity_var="?entity", label_var="?entityLabel")
        return PREFIX + f"""
SELECT DISTINCT ?article ?articleNumber ?lawCode ?entityLabel
WHERE {{
    ?article rdf:type legal:Article ;
             legal:articleNumber ?articleNumber ;
             legal:mentionsEntity ?entity .
    ?entity legal:label ?entityLabel .
    OPTIONAL {{ ?law legal:hasArticle ?article ; legal:lawCode ?lawCode . }}
    {entity_filter}
}}
ORDER BY ?lawCode ?articleNumber
LIMIT 50
"""

    rels = INTENT_REL_MAP.get(intent, [])
    if intent in {"ASK_DEFINITION", "ASK_INCLUDES", "ASK_PROHIBITION", "ASK_PERMISSION", "ASK_REQUIREMENT", "ASK_RESPONSIBILITY", "ASK_APPLIES_TO", "ASK_PURPOSE", "ASK_CONNECTION", "ASK_USAGE"}:
        if not entities.get("entity_label"):
            return ""
        relation_filters = " || ".join([f'STRENDS(STR(?rel), "#{r}")' for r in rels])
        entity_filter = _entity_filter_block(entities, entity_var="?entity", label_var="?entityLabel")
        return PREFIX + f"""
SELECT DISTINCT ?entity ?entityLabel ?subjectLabel ?relationName ?objectLabel ?lawCode ?articleNumber
WHERE {{
    ?entity legal:label ?entityLabel .
    {entity_filter}

    ?subject ?rel ?object .
    ?subject legal:label ?subjectLabel .
    ?object legal:label ?objectLabel .
    FILTER(?subject = ?entity)
    FILTER({relation_filters})

    BIND(REPLACE(STR(?rel), ".*#", "") AS ?relationName)

    OPTIONAL {{
        ?article rdf:type legal:Article ;
                 legal:mentionsEntity ?subject ;
                 legal:articleNumber ?articleNumber .
        ?law legal:hasArticle ?article ;
             legal:lawCode ?lawCode .
    }}
}}
LIMIT 100
"""

    if intent == "ASK_VIOLATION_CHECK":
        if not entities.get("entity_label"):
            return ""
        entity_filter = _entity_filter_block(entities, entity_var="?entity", label_var="?entityLabel")
        return PREFIX + f"""
SELECT DISTINCT ?entity ?entityLabel
WHERE {{
    ?entity rdf:type legal:HanhViViPham ;
            legal:label ?entityLabel .
    {entity_filter}
}}
LIMIT 20
"""

    if intent == "ASK_AGGRAVATION":
        if not entities.get("entity_label"):
            return ""
        entity_filter = _entity_filter_block(entities, entity_var="?entity", label_var="?entityLabel")
        return PREFIX + f"""
SELECT DISTINCT ?entity ?entityLabel
WHERE {{
    ?entity rdf:type legal:SevereViolation ;
            legal:label ?entityLabel .
    {entity_filter}
}}
LIMIT 20
"""

    if intent == "ASK_LIST_VIOLATIONS":
        return PREFIX + """
SELECT DISTINCT ?entity ?entityLabel
WHERE {
    ?entity rdf:type legal:HanhViViPham ;
            legal:label ?entityLabel .
}
ORDER BY ?entityLabel
LIMIT 100
"""

    return ""


def choose_endpoint(intent: str) -> str:
    if intent in {"ASK_VIOLATION_CHECK", "ASK_AGGRAVATION", "ASK_LIST_VIOLATIONS"}:
        return FUSEKI_INF_QUERY
    return FUSEKI_QUERY


def run_sparql(query: str, endpoint: str) -> list[dict[str, str]]:
    sparql = SPARQLWrapper(endpoint)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    data = sparql.query().convert()
    bindings = data.get("results", {}).get("bindings", [])
    return [{k: v.get("value") for k, v in item.items()} for item in bindings]


def _vals(results: list[dict[str, str]], key: str) -> list[str]:
    out: list[str] = []
    for row in results:
        val = row.get(key)
        if val and val not in out:
            out.append(val)
    return out


def format_answer(intent: str, results: list[dict[str, str]], entities: dict[str, Any] | None = None) -> str:
    entities = entities or {}

    if intent == "ASK_PENALTY":
        return "Ontology hiện tại chưa mô hình hóa mức phạt cụ thể, nên hệ thống chưa trả lời chính xác câu hỏi về số tiền phạt."

    if intent == "ASK_ARTICLE_CONTENT":
        if not results:
            article = entities.get("article", "")
            return f"Không tìm thấy nội dung cho Điều {article}."
        labels = _vals(results, "entityLabel")
        raws = _vals(results, "rawO")
        lines = [f"Điều {entities.get('article', '')} có liên quan đến:"]
        if labels:
            lines.append("- Thực thể được nhắc tới: " + ", ".join(labels[:10]))
        if raws:
            lines.append("- Nội dung liên quan: " + ", ".join(raws[:10]))
        return "\n".join(lines)

    if not results:
        fallback = {
            "ASK_DEFINITION": "Không tìm thấy định nghĩa phù hợp.",
            "ASK_INCLUDES": "Không tìm thấy nội dung bao gồm phù hợp.",
            "ASK_PROHIBITION": "Không tìm thấy nội dung cấm phù hợp.",
            "ASK_PERMISSION": "Không tìm thấy nội dung cho phép phù hợp.",
            "ASK_REQUIREMENT": "Không tìm thấy yêu cầu phù hợp.",
            "ASK_RESPONSIBILITY": "Không tìm thấy thông tin về trách nhiệm phù hợp.",
            "ASK_APPLIES_TO": "Không tìm thấy đối tượng áp dụng phù hợp.",
            "ASK_PURPOSE": "Không tìm thấy mục đích phù hợp.",
            "ASK_CONNECTION": "Không tìm thấy nội dung kết nối phù hợp.",
            "ASK_USAGE": "Không tìm thấy nội dung sử dụng phù hợp.",
            "ASK_LEGAL_BASIS": "Không tìm thấy căn cứ pháp lý phù hợp.",
            "ASK_VIOLATION_CHECK": "Chưa tìm thấy bằng chứng trong ontology suy luận rằng đây là hành vi vi phạm.",
            "ASK_AGGRAVATION": "Chưa tìm thấy bằng chứng trong ontology suy luận rằng đây là vi phạm nghiêm trọng.",
            "ASK_LIST_VIOLATIONS": "Không tìm thấy danh sách hành vi vi phạm.",
        }
        return fallback.get(intent, "Không tìm thấy thông tin phù hợp.")

    if intent == "ASK_LEGAL_BASIS":
        pairs: list[str] = []
        for row in results:
            law = (row.get("lawCode") or "").strip()
            article = (row.get("articleNumber") or "").strip()
            if not article:
                continue
            pair = f"{law} - Điều {article}" if law else f"Điều {article}"
            if pair not in pairs:
                pairs.append(pair)
        return "Các căn cứ pháp lý liên quan: " + "; ".join(pairs[:10]) + "." if pairs else "Không tìm thấy căn cứ pháp lý phù hợp."

    if intent == "ASK_VIOLATION_CHECK":
        label = results[0].get("entityLabel") or entities.get("entity_label", "thực thể này")
        return f"Có. Hệ thống suy luận cho thấy '{label}' được phân loại là hành vi vi phạm."

    if intent == "ASK_AGGRAVATION":
        label = results[0].get("entityLabel") or entities.get("entity_label", "thực thể này")
        return f"Có. Hệ thống suy luận cho thấy '{label}' được phân loại là vi phạm nghiêm trọng."

    if intent == "ASK_LIST_VIOLATIONS":
        labels = _vals(results, "entityLabel")
        return "Một số hành vi vi phạm: " + ", ".join(labels[:20]) + (", ..." if len(labels) > 20 else ".") if labels else "Không tìm thấy danh sách hành vi vi phạm."

    grouped: dict[str, list[str]] = defaultdict(list)
    for row in results:
        subj = row.get("subjectLabel") or entities.get("entity_label", "thực thể")
        obj = row.get("objectLabel")
        if obj and obj not in grouped[subj]:
            grouped[subj].append(obj)
    if grouped:
        return "\n".join(f"{subj}: " + "; ".join(objs[:10]) for subj, objs in list(grouped.items())[:5])

    return "Đã tìm thấy dữ liệu nhưng chưa định dạng được câu trả lời phù hợp."


def process_question(question: str) -> dict[str, Any]:
    analysis = analyze_question(question)
    intent = analysis["intent"]
    entities = analysis["entities"]
    sparql = generate_sparql(intent, entities)
    endpoint = choose_endpoint(intent)
    results: list[dict[str, str]] = []

    if sparql:
        try:
            results = run_sparql(sparql, endpoint)
        except Exception as exc:
            return {
                "question": question,
                "intent": intent,
                "entities": entities,
                "endpoint": endpoint,
                "sparql": sparql,
                "results": [],
                "answer": f"Lỗi khi truy vấn Fuseki: {exc}",
            }

    return {
        "question": question,
        "intent": intent,
        "entities": entities,
        "endpoint": endpoint,
        "sparql": sparql,
        "results": results,
        "answer": format_answer(intent, results, entities),
    }
