import PropTypes from "prop-types";
import { distinctIntents } from "../state/historyUtils.js";

function HistoryPanel({
  history,
  rawHistory,
  filters,
  onFiltersChange,
  onReplay,
  onClose,
}) {
  const intents = distinctIntents(rawHistory);
  const statuses = ["ok", "empty", "warn", "error"];

  return (
    <div className="card history-card">
      <div className="card-header history-header">
        <div>
          <h2>Lịch sử truy vấn</h2>
          <p>Lọc theo intent hoặc trạng thái để debug từng nhóm câu hỏi.</p>
        </div>
        {onClose && (
          <button
            className="icon-button"
            aria-label="Đóng lịch sử truy vấn"
            onClick={onClose}
          >
            ×
          </button>
        )}
      </div>

      <div className="filter-row">
        <label>
          Intent
          <select
            value={filters.intent}
            onChange={(event) =>
              onFiltersChange({ ...filters, intent: event.target.value })
            }
          >
            <option value="all">Tất cả</option>
            {intents.map((intent) => (
              <option key={intent} value={intent}>
                {intent}
              </option>
            ))}
          </select>
        </label>

        <label>
          Trạng thái
          <select
            value={filters.status}
            onChange={(event) =>
              onFiltersChange({ ...filters, status: event.target.value })
            }
          >
            <option value="all">Tất cả</option>
            {statuses.map((status) => (
              <option key={status} value={status}>
                {status}
              </option>
            ))}
          </select>
        </label>
      </div>

      <ul className="history-list">
        {history.map((item) => (
          <li key={item.id} className={`history-item status-${item.status}`}>
            <div>
              <p className="history-question">{item.question}</p>
              <p className="history-meta">
                Intent: {item.intent} ·{" "}
                {new Date(item.timestamp).toLocaleTimeString()}
              </p>
            </div>
            <div className="history-actions">
              <button onClick={() => onReplay(item)}>Hỏi lại</button>
              {item.sparql && (
                <button
                  onClick={() => navigator.clipboard.writeText(item.sparql)}
                >
                  Copy SPARQL
                </button>
              )}
            </div>
          </li>
        ))}
        {history.length === 0 && (
          <p className="muted">Không có truy vấn nào phù hợp với bộ lọc.</p>
        )}
      </ul>
    </div>
  );
}

HistoryPanel.propTypes = {
  history: PropTypes.array.isRequired,
  rawHistory: PropTypes.array.isRequired,
  filters: PropTypes.object.isRequired,
  onFiltersChange: PropTypes.func.isRequired,
  onReplay: PropTypes.func.isRequired,
  onClose: PropTypes.func,
};

export default HistoryPanel;
