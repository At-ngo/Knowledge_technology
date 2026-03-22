from question_analyzer import analyze_question
from sparql_generator import generate_sparql

test_questions = [
    "Không đội mũ bảo hiểm bị phạt bao nhiêu?",
    "Vượt đèn đỏ thuộc điều nào?",
    "Điều 6 khoản 2 nói gì?",
    "Tái phạm vượt đèn đỏ bị xử thế nào?"
]

for q in test_questions:
    result = analyze_question(q)
    sparql = generate_sparql(result["intent"], result["entities"])

    print("Câu hỏi:", q)
    print("Intent:", result["intent"])
    print("Entities:", result["entities"])
    print("SPARQL:")
    print(sparql)
    print("=" * 80)