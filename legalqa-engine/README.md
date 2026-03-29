# Legal QA Module 5 - Spring Boot

Project này là bản viết lại Module 5 bằng Spring Boot.

## Chức năng
- Nhận câu hỏi pháp lý tiếng Việt
- Detect intent
- Extract entity từ mapping của Module 5
- Sinh SPARQL theo ontology `http://example.org/legal-qa#`
- Query Fuseki dataset gốc hoặc dataset suy luận
- Trả câu trả lời tiếng Việt + SPARQL + raw results

## Cấu trúc gọn
- `QaController.java`: web + API
- `QaService.java`: toàn bộ pipeline Module 5
- `FusekiService.java`: gọi Fuseki
- `QaResponse.java`: DTO kết quả

## Endpoint web/API
- Web UI: `GET /`
- Form hỏi đáp: `POST /`
- API JSON: `POST /api/ask`
- Health check: `GET /api/health`

Body mẫu cho `/api/ask`
```json
{
  "question": "Điều 2 nói gì?"
}
```

## Cấu hình Fuseki
Sửa trong `src/main/resources/application.yml`:
- `app.fuseki.base-endpoint`
- `app.fuseki.inference-endpoint`

### Đường dẫn đang để mặc định
- Base: `http://localhost:3030/legalqa/query`
- Inference: `http://localhost:3030/legalqa-inf/sparql`

## Vì sao inference dùng `/sparql`?
Trong file `fuseki-config-inference.ttl` của nhóm em có:
- `fuseki:name "legalqa-inf"`
- `fuseki:serviceQuery "sparql"`

Nên endpoint query cho dataset suy luận là:
- `http://localhost:3030/legalqa-inf/sparql`

## Kiểm tra lại README của nhóm em
README của các module khác đang ổn về logic, nhưng khi code Spring Boot thì nên hiểu chính xác như sau:
- Dataset root gốc: `/legalqa/`
- Dataset root suy luận: `/legalqa-inf/`
- Query endpoint thật thường là `/query` hoặc `/sparql`, tùy cấu hình serviceQuery

### Với project hiện tại
- `legalqa` được giả định chạy qua `/query`
- `legalqa-inf` chạy qua `/sparql`

Nếu em tạo dataset gốc `legalqa` bằng file config riêng và cũng đặt `serviceQuery "sparql"`, hãy đổi:
- `http://localhost:3030/legalqa/query`
thành
- `http://localhost:3030/legalqa/sparql`

## Cách chạy
### 1. Chạy Fuseki gốc
- Mở `fuseki-server.bat`
- Tạo dataset `legalqa`
- Upload `legal_ontology.rdf` và `legal_triples.ttl`

### 2. Chạy Fuseki suy luận
Từ thư mục Fuseki:
```bash
fuseki-server.bat --config ..\Knowledge_technology\reasoning\fuseki-config-inference.ttl
```

### 3. Chạy Spring Boot
```bash
mvn spring-boot:run
```

Hoặc build jar:
```bash
mvn clean package
java -jar target/legalqa-module5-1.0.0.jar
```

## Câu hỏi nên test
- `Điều 2 nói gì?`
- `Đường bộ bao gồm những gì?`
- `Ủy ban nhân dân các cấp có trách nhiệm gì?`
- `Giấy phép lái xe thuộc điều nào?`
- `Nồng độ cồn có phải vi phạm không?`
- `Nồng độ cồn có nghiêm trọng không?`
- `Không đội mũ bảo hiểm bị phạt bao nhiêu?`

## Lưu ý
- Intent `ASK_PENALTY` hiện chỉ trả lời rằng ontology chưa mô hình hóa mức phạt cụ thể.
- `ASK_ARTICLE_CONTENT` đang trả lời từ triples hiện có (`mentionsEntity`, `rawSubject`, `rawObject`), không phụ thuộc `laws_cleaned.json`.
