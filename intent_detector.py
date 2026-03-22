import re 
from unidecode import unidecode

def normalize_text(text: str) -> str:
    text = unidecode(text)
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)    
    return text

def detect_intent(question: str) -> str:
    q = normalize_text(question)

    if ('phat bao nhieu' in q
        or 'muc phat' in q
        or 'bi phat bao nhieu' in q):
        return 'ASK_PENALTY'
    
    if ('dieu nao' in q
        or 'khoan nao' in q
        or 'diem nao' in q
        or 'thuoc dieu nao' in q
        or 'quy dinh o dau' in q):
        return 'ASK_LEGAL_BASIS'
    
    if ("co vi pham khong" in q 
        or "co bi phat khong" in q):
        return "ASK_VIOLATION_CHECK"

    if ("tuoc bang" in q 
        or "tam giu xe" in q 
        or "hinh phat bo sung" in q):
        return "ASK_ADDITIONAL_PENALTY"

    if ("danh sach hanh vi" in q 
        or "nhung hanh vi nao" in q 
        or "cac hanh vi nao" in q):
        return "ASK_LIST_VIOLATIONS"

    if (re.search(r"dieu\s+\d+", q) and ("noi gi" in q or "noi dung" in q)):
        return "ASK_ARTICLE_CONTENT"

    if ("tai pham" in q 
        or "xu nang hon" in q 
        or "nang hon khong" in q):
        return "ASK_AGGRAVATION"

    return "UNKNOWN"

if __name__ == "__main__":
    test_questions = [
        "Không đội mũ bảo hiểm bị phạt bao nhiêu?",
        "Vượt đèn đỏ thuộc điều nào?",
        "Đi ngược chiều có vi phạm không?",
        "Không có bằng lái có bị tước bằng không?",
        "Điều 6 nói gì?",
        "Tái phạm vượt đèn đỏ bị xử thế nào?"
    ]

    for q in test_questions:
        print(f"Câu hỏi: {q}")
        print(f"Intent: {detect_intent(q)}")
        print("-" * 50)