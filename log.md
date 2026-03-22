# Development Log - Legal QA System

## 07/03/2026

### Module 1 - Corpus Processing
Status: DONE

Tasks:
- Thu thập PDF luật (LUẬT LAO ĐỘNG; LUẬT TRẬT TỰ, AN TOÀN GIAO THÔNG ĐƯỜNG BỘ; LUẬT ĐƯỜNG BỘ)
- Convert sang text
- Tách cấu trúc: Chương / Điều / Khoản / Điểm
- Chuẩn hóa thành JSON

Output file:
data/legal_corpus.json

Example:
{
    "id": "LDB_I_1_0_0",
    "law": "LDB",
    "chapter": "I",
    "article": "1",
    "article_title": "Phạm vi điều chỉnh",
    "clause": "",
    "point": "",
    "content": "Luật này quy định về hoạt động đường bộ và quản lý nhà nước về hoạt động đường bộ."
  },
  {
    "id": "LDB_I_2_1_0",
    "law": "LDB",
    "chapter": "I",
    "article": "2",
    "article_title": "Giải thích từ ngữ",
    "clause": "1",
    "point": "",
    "content": "Hoạt động đường bộ bao gồm: hoạt động về quy hoạch, đầu tư, xây dựng, quản lý, sử dụng, vận hành, khai thác, bảo trì, bảo vệ kết cấu hạ tầng đường bộ; vận tải đường bộ."
  },

---

### Module 2 - Relation Extraction

Tasks: Clone OpenNRE

Task: Trích xuất quan hệ từ văn bản luật

Mô tả công việc:

Sử dụng dữ liệu văn bản luật đã được chuẩn hóa từ Module 1.

Tạo tool và áp dụng mô hình AI kết hợp prompt để phân tích câu luật và trích xuất quan hệ theo dạng:

Subject – Relation – Object.

Chỉ sử dụng các relation trong danh sách định nghĩa sẵn:
quyDinhVe, dinhNghia, baoGom, apDungCho, cam, choPhep, yeuCau, baoDam, mucDich, thucHien, suDung, ketNoi.

Mỗi câu luật có thể tạo ra một hoặc nhiều quan hệ tùy theo nội dung.

Output:

Tập dữ liệu các quan hệ được trích xuất từ văn bản luật.

Tổng số quan hệ thu được: khoảng 3200 triples.

Format Output:

Dữ liệu được lưu dưới dạng JSON với cấu trúc:

{
 "text": "câu luật gốc",
 "h": { "name": "subject" },
 "t": { "name": "object" },
 "relation": "relation_type"
}

Ví dụ:

{
 "text": "Luật này quy định về hoạt động đường bộ và quản lý nhà nước về hoạt động đường bộ",
 "h": { "name": "Luật này" },
 "t": { "name": "hoạt động đường bộ" },
 "relation": "quyDinhVe"
}

Ngoài ra các quan hệ cũng được lưu dưới dạng knowledge triples:

{
 "subject": "Luật này",
 "relation": "quyDinhVe",
 "object": "hoạt động đường bộ"
}

Các file kết quả được sử dụng để:

Huấn luyện mô hình Relation Extraction

Xây dựng Knowledge Graph từ văn bản luật

Output là 2 file dataset_annotation.json và knowledge_triples.json

### Module 3 - Ontology & RDF
Tasks:
- Thiết kế ontology bằng Protégé
- Xây dựng các lớp (Class): Law, Chapter, Article, LegalEntity
- Xây dựng các ObjectProperty:
  - hasChapter
  - hasArticle
  - mentionsEntity
  - quyDinhVe
  - dinhNghia
  - baoGom
  - apDungCho
  - cam
  - choPhep
  - yeuCau
  - baoDam
  - mucDich
  - thucHien
  - suDung
  - ketNoi
- Xây dựng các DataProperty:
  - lawCode
  - chapterCode
  - articleNumber
  - label
  - rawSubject
  - rawObject

- Định nghĩa namespace cho ontology

- Chuyển đổi knowledge triples từ Module 2 sang RDF/Turtle (.ttl)

- Chuẩn hóa entity trước khi sinh RDF:
    Chuẩn hóa chữ hoa/thường
    Loại bỏ một số từ dẫn như “các”, “những”, “mọi”
    Gom các entity đồng nghĩa/biến thể về cùng một URI

- Nạp ontology và RDF triples vào Apache Jena Fuseki

- Kiểm tra dữ liệu bằng truy vấn SPARQL

Mô tả công việc:

Sử dụng dữ liệu knowledge triples từ Module 2 để xây dựng ontology và biểu diễn tri thức dưới dạng RDF.

Ontology được xây dựng bằng Protégé với 4 lớp chính:
- Law: biểu diễn văn bản luật
- Chapter: biểu diễn chương của luật
- Article: biểu diễn điều luật
- LegalEntity: biểu diễn các thực thể pháp lý được trích xuất từ nội dung luật

Các relation ngữ nghĩa được ánh xạ trực tiếp từ output Module 2 theo dạng: Subject – Relation – Object
Trong đó:
- Subject và Object được biểu diễn thành các cá thể của lớp LegalEntity
- Các điều luật vẫn được giữ lại để liên kết với thực thể thông qua quan hệ mentionsEntity
- rawSubject và rawObject được dùng để lưu lại nội dung subject/object gốc phục vụ truy vết và kiểm tra

Ontology sử dụng namespace:
- legal: <http://example.org/legal-qa#>

Dữ liệu từ file knowledge_triples.json được chuyển đổi sang RDF/Turtle bằng script Python và lưu thành file .ttl.

Sau đó ontology và RDF triples được nạp vào Apache Jena Fuseki để: lưu trữ knowledge graph, kiểm tra dữ liệu, truy vấn bằng SPARQL

Output files:
- ontology/legal_ontology.rdf
- legal_triples.ttl
- convertToRDF.py