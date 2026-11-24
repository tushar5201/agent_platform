import Markdown from "react-markdown";
import type { Message, ToolCall } from "../store/chat";

const label = (name: string) => name.replace(/^[a-z0-9]+_/, "");

function ToolChip({ tool }: { tool: ToolCall }) {
  const style = {
    running: "border-amber-400/60 text-amber-700 dark:text-amber-300",
    ok: "border-emerald-500/50 text-emerald-700 dark:text-emerald-300",
    failed: "border-red-500/50 text-red-700 dark:text-red-300",
  }[tool.status];
  const icon = { running: "…", ok: "✓", failed: "✗" }[tool.status];
  return (
    <span
      title={tool.args}
      data-testid="tool-chip"
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-mono text-xs ${style}`}
    >
      <span aria-hidden>{icon}</span>
      {label(tool.name)}
      <span className="sr-only">{tool.status}</span>
    </span>
  );
}

export function MessageView({ message }: { message: Message }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-2xl rounded-br-sm bg-blue-600 px-4 py-2 text-white">
          {message.text}
        </div>
      </div>
    );
  }
  return (
    <div className="flex flex-col items-start gap-2">
      {message.tools.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {message.tools.map((t, i) => (
            <ToolChip key={i} tool={t} />
          ))}
        </div>
      )}
      {(message.text || message.pending) && (
        <div
          className={`md max-w-[85%] rounded-2xl rounded-bl-sm bg-neutral-100 px-4 py-2 dark:bg-neutral-800 ${
            message.pending ? "cursor" : ""
          }`}
        >
          <Markdown>{message.text}</Markdown>
        </div>
      )}
    </div>
  );
}
