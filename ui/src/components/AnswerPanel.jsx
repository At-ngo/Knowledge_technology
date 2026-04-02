import PropTypes from "prop-types";
import { useEffect, useState } from "react";

function MetaRow({ label, value }) {
  if (!value) return null;
  return (
    <div className="meta-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

MetaRow.propTypes = {
  label: PropTypes.string.isRequired,
  value: PropTypes.string,
};

const STEP = 3;
const INTERVAL = 15;

function AnswerPanel({ entry, isLoading, error, answerRef, onTypingChange }) {
  const [typedAnswer, setTypedAnswer] = useState("");
  const [isTyping, setIsTyping] = useState(false);

  useEffect(() => {
    if (!entry?.answer || isLoading) {
      setTypedAnswer(entry?.answer || "");
      setIsTyping(false);
      return undefined;
    }

    let index = 0;
    const text = entry.answer;
    setTypedAnswer("");
    setIsTyping(true);

    const timer = setInterval(() => {
      index = Math.min(index + STEP, text.length);
      setTypedAnswer(text.slice(0, index));
      if (index >= text.length) {
        clearInterval(timer);
        setIsTyping(false);
      }
    }, INTERVAL);

    return () => clearInterval(timer);
  }, [entry, isLoading]);

  useEffect(() => {
    if (onTypingChange) onTypingChange(isTyping);
  }, [isTyping, onTypingChange]);

  const answerText = isTyping ? typedAnswer : entry?.answer;

  return (
    <div className="card">
      <div className="card-header">
        <h2>Kết quả gần nhất</h2>
        {entry && (
          <p>Phản hồi lúc {new Date(entry.timestamp).toLocaleTimeString()}</p>
        )}
      </div>
      {isLoading && <p className="muted">Đang chờ Fuseki trả lời...</p>}
      {error && <p className="error">{error}</p>}
      {!isLoading && !entry && !error && (
        <p className="muted">
          Chưa có câu hỏi nào được gửi trong phiên làm việc này.
        </p>
      )}
      {entry && !isLoading && (
        <>
          <pre
            className={`answer-box${isTyping ? " typing" : ""}`}
            ref={answerRef}
          >
            {answerText}
            {isTyping && <span className="typing-caret" aria-hidden="true" />}
          </pre>
          <div className="meta-grid">
            <MetaRow label="Intent" value={entry.intent} />
            <MetaRow label="Endpoint" value={entry.endpoint} />
            <MetaRow label="Trạng thái" value={entry.status} />
          </div>
          {entry.sparql && (
            <details className="sparql-block">
              <summary>SPARQL được sinh</summary>
              <pre>{entry.sparql}</pre>
            </details>
          )}
        </>
      )}
    </div>
  );
}

AnswerPanel.propTypes = {
  entry: PropTypes.object,
  isLoading: PropTypes.bool,
  error: PropTypes.string,
  answerRef: PropTypes.oneOfType([
    PropTypes.func,
    PropTypes.shape({ current: PropTypes.any }),
  ]),
  onTypingChange: PropTypes.func,
};

export default AnswerPanel;
