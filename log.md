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

---

## 22/03/2026

### Module 4 - Inference Engine

Status: DONE

Pipeline:

1. Thiết kế tập luật GenericRuleReasoner (`reasoning/legal_inference.rules`). Bộ luật bao gồm các nhóm quy tắc: lan truyền `baoGom` theo kiểu bắc cầu, thừa hưởng `apDungCho` xuống từng thành viên nhóm, đánh dấu `HanhViViPham`/`SevereViolation` cho hành vi bị cấm (đặc biệt các trường hợp vi phạm nồng độ cồn), và tự động nối hành vi ↔ điều luật để dễ truy vấn.
2. Mở rộng ontology: bổ sung hai lớp `HanhViViPham` và `SevereViolation`, cập nhật các ràng buộc liên hệ với `LegalEntity`, đồng thời đồng bộ lại file `legal_ontology.rdf`.
3. Triển khai hạ tầng Fuseki suy luận: cấu hình `reasoning/fuseki-config-inference.ttl` trỏ tới kho TDB2 `tdb-legalqa`, nạp rule set vào `GenericRuleReasonerFactory`, khai báo endpoint `/legalqa-inf` hỗ trợ query/update/read graph store.
4. Viết script kiểm thử `reasoning/run_inference_demo.py` sử dụng RDFlib để nạp RDF + rule, chạy suy luận cục bộ, thống kê số triple phát sinh và chạy một loạt truy vấn ASK/SELECT mẫu trước khi đưa rule vào Fuseki.
5. Tái nạp dữ liệu vào TDB bằng `tdb2.tdbloader`, khởi động Fuseki với cấu hình mới và xác nhận endpoint inference trả lời đúng (đặc biệt các truy vấn ASK/SELECT ghi trong báo cáo kiểm thử).

Kết quả kiểm thử (run_inference_demo.py):

- 50 triple `baoGom` mới, 15 triple `apDungCho` mới, 208 hành vi gắn `HanhViViPham`, 3 trường hợp `SevereViolation`, 1128 liên kết điều luật ↔ hành vi; các truy vấn mẫu đều trả về như kỳ vọng trước khi triển khai trên Fuseki.
- `ASK { legal:KetCauHaTangDuongBo legal:baoGom legal:Duong }` ⇒ TRUE (không tồn tại trong dữ liệu gốc).
- `SELECT ?holder { ?holder legal:apDungCho legal:NguoiDiBoTrenDuongBo }` ⇒ trả về `legal:ThongTin` như kỳ vọng.
- `SELECT ?action { ?action rdf:type legal:SevereViolation }` ⇒ trả về ba hành vi liên quan nồng độ cồn.

### Module 5 - Legal Question Answering

Status: DONE

Tasks:

- Xây dựng bộ câu hỏi kiểm thử cho hệ thống hỏi đáp pháp luật
- Thiết kế bộ phân tích câu hỏi tiếng Việt:
    - chuẩn hóa câu hỏi
    - nhận diện intent
    - trích xuất entity
- Mapping câu hỏi sang ontology concept dựa trên từ điển thực thể và mã luật
- Sinh truy vấn SPARQL theo từng loại câu hỏi
- Kết nối Apache Jena Fuseki để truy vấn dữ liệu gốc và dữ liệu suy luận
- Xây dựng bộ format câu trả lời tiếng Việt
- Tích hợp module thành backend Spring Boot và hỗ trợ trả JSON cho giao diện web

Mô tả công việc:

Module 5 có nhiệm vụ nhận câu hỏi tiếng Việt từ người dùng, phân tích câu hỏi để xác định intent và entity, sau đó ánh xạ sang ontology concept tương ứng.

Từ thông tin đó, hệ thống sinh truy vấn SPARQL phù hợp, gửi truy vấn tới Fuseki để lấy dữ liệu từ knowledge graph, rồi format lại thành câu trả lời tiếng Việt.

Ngoài ra, module cũng xử lý các trường hợp câu hỏi mơ hồ, ví dụ khi người dùng chỉ hỏi “Điều 2 nói gì?” nhưng không nêu rõ tên luật.

Các nhóm intent chính đã hỗ trợ:

- `ASK_ARTICLE_CONTENT`
- `ASK_LEGAL_BASIS`
- `ASK_DEFINITION`
- `ASK_INCLUDES`
- `ASK_RESPONSIBILITY`
- `ASK_VIOLATION_CHECK`
- `ASK_AGGRAVATION`
- `ASK_LIST_VIOLATIONS`

Kết quả:

- Hệ thống đã chạy được pipeline:
  question → intent/entity → SPARQL → Fuseki → answer
- Đã truy vấn được dữ liệu từ ontology/RDF và trả lời cho một số câu hỏi tiêu biểu
- Đã tích hợp backend bằng Spring Boot và hỗ trợ trả JSON cho giao diện web

Cấu trúc đầu ra của module 5:

{
"question": "câu hỏi người dùng",
"answer": "câu trả lời của hệ thống"
}

Output files:

- `QaController.java`
- `QaService.java`
- `FusekiService.java`
- `QaResponse.java`
- `application.yml`
- `mapping_dictionary.json`
- `intent_relation_map.json`
- `index.html`
