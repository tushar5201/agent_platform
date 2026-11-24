import { parseSSE, type ChatEvent } from "./sse";

export interface ChatApi {
    /** Headers added to every request. Demo: a session id. Real app: Authorization Bearer. */
    getHeaders: () => Record<string, string>;
    baseUrl?: string;
}

export class ApiError extends Error {
    constructor(
        public status: number,
        message: string,
    ) {
        super(message);
    }
}

export function newId(): string {
    const c = globalThis.crypto;
    return (c?.randomUUID ? c.randomUUID() : `${Date.now()}${Math.random().toString(16).slice(2)}`)
        .replaceAll("-", "")
        .slice(0, 32);
}

/** Demo auth: anonymous per-browser session. Only works when the server runs in demo mode. */
export const demoApi: ChatApi = {
    getHeaders() {
        let sid = localStorage.getItem("ap.session");
        if (!sid) {
            sid = newId();
            localStorage.setItem("ap.session", sid);
        }
        return { "X-Demo-Session": sid };
    },
};

async function failure(res: Response): Promise<ApiError> {
    let detail = `Request failed (${res.status})`;
    try {
        const body = await res.json();
        if (typeof body?.detail === "string") detail = body.detail;
    } catch {
        /* keep default */
    }
    return new ApiError(res.status, detail);
}

export async function* streamChat(
    api: ChatApi,
    message: string,
    conversationId: string,
    signal?: AbortSignal,
): AsyncGenerator<ChatEvent> {
    const res = await fetch(`${api.baseUrl ?? ""}/v1/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...api.getHeaders() },
        body: JSON.stringify({ message, conversation_id: conversationId }),
        signal,
    });
    if (!res.ok) throw await failure(res);
    if (!res.body) throw new ApiError(500, "Empty response");
    yield* parseSSE(res.body);
}

export interface HistoryItem {
    role: "user" | "assistant";
    text: string;
}

export async function fetchHistory(api: ChatApi, conversationId: string): Promise<HistoryItem[]> {
    const res = await fetch(`${api.baseUrl ?? ""}/v1/chat/${conversationId}/history`, {
        headers: api.getHeaders(),
    });
    if (!res.ok) throw await failure(res);
    return (await res.json()).messages as HistoryItem[];
}
