import { parseSSE, type ChatEvent } from "./sse";

function streamOf(chunks: string[]) {
    const enc = new TextEncoder();
    return new ReadableStream<Uint8Array>({
        start(c) {
            chunks.forEach((x) => c.enqueue(enc.encode(x)));
            c.close();
        },
    });
}
async function collect(chunks: string[]) {
    const out: ChatEvent[] = [];
    for await (const ev of parseSSE(streamOf(chunks))) out.push(ev);
    return out;
}

describe("parseSSE", () => {
    it("parses multiple events", async () => {
        const out = await collect(['event: token\ndata: {"text":"a"}\n\nevent: done\ndata: {"conversation_id":"c","disclaimer":"d"}\n\n']);
        expect(out.map((e) => e.event)).toEqual(["token", "done"]);
    });

    it("handles an event split across chunks, even mid-JSON and mid-separator", async () => {
        const out = await collect(['event: tok', 'en\ndata: {"te', 'xt":"hi"}\n', "\n"]);
        expect(out).toEqual([{ event: "token", data: { text: "hi" } }]);
    });

    it("handles CRLF and keeps unicode intact", async () => {
        const out = await collect(['event: token\r\ndata: {"text":"₹ 100 ✓"}\r\n\r\n']);
        expect(out).toEqual([{ event: "token", data: { text: "₹ 100 ✓" } }]);
    });

    it("skips malformed blocks instead of throwing", async () => {
        const out = await collect(["event: token\ndata: {oops\n\n", 'event: token\ndata: {"text":"ok"}\n\n']);
        expect(out).toEqual([{ event: "token", data: { text: "ok" } }]);
    });
});
