Các bước để chạy lại:

1. Download Protege để xem ontology: https://protege.stanford.edu/software.php#desktop-protege
2. Chạy Fuseki local:
   Download apache-jena-fuseki-6.0.0.zip: https://jena.apache.org/download/
   Tạo dataset: legalqa
   Upload:
   legal_ontology.rdf
   legal_triples.ttl
   Truy vấn SPARQL

---

## Module 4 - Inference Engine

Artifacts mới:

- reasoning/legal_inference.rules — tập luật cho GenericRuleReasoner (bao gồm suy luận bắc cầu `baoGom`, kế thừa `apDungCho`, phân loại hành vi bị cấm và đánh dấu vi phạm nghiêm trọng do nồng độ cồn).
- reasoning/fuseki-config-inference.ttl — cấu hình Fuseki để khởi động dịch vụ `legalqa-inf` với mô hình suy luận.
- reasoning/run_inference_demo.py — script RDFlib để dry-run luật trước khi triển khai lên Fuseki.

Cách kiểm thử nhanh:

1. Bật virtualenv (`.venv`) hoặc cài `rdflib`, sau đó chạy `python reasoning/run_inference_demo.py` trong thư mục Knowledge_technology.
2. Script sẽ thống kê số triple được suy diễn và cho mẫu truy vấn SPARQL:
   - `ASK { legal:KetCauHaTangDuongBo legal:baoGom legal:Duong }` ⇒ `true` (từ chuỗi baoGom nhiều tầng).
   - `SELECT ?holder { ?holder legal:apDungCho legal:NguoiDiBoTrenDuongBo }` ⇒ trả về `legal:ThongTin`.
   - `SELECT ?action { ?action rdf:type legal:SevereViolation }` ⇒ các hành vi liên quan đến nồng độ cồn.
3. Khi sẵn sàng triển khai, chạy Fuseki với `./fuseki-server --config reasoning/fuseki-config-inference.ttl` để mở endpoint `/legalqa-inf/sparql` đã gắn reasoner.
