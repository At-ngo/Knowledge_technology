import PropTypes from "prop-types";
import { useState } from "react";

function EndpointDrawer({ open, onClose, settings, onSave }) {
  const [local, setLocal] = useState(settings);

  const handleSave = () => {
    onSave(local);
    onClose();
  };

  const resetDefaults = () => {
    const next = {
      apiBase: "http://localhost:8080/api",
      useDebugEndpoint: true,
      pinnedIntent: "all",
      useInferenceForIntents: settings.useInferenceForIntents,
    };
    setLocal(next);
    onSave(next);
  };

  return (
    <div className={`drawer ${open ? "open" : ""}`}>
      <div className="drawer-panel">
        <header>
          <h3>Cấu hình endpoint</h3>
          <button className="ghost" onClick={onClose}>
            Đóng
          </button>
        </header>

        <label>
          API Gateway
          <input
            type="text"
            value={local.apiBase}
            onChange={(event) =>
              setLocal({ ...local, apiBase: event.target.value })
            }
          />
          <span className="hint">
            Mặc định proxy qua Vite: http://localhost:8080/api
          </span>
        </label>

        <label className="checkbox">
          <input
            type="checkbox"
            checked={local.useDebugEndpoint}
            onChange={(event) =>
              setLocal({ ...local, useDebugEndpoint: event.target.checked })
            }
          />
          Sử dụng `/ask/debug` để xem đầy đủ SPARQL & metadata
        </label>

        <div className="drawer-actions">
          <button className="ghost" onClick={resetDefaults}>
            Khôi phục mặc định
          </button>
          <button className="primary" onClick={handleSave}>
            Lưu
          </button>
        </div>
      </div>
    </div>
  );
}

EndpointDrawer.propTypes = {
  open: PropTypes.bool,
  onClose: PropTypes.func.isRequired,
  settings: PropTypes.object.isRequired,
  onSave: PropTypes.func.isRequired,
};

export default EndpointDrawer;
