import { useMemo, useState } from "react";
import { Chat } from "./components/Chat";
import { Sidebar } from "./components/Sidebar";
import { demoApi, type ChatApi } from "./lib/api";
import { createChatStore } from "./store/chat";
import { ChatProvider } from "./store/context";

const SUGGESTIONS = [
    "What time is it in Asia/Kolkata?",
    "List my notes and read note 3",
    "Run whoami",
    "What is (12 + 8) * 3 ** 2?",
];

/** Pass a custom `api` (e.g. Authorization Bearer headers) to embed this UI in another app. */
export default function App({ api = demoApi }: { api?: ChatApi }) {
    const store = useMemo(() => createChatStore(api), [api]);
    const [open, setOpen] = useState(false);
    return (
        <ChatProvider store={store}>
            <div className="relative flex h-full flex-col bg-white text-neutral-900 dark:bg-neutral-950 dark:text-neutral-100">
                <header className="flex items-center gap-2 border-b border-neutral-200 px-3 py-2 pt-[max(0.5rem,env(safe-area-inset-top))] dark:border-neutral-800">
                    <button aria-label="Toggle sidebar" onClick={() => setOpen((o) => !o)} className="rounded px-2 py-1 md:hidden">
                        ☰
                    </button>
                    <span className="font-semibold">Agent Platform</span>
                </header>
                <div className="relative flex min-h-0 flex-1">
                    <Sidebar open={open} onClose={() => setOpen(false)} />
                    <Chat suggestions={SUGGESTIONS} />
                </div>
            </div>
        </ChatProvider>
    );
}
