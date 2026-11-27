"use client";
import { Task } from "@/types";
import { FileText, CircleDashed } from "lucide-react";

export default function ReportPanel({
  task, sourceTasks, mode,
}: { task: Task | null; sourceTasks: Task[]; mode: string | null }) {
  const reporterTask = task?.result ? task : null;
  const isFallbackTask = (item: Task) =>
    Boolean(
      item.result?.startsWith("[Deterministic demo]") ||
      item.explanation?.startsWith("Deterministic fallback"),
    );
  const hasFallbackOutput = Boolean(reporterTask && isFallbackTask(reporterTask));
  const hasFallbackInput = sourceTasks.some((item) => item.id !== task?.id && isFallbackTask(item));
  const hasOutput = mode === "llm" && reporterTask !== null && !hasFallbackOutput && !hasFallbackInput;
  const statusLabel = mode === null
    ? "Connecting"
    : mode === "unavailable"
      ? "Connection unavailable"
      : mode !== "llm"
        ? "AI model not connected"
        : task?.status === "failed"
          ? "Report failed"
          : hasFallbackOutput || hasFallbackInput
            ? "AI result unavailable"
            : hasOutput && task?.status === "running"
              ? "Awaiting approval"
              : hasOutput
                ? "Approved"
                : "In progress";

  const emptyMessage = mode === null
    ? "Connecting to the AI service..."
    : mode === "unavailable"
      ? "The backend could not be reached. Start the backend and try again."
      : mode !== "llm"
        ? "A detailed model-generated result is not available yet. Add OPENAI_API_KEY to backend/.env, restart the backend, then start a new session."
        : hasFallbackOutput || hasFallbackInput
          ? "The model did not return a usable result for this session. Check the API key, model name, and backend logs, then start a new session."
          : task?.status === "failed"
            ? task.result || "The report task failed. Inspect the task details for more information."
            : "The detailed result will appear here when the reporter task completes.";

  return (
    <section className="result-panel paper-panel" aria-labelledby="result-heading" id="result">
      <header className="result-heading">
        <div>
          <span className="section-kicker">WORKFLOW OUTPUT</span>
          <h2 id="result-heading"><FileText size={18} /> Final result</h2>
        </div>
        <span className={`result-state ${hasOutput ? "is-ready" : ""}`}>
          <i />{statusLabel}
        </span>
      </header>

      {reporterTask && hasOutput ? (
        <div className="result-content">
          <div className="result-text">{reporterTask.result}</div>
          {reporterTask.explanation && (
            <div className="result-explanation">
              <strong>How I reached this</strong>
              <p>{reporterTask.explanation}</p>
            </div>
          )}
          <div className="result-evidence">
            <strong>Inputs and evidence</strong>
            {reporterTask.evidence && reporterTask.evidence.length > 0 ? (
              <ul>
                {reporterTask.evidence.map((item, index) => (
                  <li key={`${reporterTask.id}-evidence-${index}`}>
                    {typeof item === "string" ? item : (
                      <>
                        <b>{item.title || item.document_id || "Evidence item"}</b>
                        {item.status && <span className="evidence-status">{item.status}</span>}
                        {item.excerpt && <p>{item.excerpt}</p>}
                        {item.url && <a href={item.url} target="_blank" rel="noreferrer">{item.url}</a>}
                      </>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No source items were provided to the reporter.</p>
            )}
          </div>
          <div className="result-limitation">
            <strong>Confidence and limitations</strong>
            {reporterTask.uncertainty && <p>Uncertainty: {reporterTask.uncertainty}</p>}
            {reporterTask.limitations && <p>{reporterTask.limitations}</p>}
          </div>
        </div>
      ) : (
        <div className="result-empty">
          <CircleDashed size={19} />
          <span>{emptyMessage}</span>
        </div>
      )}
    </section>
  );
}
