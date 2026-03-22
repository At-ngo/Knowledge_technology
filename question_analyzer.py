from intent_detector import detect_intent
from entity_extractor import extract_entities

def analyze_question(question: str) -> dict:
    return {
        "question": question,
        "intent": detect_intent(question),
        "entities": extract_entities(question)
    }

if __name__ == "__main__":
    test_questions = [
        "Không đội mũ bảo hiểm bị phạt bao nhiêu?",
        "Xe máy vượt đèn đỏ bị phạt bao nhiêu?",
        "Điều 6 khoản 2 nói gì?",
        "Tái phạm vượt đèn đỏ bị xử thế nào?"
    ]

    for q in test_questions:
        result = analyze_question(q)
        print(result)
        print("-" * 60)