import { useEffect, useRef } from "react";
import { useChat } from "../store/context";
import { Composer } from "./Composer";
import { MessageView } from "./MessageView";

export function Chat({ suggestions = [], title }: { suggestions?: string[]; title?: string }) {
  const messages = useChat((s) => s.messages);
  const streaming = useChat((s) => s.streaming);
  const error = useChat((s) => s.error);
  const notice = useChat((s) => s.notice);
  const disclaimer = useChat((s) => s.disclaimer);
  const send = useChat((s) => s.send);
  const stop = useChat((s) => s.stop);
  const logRef = useRef<HTMLDivElement>(null);
  const stick = useRef(true);

  useEffect(() => {
    const el = logRef.current;
    if (el && stick.current) el.scrollTo({ top: el.scrollHeight });
  }, [messages]);

  return (
    <div className="flex h-full min-w-0 flex-1 flex-col">
      <div
        ref={logRef}
        onScroll={(e) => {
          const el = e.currentTarget;
          stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
        }}
        role="log"
        aria-live="polite"
        aria-label="Conversation"
        className="flex-1 overflow-y-auto px-4 py-6"
      >
        <div className="mx-auto flex max-w-3xl flex-col gap-4">
          {messages.length === 0 && (
            <div className="mt-16 text-center">
              <h1 className="text-2xl font-semibold">{title ?? "How can I help?"}</h1>
              <div className="mt-6 flex flex-wrap justify-center gap-2">
                {suggestions.map((q) => (
                  <button
                    key={q}
                    onClick={() => send(q)}
                    className="rounded-full border border-neutral-300 px-3 py-1.5 text-sm hover:bg-neutral-100 dark:border-neutral-700 dark:hover:bg-neutral-800"
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((m) => (
            <MessageView key={m.id} message={m} />
          ))}
          {notice && <p className="text-sm text-amber-700 dark:text-amber-300">{notice}</p>}
          {error && (
            <p role="alert" className="rounded-lg border border-red-500/40 px-3 py-2 text-sm text-red-700 dark:text-red-300">
              {error}
            </p>
          )}
        </div>
      </div>
      <div className="border-t border-neutral-200 px-4 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3 dark:border-neutral-800">
        <div className="mx-auto max-w-3xl">
          <Composer streaming={streaming} onSend={send} onStop={stop} />
          {disclaimer && <p className="mt-2 text-center text-xs text-neutral-500">{disclaimer}</p>}
        </div>
      </div>
    </div>
  );
}
