import json
from qa_engine import process_question


def main():
    print("Nhập câu hỏi pháp luật (gõ 'exit' để thoát).")
    while True:
        question = input("> ").strip()
        if not question:
            continue
        if question.lower() in {"exit", "quit"}:
            break
        print(json.dumps(process_question(question), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
