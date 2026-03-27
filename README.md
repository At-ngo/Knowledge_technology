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

---
