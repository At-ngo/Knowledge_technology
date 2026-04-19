Các bước để chạy lại toàn bộ hệ thống:

1. **Xem ontology**
   - Download Protégé: https://protege.stanford.edu/software.php#desktop-protege
   - Mở file `ontology/legal_ontology.rdf` để duyệt class, property và kiểm tra rule annotation (nếu cần).

2. **Khởi động Fuseki cơ bản (dataset legalqa không suy luận)**
   - Download Apache Jena Fuseki 6.0.0: https://jena.apache.org/download/
   - Giải nén, chạy `fuseki-server.bat`.
   - Tạo dataset tên `legalqa`.
   - Upload hai file: `ontology/legal_ontology.rdf` và `legal_triples.ttl`.
   - Mở giao diện SPARQL để chạy các truy vấn kiểm tra dữ liệu gốc.

3. **Chạy module suy luận (legalqa-inf)**
   - Đảm bảo đã cài Java và đặt biến môi trường JAVA_HOME.
   - Từ thư mục Fuseki, nạp dữ liệu vào TDB2:  
     `tdb2.tdbloader --loc ..\Knowledge_technology\tdb-legalqa ..\Knowledge_technology\ontology\legal_ontology.rdf ..\Knowledge_technology\legal_triples.ttl`  
     (xóa thư mục `tdb-legalqa` trước nếu cần nạp lại).
   - Chạy `fuseki-server.bat --config ..\Knowledge_technology\reasoning\fuseki-config-inference.ttl` để mở endpoint `/legalqa-inf`.
   - Dùng giao diện SPARQL hoặc script `reasoning/run_inference_demo.py` để gửi các truy vấn kiểm thử module 4 (ví dụ các câu ASK/SELECT trong log).
   - Endpoint `/legalqa/` phục vụ dữ liệu gốc, `/legalqa-inf/` phục vụ dữ liệu đã suy luận.

4. **Chạy test module 5**
   - Khởi động Fuseki Server.
   - Chạy file `LegalQaApplication.java`.
   - Truy cập `http://localhost:8080/`.

5. **Chạy benchmark đánh giá mô hình QA**
   - Bộ benchmark nằm tại: `evaluation/qa_benchmark.py`.
   - Dataset mẫu nhanh (4 câu): `evaluation/qa_eval_dataset.example.json`.
   - Dataset full coverage (46 câu): `evaluation/qa_eval_dataset.full.json`.
   - Chạy dataset mẫu:
     `python evaluation/qa_benchmark.py --dataset evaluation/qa_eval_dataset.example.json --base-url http://localhost:8080 --output evaluation/reports/qa_benchmark_report.json`
   - Chạy dataset full:
     `python evaluation/qa_benchmark.py --dataset evaluation/qa_eval_dataset.full.json --base-url http://localhost:8080 --output evaluation/reports/qa_benchmark_report.full.json`
     `python evaluation/qa_benchmark.py --dataset evaluation/qa_eval_dataset.full.json --base-url http://localhost:8080 --output evaluation/reports/qa_benchmark_report.full.json --confidence-output evaluation/reports/model_confidence_metrics.json`
   - Script sẽ trả các chỉ số chính:
     - `intent_accuracy`
     - `answer_exact_accuracy`
     - `answer_contains_accuracy`
     - `answer_token_f1`
     - `success_accuracy`
     - `request_success_rate`
     - `latency_ms` (avg/p50/p95/max)
   - Kết quả chi tiết được ghi ra file JSON trong thư mục `evaluation/reports/`.

---
