import { createContext, useContext, type ReactNode } from "react";
import { useStore } from "zustand";
import type { ChatStore } from "./chat";

type State = ReturnType<ChatStore["getState"]>;
const Ctx = createContext<ChatStore | null>(null);

export function ChatProvider({ store, children }: { store: ChatStore; children: ReactNode }) {
    return <Ctx.Provider value={ store }> { children } </Ctx.Provider>;
}

export function useChat<T>(selector: (s: State) => T): T {
    const store = useContext(Ctx);
    if (!store) throw new Error("useChat must be used inside <ChatProvider>");
    return useStore(store, selector);
}
