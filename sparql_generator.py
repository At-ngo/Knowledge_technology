def generate_sparql(intent: str, entities: dict) -> str:
    PREFIX = "PREFIX ex: <http://example.org/legal#>\n"

    if intent == "ASK_PENALTY" and "violation" not in entities:
        return "Thiếu entity violation để tạo truy vấn ASK_PENALTY."

    if intent == "ASK_PENALTY" and "violation" in entities:
        violation = entities["violation"]
        return PREFIX + f"""
SELECT ?fine ?article ?clause ?point
WHERE {{
    ex:{violation} ex:hasPenalty ?p .
    ?p ex:fineAmount ?fine .
    ex:{violation} ex:regulatedBy ?rule .
    ?rule ex:articleNumber ?article .
    OPTIONAL {{ ?rule ex:clauseNumber ?clause . }}
    OPTIONAL {{ ?rule ex:pointNumber ?point . }}
}}
"""

    if intent == "ASK_LEGAL_BASIS" and "violation" in entities:
        violation = entities["violation"]
        return PREFIX + f"""
SELECT ?article ?clause ?point
WHERE {{
    ex:{violation} ex:regulatedBy ?rule .
    ?rule ex:articleNumber ?article .
    OPTIONAL {{ ?rule ex:clauseNumber ?clause . }}
    OPTIONAL {{ ?rule ex:pointNumber ?point . }}
}}
"""

    if intent == "ASK_ARTICLE_CONTENT" and "article" in entities:
        article = entities["article"]
        clause_filter = ""
        if "clause" in entities:
            clause = entities["clause"]
            clause_filter = f'?rule ex:clauseNumber "{clause}" .'

        return PREFIX + f"""
SELECT ?content
WHERE {{
    ?rule ex:articleNumber "{article}" .
    {clause_filter}
    ?rule ex:content ?content .
}}
"""

    if intent == "ASK_AGGRAVATION" and "violation" in entities and "condition" in entities:
        violation = entities["violation"]
        condition = entities["condition"]
        return PREFIX + f"""
SELECT ?effect
WHERE {{
    ex:{violation} ex:hasCondition ex:{condition} .
    ex:{condition} ex:legalEffect ?effect .
}}
"""

    return "Không tạo được SPARQL cho câu hỏi này."