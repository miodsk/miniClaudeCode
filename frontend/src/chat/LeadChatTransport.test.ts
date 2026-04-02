import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  LeadChatTransport,
  type ChatRequest,
  type FetchEventSourceFunction,
} from "./LeadChatTransport";

const live2d = {
  state: "speaking",
  emotion: "happy",
  motion: "smile03",
  expression: "happy",
} as const;

function createResponse(contentType = "text/event-stream") {
  return {
    ok: true,
    status: 200,
    headers: {
      get(name: string) {
        return name.toLowerCase() === "content-type" ? contentType : null;
      },
    },
  } as Response;
}

const request: ChatRequest = {
  sessionId: "sess_default",
  message: {
    id: "user-1",
    text: "你好",
  },
  trigger: "submit",
};

describe("LeadChatTransport", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("parses a POST SSE stream and assembles assistant text", async () => {
    const onDelta = vi.fn();
    const fetchEventSource = vi.fn(async (_input, init) => {
      await init?.onopen?.(createResponse());
      init?.onmessage?.({
        event: "start",
        data: JSON.stringify({
          session_id: "sess_default",
          assistant_message_id: "assistant-1",
          metadata: { live2d },
        }),
        id: "",
        retry: undefined,
      });
      init?.onmessage?.({
        event: "delta",
        data: JSON.stringify({
          assistant_message_id: "assistant-1",
          sequence: 1,
          text: "你好，",
        }),
        id: "",
        retry: undefined,
      });
      init?.onmessage?.({
        event: "state",
        data: JSON.stringify({
          assistant_message_id: "assistant-1",
          metadata: { live2d },
        }),
        id: "",
        retry: undefined,
      });
      init?.onmessage?.({
        event: "delta",
        data: JSON.stringify({
          assistant_message_id: "assistant-1",
          sequence: 2,
          text: "欢迎回来",
        }),
        id: "",
        retry: undefined,
      });
      init?.onmessage?.({
        event: "complete",
        data: JSON.stringify({
          assistant_message_id: "assistant-1",
          finish_reason: "stop",
          message: {
            id: "assistant-1",
            role: "assistant",
            content: "你好，欢迎回来",
            metadata: { live2d },
          },
        }),
        id: "",
        retry: undefined,
      });
    }) satisfies FetchEventSourceFunction;

    const transport = new LeadChatTransport({ fetchEventSource });
    const result = await transport.sendMessage(request, { onDelta });

    expect(fetchEventSource).toHaveBeenCalledWith(
      "/api/chat",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          session_id: request.sessionId,
          message: request.message,
          trigger: request.trigger,
        }),
      })
    );
    expect(onDelta).toHaveBeenNthCalledWith(1, {
      assistantMessageId: "assistant-1",
      text: "你好，",
      fullText: "你好，",
      metadata: live2d,
    });
    expect(onDelta).toHaveBeenNthCalledWith(2, {
      assistantMessageId: "assistant-1",
      text: "欢迎回来",
      fullText: "你好，欢迎回来",
      metadata: live2d,
    });
    expect(result).toEqual({
      assistantMessageId: "assistant-1",
      fullText: "你好，欢迎回来",
      metadata: { live2d },
    });
  });

  it("rejects malformed SSE payloads with a controlled error", async () => {
    const fetchEventSource = vi.fn(async (_input, init) => {
      await init?.onopen?.(createResponse());
      init?.onmessage?.({
        event: "delta",
        data: "{not-json}",
        id: "",
        retry: undefined,
      });
    }) satisfies FetchEventSourceFunction;

    const transport = new LeadChatTransport({ fetchEventSource });

    await expect(transport.sendMessage(request)).rejects.toThrow(
      "Failed to parse delta event payload"
    );
  });

  it("deduplicates repeated delta events by sequence", async () => {
    const fetchEventSource = vi.fn(async (_input, init) => {
      await init?.onopen?.(createResponse());
      init?.onmessage?.({
        event: "start",
        data: JSON.stringify({
          session_id: "sess_default",
          assistant_message_id: "assistant-1",
          metadata: { live2d },
        }),
        id: "",
        retry: undefined,
      });
      init?.onmessage?.({
        event: "delta",
        data: JSON.stringify({
          assistant_message_id: "assistant-1",
          sequence: 1,
          text: "一",
        }),
        id: "",
        retry: undefined,
      });
      init?.onmessage?.({
        event: "delta",
        data: JSON.stringify({
          assistant_message_id: "assistant-1",
          sequence: 1,
          text: "一",
        }),
        id: "",
        retry: undefined,
      });
      init?.onmessage?.({
        event: "delta",
        data: JSON.stringify({
          assistant_message_id: "assistant-1",
          sequence: 2,
          text: "二",
        }),
        id: "",
        retry: undefined,
      });
      init?.onmessage?.({
        event: "complete",
        data: JSON.stringify({
          assistant_message_id: "assistant-1",
          finish_reason: "stop",
          message: {
            id: "assistant-1",
            role: "assistant",
            content: "一二",
            metadata: { live2d },
          },
        }),
        id: "",
        retry: undefined,
      });
    }) satisfies FetchEventSourceFunction;

    const transport = new LeadChatTransport({ fetchEventSource });
    const result = await transport.sendMessage(request);

    expect(result.fullText).toBe("一二");
  });
});
