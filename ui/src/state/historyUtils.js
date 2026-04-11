const friendlyStatus = (entry) => {
  if (!entry?.data) return "error";
  if (entry.data.success) return "ok";
  if (entry.data.message === "NO_RESULT") return "empty";
  if (entry.data.message === "FUSEKI_ERROR") return "error";
  return "warn";
};

export const createHistoryEntry = ({ question, data }) => ({
  id: crypto.randomUUID(),
  question,
  timestamp: new Date().toISOString(),
  intent: data.intent ?? "UNKNOWN",
  endpoint: data.endpoint ?? "",
  sparql: data.sparql ?? "",
  answer: data.answer ?? "",
  data,
  status: friendlyStatus({ data }),
});

export const filterHistory = (history, intentFilter, statusFilter) =>
  history.filter((item) => {
    const intentOk = intentFilter === "all" || item.intent === intentFilter;
    const statusOk = statusFilter === "all" || item.status === statusFilter;
    return intentOk && statusOk;
  });

export const distinctIntents = (history) => {
  const intents = new Set(history.map((item) => item.intent));
  return Array.from(intents);
};
