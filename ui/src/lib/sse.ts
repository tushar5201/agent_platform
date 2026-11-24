export type ChatEvent =
    | { event: "token"; data: { text: string } }
    | { event: "tool_start"; data: { name: string; args: string } }
    | { event: "tool_end"; data: { name: string; ok: boolean } }
    | { event: "notice"; data: { unavailable_tool_servers: string[] } }
    | { event: "done"; data: { conversation_id: string; disclaimer: string } }
    | { event: "error"; data: { message: string } };

/** Parse a fetch body (text/event-stream) into typed events. Handles split chunks and CRLF. */
export async function* parseSSE(stream: ReadableStream<Uint8Array>): AsyncGenerator<ChatEvent> {
    const reader = stream.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    try {
        for (; ;) {
            const { done, value } = await reader.read();
            if (done) break;
            buf += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
            let i: number;
            while ((i = buf.indexOf("\n\n")) >= 0) {
                const block = buf.slice(0, i);
                buf = buf.slice(i + 2);
                const ev = decodeBlock(block);
                if (ev) yield ev;
            }
        }
    } finally {
        reader.releaseLock();
    }
}

function decodeBlock(block: string): ChatEvent | null {
    let event = "";
    const data: string[] = [];
    for (const line of block.split("\n")) {
        if (line.startsWith("event:")) event = line.slice(6).trim();
        else if (line.startsWith("data:")) data.push(line.slice(5).trim());
    }
    if (!event || data.length === 0) return null;
    try {
        return { event, data: JSON.parse(data.join("\n")) } as ChatEvent;
    } catch {
        return null;
    }
}
