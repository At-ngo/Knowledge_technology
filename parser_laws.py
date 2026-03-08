from docx import Document
import re
import json
import os


# =========================
# 1. ĐỌC FILE DOCX
# =========================
def extract_text_from_docx(path):
    doc = Document(path)
    full_text = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            full_text.append(text)
    return "\n".join(full_text)


# =========================
# 2. TÁCH CHƯƠNG
# =========================
def split_chapters(text):
    pattern = r"\n(?:Chương|CHƯƠNG)\s+([IVXLCDM]+|\d+)"
    matches = list(re.finditer(pattern, text))

    if not matches:
        return [(None, text)]

    chapters = []

    for i in range(len(matches)):
        chapter_number = matches[i].group(1).upper()
        start = matches[i].end()

        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)

        chapter_content = text[start:end].strip()
        chapters.append((chapter_number, chapter_content))

    return chapters


# =========================
# 3. TÁCH ĐIỀU & TITLE
# =========================
def split_articles(text):
    pattern = r"\nĐiều\s+(\d+)\.\s*(.*)"
    matches = list(re.finditer(pattern, text))

    if not matches:
        return [(None, None, text)]

    articles = []

    for i in range(len(matches)):
        article_number = matches[i].group(1)
        article_title = matches[i].group(2).strip()
        start = matches[i].end()

        if i + 1 < len(matches):
            end = matches[i + 1].start()
        else:
            end = len(text)

        article_content = text[start:end].strip()

        articles.append((article_number, article_title, article_content))

    return articles


# =========================
# 4. TÁCH KHOẢN
# =========================
def split_clauses(article_text):
    pattern = r"(?:^|\n)(\d+)\.\s"
    parts = re.split(pattern, article_text)

    if len(parts) <= 1:
        return [(None, article_text.strip())]

    clauses = []
    for i in range(1, len(parts), 2):
        clause_number = parts[i]
        clause_content = parts[i + 1].strip()
        clauses.append((clause_number, clause_content))

    return clauses


# =========================
# 5. TÁCH ĐIỂM
# =========================
def split_points(clause_text):

    pattern = r"(?:^|\n)([a-zđ])\)\s"
    parts = re.split(pattern, clause_text)

    if len(parts) <= 1:
        return None, [(None, clause_text.strip())]

    intro = parts[0].strip()
    points = []

    for i in range(1, len(parts), 2):
        point_letter = parts[i]
        point_content = parts[i + 1].strip()
        points.append((point_letter, point_content))

    return intro, points


# =========================
# 6. XỬ LÝ 1 LUẬT
# =========================
def process_law(file_path, law_name):
    text = extract_text_from_docx(file_path)

    # Cắt phần công bố cuối luật
    text = re.split(r"Luật này được Quốc hội", text)[0]

    results = []

    chapters = split_chapters(text)

    for chapter_number, chapter_content in chapters:

        articles = split_articles(chapter_content)

        for article_number, article_title, article_content in articles:

            clauses = split_clauses(article_content)

            for clause_number, clause_content in clauses:

                intro, points = split_points(clause_content)

                # =========================
                # CLAUSE NO POINT
                # =========================
                if points == [(None, clause_content.strip())]:

                    content_clean = (
                        clause_content
                        .replace("/.", "")
                        .replace("\n", " ")
                        .strip()
                    )

                    uid = f"{law_name}_{chapter_number or '0'}_{article_number or '0'}_{clause_number or '0'}"

                    results.append({
                        "id": uid,
                        "law": law_name,
                        "chapter": chapter_number or "",
                        "article": article_number or "",
                        "article_title": article_title or "",
                        "clause": clause_number or "",
                        "point": "",
                        "content": content_clean
                    })

                    continue

                # =========================
                # CLAUSE INTRO
                # =========================
                if intro:

                    content_clean = (
                        intro
                        .replace("/.", "")
                        .replace("\n", " ")
                        .strip()
                    )

                    uid = f"{law_name}_{chapter_number or '0'}_{article_number or '0'}_{clause_number or '0'}_0"

                    results.append({
                        "id": uid,
                        "law": law_name,
                        "chapter": chapter_number or "",
                        "article": article_number or "",
                        "article_title": article_title or "",
                        "clause": clause_number or "",
                        "point": "",
                        "content": content_clean
                    })

                # =========================
                # POINTS
                # =========================
                for point_letter, point_content in points:

                    content_clean = (
                        point_content
                        .replace("/.", "")
                        .replace("\n", " ")
                        .strip()
                    )

                    uid = f"{law_name}_{chapter_number or '0'}_{article_number or '0'}_{clause_number or '0'}_{point_letter}"

                    results.append({
                        "id": uid,
                        "law": law_name,
                        "chapter": chapter_number or "",
                        "article": article_number or "",
                        "article_title": article_title or "",
                        "clause": clause_number or "",
                        "point": point_letter,
                        "content": content_clean
                    })

    return results


# =========================
# 7. MAIN
# =========================
def main():
    laws = [
        ("data/luatDB.docx", "LDB"),
        ("data/luatLaoDong.docx", "LLD"),
        ("data/luatTTATGTDB.docx", "TTATGTDB")
    ]

    all_data = []

    for path, name in laws:
        print(f"Đang xử lý: {name}")
        data = process_law(path, name)
        all_data.extend(data)

    os.makedirs("output", exist_ok=True)

    with open("output/laws_cleaned.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    print("Hoàn thành!")
    print("Đã lưu vào output/laws_cleaned.json")
    print("Tổng số mục:", len(all_data))


if __name__ == "__main__":
    main()