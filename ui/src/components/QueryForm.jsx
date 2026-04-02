import PropTypes from "prop-types";

function QueryForm({ value, onChange, onSubmit, loading, textareaRef }) {
  return (
    <div className="card">
      <div className="card-header">
        <h2>Đặt câu hỏi</h2>
        <p>
          Ví dụ: "Điều 2 của Luật Đường bộ nói gì?" hoặc "Giấy phép lái xe thuộc
          điều nào?"
        </p>
      </div>
      <textarea
        className="question-input"
        ref={textareaRef}
        rows={4}
        placeholder="Nhập câu hỏi tiếng Việt..."
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      <div className="form-actions">
        <button
          className="primary"
          onClick={onSubmit}
          disabled={loading || !value.trim()}
        >
          {loading ? "Đang truy vấn..." : "Gửi câu hỏi"}
        </button>
      </div>
    </div>
  );
}

QueryForm.propTypes = {
  value: PropTypes.string.isRequired,
  onChange: PropTypes.func.isRequired,
  onSubmit: PropTypes.func.isRequired,
  loading: PropTypes.bool,
  textareaRef: PropTypes.oneOfType([
    PropTypes.func,
    PropTypes.shape({ current: PropTypes.any }),
  ]),
};

export default QueryForm;
