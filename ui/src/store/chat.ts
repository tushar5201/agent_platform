import { create } from "zustand";
import { ApiError, fetchHistory, newId, streamChat, type ChatApi } from "../lib/api";

export interface ToolCall {
    name: string;
    args: string;
    status: "running" | "ok" | "failed";
}
export interface Message {
    id: string;
    role: "user" | "assistant";
    text: string;
    tools: ToolCall[];
    pending?: boolean;
}
export interface Conversation {
    id: string;
    title: string;
    updatedAt: number;
}

interface State {
    conversations: Conversation[];
    activeId: string | null;
    messages: Message[];
    streaming: boolean;
    error: string | null;
    notice: string | null;
    disclaimer: string | null;
    newChat: () => void;
    selectChat: (id: string) => Promise<void>;
    send: (text: string) => Promise<void>;
    stop: () => void;
    deleteChat: (id: string) => void;
}

const KEY = "ap.conversations";
const load = (): Conversation[] => {
    try {
        return JSON.parse(localStorage.getItem(KEY) ?? "[]") as Conversation[];
    } catch {
        return [];
    }
};
const save = (c: Conversation[]) => localStorage.setItem(KEY, JSON.stringify(c.slice(0, 50)));

export function createChatStore(api: ChatApi) {
    let controller: AbortController | null = null;

    return create<State>((set, get) => {
        const patchLast = (fn: (m: Message) => Message) =>
            set((s) => ({ messages: s.messages.map((m, i) => (i === s.messages.length - 1 ? fn(m) : m)) }));

        const touch = (id: string, title?: string) =>
            set((s) => {
                const existing = s.conversations.find((c) => c.id === id);
                const next = [
                    { id, title: existing?.title ?? title ?? "New chat", updatedAt: Date.now() },
                    ...s.conversations.filter((c) => c.id !== id),
                ];
                save(next);
                return { conversations: next };
            });

        return {
            conversations: load(),
            activeId: null,
            messages: [],
            streaming: false,
            error: null,
            notice: null,
            disclaimer: null,

            newChat() {
                if (get().streaming) return;
                set({ activeId: null, messages: [], error: null, notice: null });
            },

            async selectChat(id) {
                if (get().streaming) return;
                set({ activeId: id, messages: [], error: null, notice: null });
                try {
                    const items = await fetchHistory(api, id);
                    if (get().activeId !== id) return;
                    set({ messages: items.map((m) => ({ id: newId(), role: m.role, text: m.text, tools: [] })) });
                } catch (e) {
                    if (get().activeId === id)
                        set({ error: e instanceof ApiError ? e.message : "Could not load this chat." });
                }
            },

            deleteChat(id) {
                const conversations = get().conversations.filter((c) => c.id !== id);
                save(conversations);
                set({ conversations });
                if (get().activeId === id) get().newChat();
            },

            stop() {
                controller?.abort();
            },

            async send(raw) {
                const text = raw.trim();
                if (!text || get().streaming) return;
                const id = get().activeId ?? newId();
                controller = new AbortController();
                set((s) => ({
                    activeId: id,
                    streaming: true,
                    error: null,
                    notice: null,
                    messages: [
                        ...s.messages,
                        { id: newId(), role: "user", text, tools: [] },
                        { id: newId(), role: "assistant", text: "", tools: [], pending: true },
                    ],
                }));
                touch(id, text.slice(0, 48));
                try {
                    for await (const ev of streamChat(api, text, id, controller.signal)) {
                        if (ev.event === "token") patchLast((m) => ({ ...m, text: m.text + ev.data.text }));
                        else if (ev.event === "tool_start")
                            patchLast((m) => ({
                                ...m,
                                tools: [...m.tools, { name: ev.data.name, args: ev.data.args, status: "running" }],
                            }));
                        else if (ev.event === "tool_end")
                            patchLast((m) => {
                                const idx = m.tools.findLastIndex((t) => t.name === ev.data.name && t.status === "running");
                                const tools = m.tools.map((t, i) =>
                                    i === idx ? { ...t, status: ev.data.ok ? ("ok" as const) : ("failed" as const) } : t,
                                );
                                return { ...m, tools };
                            });
                        else if (ev.event === "notice")
                            set({ notice: `Tool servers unavailable: ${ev.data.unavailable_tool_servers.join(", ")}` });
                        else if (ev.event === "done") set({ disclaimer: ev.data.disclaimer });
                        else if (ev.event === "error") set({ error: ev.data.message });
                    }
                } catch (e) {
                    if ((e as Error).name !== "AbortError")
                        set({ error: e instanceof ApiError ? e.message : "Network error. Please retry." });
                } finally {
                    controller = null;
                    set((s) => {
                        const last = s.messages[s.messages.length - 1];
                        const dropEmpty = last && last.role === "assistant" && !last.text && last.tools.length === 0;
                        const messages = (dropEmpty ? s.messages.slice(0, -1) : s.messages).map((m) =>
                            m.pending ? { ...m, pending: false } : m,
                        );
                        return { streaming: false, messages };
                    });
                    touch(id);
                }
            },
        };
    });
}

export type ChatStore = ReturnType<typeof createChatStore>;
