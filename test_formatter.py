from answer_formatter import format_answer

test_data = [
    (
        "ASK_PENALTY",
        [{"fine": "400.000 - 600.000 đồng", "article": "6", "clause": "2", "point": "a"}]
    ),
    (
        "ASK_LEGAL_BASIS",
        [{"article": "6", "clause": "2", "point": "a"}]
    ),
    (
        "ASK_ARTICLE_CONTENT",
        [{"content": "Người điều khiển xe mô tô, xe gắn máy không đội mũ bảo hiểm..."}]
    ),
    (
        "ASK_AGGRAVATION",
        [{"effect": "Mức phạt tăng do tái phạm"}]
    )
]

for intent, results in test_data:
    print("Intent:", intent)
    print(format_answer(intent, results))
    print("-" * 80)