// @vitest-environment jsdom

import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { LeadChatTransport } from "./LeadChatTransport";
import { useLeadChat } from "./useLeadChat";

const restoredLive2d = {
  state: "idle",
  emotion: "neutral",
  motion: "idle01",
  expression: "neutral",
} as const;

describe("useLeadChat", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("restores the backend session on mount", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        Response.json({
          session_id: "sess_restored",
          messages: [
            { id: "user-1", role: "user", content: "你好" },
            {
              id: "assistant-1",
              role: "assistant",
              content: "欢迎回来",
              metadata: { live2d: restoredLive2d },
            },
          ],
          metadata: {
            last_live2d: restoredLive2d,
          },
        })
      )
    );

    const { result } = renderHook(() => useLeadChat());

    await waitFor(() => {
      expect(result.current.messages).toHaveLength(2);
    });

    expect(result.current.messages[1]).toMatchObject({
      id: "assistant-1",
      metadata: restoredLive2d,
    });
    expect(result.current.live2dState).toEqual(restoredLive2d);
  });

  it("sends the latest user message and streams assistant updates", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
        const url = String(input);
        if (url.endsWith("/api/session")) {
          return Response.json({
            session_id: "sess_default",
            messages: [],
            metadata: {},
          });
        }

        if (url.endsWith("/api/reset") && init?.method === "POST") {
          return Response.json({ status: "reset" });
        }

        throw new Error(`Unexpected fetch call: ${url}`);
      })
    );

    const sendMessage = vi
      .spyOn(LeadChatTransport.prototype, "sendMessage")
      .mockImplementation(async (_request, handlers) => {
        handlers?.onStart?.({
          sessionId: "sess_default",
          assistantMessageId: "assistant-1",
          metadata: restoredLive2d,
        });
        handlers?.onDelta?.({
          assistantMessageId: "assistant-1",
          text: "你好，",
          fullText: "你好，",
          metadata: restoredLive2d,
        });
        handlers?.onDelta?.({
          assistantMessageId: "assistant-1",
          text: "欢迎回来",
          fullText: "你好，欢迎回来",
          metadata: restoredLive2d,
        });
        handlers?.onComplete?.({
          assistantMessageId: "assistant-1",
          fullText: "你好，欢迎回来",
          metadata: { live2d: restoredLive2d },
        });
        return {
          assistantMessageId: "assistant-1",
          fullText: "你好，欢迎回来",
          metadata: { live2d: restoredLive2d },
        };
      });

    const { result } = renderHook(() => useLeadChat());

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    await act(async () => {
      await result.current.sendMessage("你好");
    });

    expect(sendMessage).toHaveBeenCalledTimes(1);
    expect(result.current.messages).toEqual([
      expect.objectContaining({ role: "user", content: "你好" }),
      expect.objectContaining({
        id: "assistant-1",
        role: "assistant",
        content: "你好，欢迎回来",
        metadata: restoredLive2d,
      }),
    ]);
    expect(result.current.live2dState).toEqual(restoredLive2d);
  });
});
