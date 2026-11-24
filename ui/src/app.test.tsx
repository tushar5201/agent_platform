import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import type { ChatApi } from "./lib/api";

const api: ChatApi = { getHeaders: () => ({ Authorization: "Bearer test-token" }) };

function sseResponse(events: [string, unknown][], status = 200) {
    const enc = new TextEncoder();
    const body = new ReadableStream<Uint8Array>({
        start(c) {
            for (const [e, d] of events) c.enqueue(enc.encode(`event: ${e}\ndata: ${JSON.stringify(d)}\n\n`));
            c.close();
        },
    });
    return new Response(body, { status, headers: { "Content-Type": "text/event-stream" } });
}

const fetchMock = vi.fn();
beforeEach(() => {
    fetchMock.mockReset();
    vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => vi.unstubAllGlobals());

const type = async (text: string) => {
    await userEvent.type(screen.getByLabelText("Message"), text);
    await userEvent.click(screen.getByRole("button", { name: "Send" }));
};

describe("chat UI", () => {
    it("streams an answer with a tool chip, sends auth headers, and shows the disclaimer", async () => {
        fetchMock.mockResolvedValueOnce(
            sseResponse([
                ["tool_start", { name: "demo_get_time", args: '{"tz":"UTC"}' }],
                ["tool_end", { name: "demo_get_time", ok: true }],
                ["token", { text: "It is **noon**." }],
                ["done", { conversation_id: "x", disclaimer: "Explains data only." }],
            ]),
        );
        render(<App api={api} />);
        await type("time?");

        expect(await screen.findByText("noon")).toBeInTheDocument();
        expect(screen.getByText("noon").tagName).toBe("STRONG");
        const chip = screen.getByTestId("tool-chip");
        expect(chip).toHaveTextContent("get_time");
        expect(chip).toHaveTextContent("ok");
        expect(await screen.findByText("Explains data only.")).toBeInTheDocument();

        const [url, init] = fetchMock.mock.calls[0]!;
        expect(url).toBe("/v1/chat");
        expect(init.headers).toMatchObject({ Authorization: "Bearer test-token", "Content-Type": "application/json" });
        const body = JSON.parse(init.body);
        expect(body.message).toBe("time?");
        expect(body.conversation_id).toMatch(/^[A-Za-z0-9_-]{1,64}$/);
    });

    it("shows the server's error detail for HTTP errors (e.g. daily cap)", async () => {
        fetchMock.mockResolvedValueOnce(
            new Response(JSON.stringify({ detail: "Daily chat limit reached." }), { status: 429 }),
        );
        render(<App api={api} />);
        await type("hi");
        expect(await screen.findByRole("alert")).toHaveTextContent("Daily chat limit reached.");
        expect(screen.queryByTestId("tool-chip")).not.toBeInTheDocument();
    });

    it("renders model output as markdown without executing raw HTML", async () => {
        fetchMock.mockResolvedValueOnce(
            sseResponse([["token", { text: '<img src=x onerror="alert(1)"> [a](https://e.com)' }], ["done", { conversation_id: "x", disclaimer: "d" }]]),
        );
        const { container } = render(<App api={api} />);
        await type("xss");
        await screen.findByRole("link", { name: "a" });
        expect(container.querySelector("img")).toBeNull();
    });

    it("suggestion chips send a message; sidebar lists the chat and reloads history", async () => {
        fetchMock.mockResolvedValueOnce(sseResponse([["token", { text: "Done" }], ["done", { conversation_id: "x", disclaimer: "d" }]]));
        render(<App api={api} />);
        await userEvent.click(screen.getByRole("button", { name: "Run whoami" }));
        await screen.findByText("Done");
        expect(screen.getByRole("navigation")).toHaveTextContent("Run whoami");

        fetchMock.mockResolvedValueOnce(
            new Response(JSON.stringify({ messages: [{ role: "user", text: "old q" }, { role: "assistant", text: "old a" }] })),
        );
        await userEvent.click(screen.getByRole("button", { name: "+ New chat" }));
        expect(screen.queryByText("Done")).not.toBeInTheDocument();
        await userEvent.click(within(screen.getByRole("navigation")).getByRole("button", { name: "Run whoami" }));
        expect(await screen.findByText("old a")).toBeInTheDocument();
        expect(fetchMock.mock.calls[1]![0]).toMatch(/^\/v1\/chat\/[A-Za-z0-9]+\/history$/);
    });

    it("Stop aborts the stream and keeps the partial text", async () => {
        const enc = new TextEncoder();
        let ctrl!: ReadableStreamDefaultController<Uint8Array>;
        fetchMock.mockImplementationOnce((_u: string, init: RequestInit) => {
            const body = new ReadableStream<Uint8Array>({ start: (c) => (ctrl = c) });
            init.signal!.addEventListener("abort", () => ctrl.error(new DOMException("aborted", "AbortError")));
            ctrl.enqueue(enc.encode('event: token\ndata: {"text":"partial"}\n\n'));
            return Promise.resolve(new Response(body));
        });
        render(<App api={api} />);
        await type("long");
        await screen.findByText("partial");
        await userEvent.click(screen.getByRole("button", { name: "Stop" }));
        await waitFor(() => expect(screen.getByRole("button", { name: "Send" })).toBeInTheDocument());
        expect(screen.getByText("partial")).toBeInTheDocument();
        expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    });
});
