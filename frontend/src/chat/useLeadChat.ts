import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  LeadChatTransport,
  type ChatRequest,
  type Live2DMeta,
  type SSEStreamResult,
} from "./LeadChatTransport";

export type LeadChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  metadata?: Live2DMeta;
};

interface SessionResponse {
  session_id: string;
  messages: Array<{
    id: string;
    role: "user" | "assistant";
    content: string;
    metadata?: {
      live2d?: Live2DMeta;
    };
  }>;
  metadata?: {
    last_live2d?: Live2DMeta;
  };
}

const DEFAULT_SESSION_ID = "sess_default";

function createMessageId() {
  return globalThis.crypto?.randomUUID?.() ?? `msg-${Date.now()}`;
}

function toMessage(
  message: SessionResponse["messages"][number]
): LeadChatMessage {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    metadata: message.metadata?.live2d,
  };
}

async function fetchJson<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  const response = await fetch(input, init);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

function upsertAssistantMessage(
  messages: LeadChatMessage[],
  message: LeadChatMessage
): LeadChatMessage[] {
  const index = messages.findIndex((candidate) => candidate.id === message.id);
  if (index === -1) {
    return [...messages, message];
  }

  return messages.map((candidate, candidateIndex) =>
    candidateIndex === index ? { ...candidate, ...message } : candidate
  );
}

export function useLeadChat() {
  const [messages, setMessages] = useState<LeadChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [live2dState, setLive2dState] = useState<Live2DMeta | null>(null);
  const [sessionId, setSessionId] = useState(DEFAULT_SESSION_ID);
  const transport = useMemo(() => new LeadChatTransport(), []);
  const mountedRef = useRef(true);

  const syncSession = useCallback(async () => {
    const session = await fetchJson<SessionResponse>("/api/session");
    if (!mountedRef.current) {
      return;
    }

    setSessionId(session.session_id || DEFAULT_SESSION_ID);
    setMessages(session.messages.map(toMessage));
    setLive2dState(session.metadata?.last_live2d ?? null);
  }, []);

  useEffect(() => {
    mountedRef.current = true;

    void syncSession().catch((caughtError: unknown) => {
      if (!mountedRef.current) {
        return;
      }

      setError(caughtError instanceof Error ? caughtError.message : "Failed to load session");
    });

    return () => {
      mountedRef.current = false;
      transport.cancel();
    };
  }, [syncSession, transport]);

  const sendMessage = useCallback(
    async (text: string) => {
      const trimmedText = text.trim();
      if (!trimmedText) {
        return;
      }

      setError(null);
      setIsLoading(true);

      const userMessageId = createMessageId();
      const userMessage: LeadChatMessage = {
        id: userMessageId,
        role: "user",
        content: trimmedText,
      };

      setMessages((currentMessages) => [...currentMessages, userMessage]);

      const request: ChatRequest = {
        sessionId,
        message: {
          id: userMessageId,
          text: trimmedText,
        },
        trigger: "submit",
      };

      try {
        const result = await transport.sendMessage(request, {
          onStart: (payload) => {
            setSessionId(payload.sessionId || DEFAULT_SESSION_ID);
            if (payload.metadata) {
              setLive2dState(payload.metadata);
            }
            setMessages((currentMessages) =>
              upsertAssistantMessage(currentMessages, {
                id: payload.assistantMessageId,
                role: "assistant",
                content: "",
                metadata: payload.metadata ?? undefined,
              })
            );
          },
          onState: (nextLive2d) => {
            setLive2dState(nextLive2d);
          },
          onDelta: (payload) => {
            setLive2dState(payload.metadata);
            setMessages((currentMessages) =>
              upsertAssistantMessage(currentMessages, {
                id: payload.assistantMessageId,
                role: "assistant",
                content: payload.fullText,
                metadata: payload.metadata ?? undefined,
              })
            );
          },
          onComplete: (streamResult) => {
            setLive2dState(streamResult.metadata.live2d);
            setMessages((currentMessages) =>
              upsertAssistantMessage(currentMessages, {
                id: streamResult.assistantMessageId,
                role: "assistant",
                content: streamResult.fullText,
                metadata: streamResult.metadata.live2d ?? undefined,
              })
            );
          },
        });

        return result;
      } catch (caughtError) {
        const nextError =
          caughtError instanceof Error ? caughtError.message : "Failed to send message";
        setError(nextError);
        throw caughtError;
      } finally {
        if (mountedRef.current) {
          setIsLoading(false);
        }
      }
    },
    [sessionId, transport]
  );

  const resetChat = useCallback(async () => {
    setError(null);
    transport.cancel();
    await fetchJson<{ status: string }>("/api/reset", { method: "POST" });
    if (!mountedRef.current) {
      return;
    }

    setSessionId(DEFAULT_SESSION_ID);
    setMessages([]);
    setLive2dState(null);
    setIsLoading(false);
  }, [transport]);

  return {
    messages,
    isLoading,
    error,
    live2dState,
    sendMessage,
    resetChat,
    reloadSession: syncSession,
  } as const;
}

export type { Live2DMeta, SSEStreamResult };
