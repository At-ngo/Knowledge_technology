import re
from unidecode import unidecode

def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = unidecode(text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text

VIOLATION_DICT = {
    "khong doi mu bao hiem": "KhongDoiMuBaoHiem",
    "vuot den do": "VuotDenDo",
    "di nguoc chieu": "DiNguocChieu",
    "khong co bang lai": "KhongCoBangLai",
    "chay qua toc do": "ChayQuaTocDo",
    "nong do con": "NongDoCon"
}

SUBJECT_DICT = {
    "xe may": "XeMay",
    "o to": "OTo",
    "xe oto": "OTo"
}

CONDITION_DICT = {
    "tai pham": "TaiPham",
    "nong do con cao": "NongDoConCao"
}

def extract_entities(question: str) -> dict:
    q = normalize_text(question)
    entities = {}

    for phrase, code in VIOLATION_DICT.items():
        if phrase in q:
            entities["violation"] = code
            break

    for phrase, code in SUBJECT_DICT.items():
        if phrase in q:
            entities["subject"] = code
            break

    for phrase, code in CONDITION_DICT.items():
        if phrase in q:
            entities["condition"] = code
            break

    dieu = re.search(r"dieu\s+(\d+)", q)
    if dieu:
        entities["article"] = dieu.group(1)

    khoan = re.search(r"khoan\s+(\d+)", q)
    if khoan:
        entities["clause"] = khoan.group(1)

    diem = re.search(r"diem\s+([a-z])", q)
    if diem:
        entities["point"] = diem.group(1)

    return entities

if __name__ == "__main__":
    test_questions = [
        "Không đội mũ bảo hiểm bị phạt bao nhiêu?",
        "Xe máy vượt đèn đỏ bị phạt bao nhiêu?",
        "Điều 6 nói gì?",
        "Điều 6 khoản 2 nói gì?",
        "Tái phạm vượt đèn đỏ bị xử thế nào?",
        "Nồng độ cồn cao bị phạt bao nhiêu?"
    ]

    for q in test_questions:
        print(f"Câu hỏi: {q}")
        print("Entities:", extract_entities(q))
        print("-" * 50)