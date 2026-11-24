import { useChat } from "../store/context";

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const conversations = useChat((s) => s.conversations);
  const activeId = useChat((s) => s.activeId);
  const streaming = useChat((s) => s.streaming);
  const newChat = useChat((s) => s.newChat);
  const selectChat = useChat((s) => s.selectChat);
  const deleteChat = useChat((s) => s.deleteChat);

  return (
    <aside
      aria-label="Conversations"
      className={`${open ? "flex" : "hidden"} absolute inset-y-0 left-0 z-10 w-72 flex-col border-r border-neutral-200 bg-neutral-50 p-2 md:static md:flex dark:border-neutral-800 dark:bg-neutral-900`}
    >
      <button
        onClick={() => {
          newChat();
          onClose();
        }}
        disabled={streaming}
        className="mb-2 rounded-lg bg-blue-600 px-3 py-2 text-left text-white hover:bg-blue-500 disabled:opacity-50"
      >
        + New chat
      </button>
      <nav className="flex-1 space-y-0.5 overflow-y-auto">
        {conversations.map((c) => (
          <div
            key={c.id}
            className={`group flex items-center rounded-lg ${
              c.id === activeId ? "bg-neutral-200 dark:bg-neutral-800" : "hover:bg-neutral-100 dark:hover:bg-neutral-800/60"
            }`}
          >
            <button
              onClick={() => {
                void selectChat(c.id);
                onClose();
              }}
              className="min-w-0 flex-1 truncate px-3 py-2 text-left text-sm"
            >
              {c.title}
            </button>
            <button
              aria-label={`Delete ${c.title}`}
              onClick={() => deleteChat(c.id)}
              className="px-2 text-neutral-500 opacity-0 hover:text-red-600 focus:opacity-100 group-hover:opacity-100"
            >
              ×
            </button>
          </div>
        ))}
        {conversations.length === 0 && <p className="px-3 py-2 text-sm text-neutral-500">No chats yet</p>}
      </nav>
    </aside>
  );
}
