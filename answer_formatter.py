def format_legal_basis(article=None, clause=None, point=None):
    parts = []
    if article:
        parts.append(f"Điều {article}")
    if clause:
        parts.append(f"Khoản {clause}")
    if point:
        parts.append(f"Điểm {point}")
    return ", ".join(parts)

def format_answer(intent: str, results: list[dict]) -> str:
    if not results:
        return "Không tìm thấy thông tin phù hợp."

    row = results[0]

    if intent == "ASK_PENALTY":
        fine = row.get("fine")
        legal_basis = format_legal_basis(
            row.get("article"),
            row.get("clause"),
            row.get("point")
        )
        if legal_basis:
            return f"Mức phạt là {fine}. Căn cứ pháp lý: {legal_basis}."
        return f"Mức phạt là {fine}."

    if intent == "ASK_LEGAL_BASIS":
        article = row.get("article", "không rõ")
        clause = row.get("clause", "không rõ")
        point = row.get("point", "không rõ")

        return (
            f"Hành vi này được quy định tại Điều {article}, "
            f"Khoản {clause}, Điểm {point}."
        )

    if intent == "ASK_ARTICLE_CONTENT":
        content = row.get("content", "không có nội dung")
        return f"Nội dung điều luật: {content}"

    if intent == "ASK_AGGRAVATION":
        effect = row.get("effect", "không rõ")
        return f"Trong trường hợp này, hệ quả pháp lý là: {effect}"

    return "Chưa hỗ trợ định dạng câu trả lời cho intent này."