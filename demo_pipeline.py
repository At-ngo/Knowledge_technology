from question_analyzer import analyze_question
from sparql_generator import generate_sparql
from answer_formatter import format_answer

MOCK_RESULTS = {
    "ASK_PENALTY": [
        {"fine": "400.000 - 600.000 đồng", "article": "6", "clause": "2", "point": "a"}
    ],
    "ASK_LEGAL_BASIS": [
        {"article": "6", "clause": "2", "point": "a"}
    ],
    "ASK_ARTICLE_CONTENT": [
        {"content": "Người điều khiển xe mô tô, xe gắn máy không đội mũ bảo hiểm..."}
    ],
    "ASK_AGGRAVATION": [
        {"effect": "Mức phạt tăng do tái phạm"}
    ]
}

questions = [
    "Không đội mũ bảo hiểm bị phạt bao nhiêu?",
    "Vượt đèn đỏ thuộc điều nào?",
    "Điều 6 khoản 2 nói gì?",
    "Tái phạm vượt đèn đỏ bị xử thế nào?"
]

for q in questions:
    analysis = analyze_question(q)
    sparql = generate_sparql(analysis["intent"], analysis["entities"])
    results = MOCK_RESULTS.get(analysis["intent"], [])
    answer = format_answer(analysis["intent"], results)

    print("Câu hỏi:", q)
    print("Intent:", analysis["intent"])
    print("Entities:", analysis["entities"])
    print("SPARQL:")
    print(sparql)
    print("Câu trả lời:")
    print(answer)
    print("=" * 100)