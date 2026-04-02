import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import QueryForm from "./components/QueryForm.jsx";
import AnswerPanel from "./components/AnswerPanel.jsx";
import HistoryPanel from "./components/HistoryPanel.jsx";
import EndpointDrawer from "./components/EndpointDrawer.jsx";
import { createHistoryEntry, filterHistory } from "./state/historyUtils.js";
import mascotImage from "./assets/image.png";

const DEFAULT_SETTINGS = {
  apiBase: "http://localhost:8080/api",
  useDebugEndpoint: true,
  pinnedIntent: "all",
  useInferenceForIntents: [
    "ASK_VIOLATION_CHECK",
    "ASK_AGGRAVATION",
    "ASK_LIST_VIOLATIONS",
  ],
};

function App() {
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [showIntro, setShowIntro] = useState(true);
  const [answerTyping, setAnswerTyping] = useState(false);
  const [history, setHistory] = useState([]);
  const [filters, setFilters] = useState({ intent: "all", status: "all" });
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [mascotMode, setMascotMode] = useState("idle");
  const [mascotPose, setMascotPose] = useState({
    x: 0,
    y: 0,
    tilt: 0,
    ready: false,
  });
  const appShellRef = useRef(null);
  const questionInputRef = useRef(null);
  const answerBoxRef = useRef(null);
  const [settings, setSettings] = useState(() => {
    const cached = localStorage.getItem("legalqa-settings");
    return cached
      ? { ...DEFAULT_SETTINGS, ...JSON.parse(cached) }
      : DEFAULT_SETTINGS;
  });

  const latestEntry = history[0] ?? null;

  const clamp = useCallback(
    (value, min, max) => Math.min(Math.max(value, min), max),
    [],
  );

  const applyFilters = useMemo(
    () => filterHistory(history, filters.intent, filters.status),
    [history, filters],
  );

  const persistSettings = useCallback((next) => {
    setSettings(next);
    localStorage.setItem("legalqa-settings", JSON.stringify(next));
  }, []);

  const updateMascotPose = useCallback(
    (mode) => {
      if (typeof window === "undefined") return;

      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      const shellRect = appShellRef.current?.getBoundingClientRect() ?? null;
      const shellLeft = shellRect?.left ?? viewportWidth * 0.2;

      let x = shellLeft - 78;
      let y = 170;
      let targetX = viewportWidth * 0.5;
      let targetY = viewportHeight * 0.5;

      if (mode === "intro") {
        x = viewportWidth * 0.5;
        y = viewportHeight * 0.43;
      } else if (mode === "question" && questionInputRef.current) {
        const rect = questionInputRef.current.getBoundingClientRect();
        const isMobile = viewportWidth < 900;
        x = isMobile ? rect.left + rect.width * 0.5 : rect.left - 56;
        y = isMobile ? rect.top - 140 : rect.top + rect.height * 0.5 - 30;
        targetX = rect.left + rect.width * 0.5;
        targetY = rect.top + rect.height * 0.5;
      } else if (mode === "answer" && answerBoxRef.current) {
        const rect = answerBoxRef.current.getBoundingClientRect();
        const isMobile = viewportWidth < 900;
        x = isMobile ? rect.left + rect.width * 0.5 : rect.left - 56;
        y = isMobile ? rect.top - 130 : rect.top + rect.height * 0.7;
        targetX = rect.left + rect.width * 0.45;
        targetY = rect.top + rect.height * 0.7;
      }

      const safeX = clamp(x, 72, viewportWidth - 72);
      const safeY = clamp(y, 88, viewportHeight - 88);
      const deltaX = targetX - safeX;
      const deltaY = targetY - safeY;
      const tilt = clamp((deltaX * 0.02 + deltaY * 0.018) * -1, -16, 16);

      setMascotPose({ x: safeX, y: safeY, tilt, ready: true });
    },
    [clamp],
  );

  useEffect(() => {
    if (showIntro) {
      setMascotMode("intro");
      updateMascotPose("intro");
      return;
    }

    if (answerTyping) {
      setMascotMode("answer");
      updateMascotPose("answer");
      return;
    }

    if (question.trim() && !isLoading) {
      setMascotMode("question");
      updateMascotPose("question");
      return;
    }

    setMascotMode("idle");
    updateMascotPose("idle");
  }, [showIntro, answerTyping, question, isLoading, updateMascotPose]);

  useEffect(() => {
    if (showIntro) return undefined;
    const handleResize = () => updateMascotPose(mascotMode);
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [showIntro, mascotMode, updateMascotPose]);

  const handleSubmit = useCallback(async () => {
    if (!question.trim()) return;
    setIsLoading(true);
    setError("");

    const url = `${settings.apiBase}${settings.useDebugEndpoint ? "/ask/debug" : "/ask"}`;
    const payload = { question };

    try {
      const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!response.ok) throw new Error(`API trả về ${response.status}`);
      const data = await response.json();
      const entry = createHistoryEntry({ question, data });
      setHistory((prev) => [entry, ...prev]);
      setQuestion("");
    } catch (apiError) {
      console.error(apiError);
      setError(apiError.message || "Không thể kết nối API.");
    } finally {
      setIsLoading(false);
    }
  }, [question, settings]);

  return (
    <>
      <div
        className={`mascot-follower mode-${mascotMode} ${mascotPose.ready ? "ready" : ""}`}
        style={{
          "--mascot-x": `${mascotPose.x}px`,
          "--mascot-y": `${mascotPose.y}px`,
          "--mascot-tilt": `${mascotPose.tilt}deg`,
        }}
        aria-hidden="true"
      >
        <img src={mascotImage} alt="" />
      </div>

      {showIntro && (
        <div
          className="intro-overlay"
          role="button"
          tabIndex={0}
          onClick={() => setShowIntro(false)}
          onKeyDown={(event) => {
            if (event.key === "Enter" || event.key === " ") {
              setShowIntro(false);
            }
          }}
        >
          <div className="intro-content">
            <div className="intro-speech">
              Xin chào! Nhấn vào bất kỳ đâu để bắt đầu.
            </div>
            <p>Trợ lý pháp lý thông minh đã sẵn sàng hỗ trợ bạn.</p>
          </div>
        </div>
      )}

      <div
        ref={appShellRef}
        className={`app-shell ${showIntro ? "hidden" : "visible"}`}
      >
        <header className="app-header">
          <div className="app-header-content">
            <p className="eyebrow">Legal Knowledge Graph</p>
            <h1>Legal QA Console</h1>
            <p className="lede">
              Đặt câu hỏi tiếng Việt, theo dõi lịch sử truy vấn, và điều chỉnh
              endpoint Fuseki ngay trong một giao diện.
            </p>
          </div>
        </header>

        <main className="layout">
          <section className="panel tall">
            <QueryForm
              value={question}
              onChange={setQuestion}
              onSubmit={handleSubmit}
              loading={isLoading}
              textareaRef={questionInputRef}
            />
            <AnswerPanel
              entry={latestEntry}
              isLoading={isLoading}
              error={error}
              answerRef={answerBoxRef}
              onTypingChange={setAnswerTyping}
            />
          </section>
        </main>

        <button
          className="endpoint-toggle"
          aria-label="Cấu hình endpoint"
          title="Cấu hình endpoint"
          onClick={() => setDrawerOpen(true)}
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <circle
              cx="12"
              cy="12"
              r="3"
              stroke="currentColor"
              strokeWidth="1.5"
            />
            <circle
              cx="12"
              cy="12"
              r="7.5"
              stroke="currentColor"
              strokeWidth="1.2"
              strokeDasharray="2 2"
            />
            <path
              d="M4 12h2m12 0h2M12 4v2m0 12v2"
              stroke="currentColor"
              strokeWidth="1.2"
              strokeLinecap="round"
            />
          </svg>
        </button>

        <button
          className="history-toggle"
          aria-label="Mở lịch sử truy vấn"
          title="Mở lịch sử truy vấn"
          onClick={() => setHistoryOpen(true)}
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
          >
            <circle
              cx="12"
              cy="12"
              r="9"
              stroke="currentColor"
              strokeWidth="1.5"
            />
            <path
              d="M12 7v5l3 2"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </button>

        <div
          className={`history-drawer ${historyOpen ? "open" : ""}`}
          aria-hidden={!historyOpen}
        >
          <div
            className="history-drawer-backdrop"
            aria-hidden="true"
            onClick={() => setHistoryOpen(false)}
          />
          <div className="history-drawer-panel">
            <HistoryPanel
              history={applyFilters}
              rawHistory={history}
              filters={filters}
              onFiltersChange={setFilters}
              onReplay={(item) => {
                setQuestion(item.question);
                setHistoryOpen(false);
              }}
              onClose={() => setHistoryOpen(false)}
            />
          </div>
        </div>

        <EndpointDrawer
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
          settings={settings}
          onSave={persistSettings}
        />
      </div>
    </>
  );
}

export default App;
