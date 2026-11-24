import { useRef, useState, type KeyboardEvent } from "react";

interface Props {
  streaming: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
  maxLength?: number;
}

export function Composer({ streaming, onSend, onStop, maxLength = 2000 }: Props) {
  const [text, setText] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);

  const submit = () => {
    if (!text.trim() || streaming) return;
    onSend(text);
    setText("");
    if (ref.current) ref.current.style.height = "auto";
  };
  const onKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="flex items-end gap-2">
      <textarea
        ref={ref}
        aria-label="Message"
        rows={1}
        value={text}
        maxLength={maxLength}
        placeholder="Ask something (Enter to send, Shift+Enter for a new line)"
        onChange={(e) => {
          setText(e.target.value);
          e.target.style.height = "auto";
          e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
        }}
        onKeyDown={onKey}
        className="max-h-40 min-h-11 flex-1 resize-none rounded-xl border border-neutral-300 bg-transparent px-3 py-2.5 outline-none focus:border-blue-500 dark:border-neutral-700"
      />
      {streaming ? (
        <button onClick={onStop} className="h-11 rounded-xl bg-neutral-700 px-4 text-white hover:bg-neutral-600">
          Stop
        </button>
      ) : (
        <button
          onClick={submit}
          disabled={!text.trim()}
          className="h-11 rounded-xl bg-blue-600 px-4 text-white hover:bg-blue-500 disabled:opacity-40"
        >
          Send
        </button>
      )}
    </div>
  );
}
