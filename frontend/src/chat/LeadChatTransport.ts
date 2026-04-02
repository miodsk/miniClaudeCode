import {
  EventStreamContentType,
  fetchEventSource,
  type EventSourceMessage,
  type FetchEventSourceInit,
} from "@microsoft/fetch-event-source";

export interface Live2DMeta {
  state: "idle" | "thinking" | "speaking" | "reacting";
  emotion: "neutral" | "happy" | "sad" | "angry";
  motion: string;
  expression: string;
}

export interface ChatRequest {
  sessionId: string;
  message: {
    id: string;
    text: string;
  };
  trigger: string;
}

export interface SSEStreamResult {
  assistantMessageId: string;
  fullText: string;
  metadata: {
    live2d: Live2DMeta | null;
  };
}

export interface SSEStartPayload {
  session_id: string;
  assistant_message_id: string;
  metadata: {
    live2d: Live2DMeta;
  };
}

interface SSEStatePayload {
  assistant_message_id: string;
  metadata: {
    live2d: Live2DMeta;
  };
}

interface SSEDeltaPayload {
  assistant_message_id: string;
  sequence: number;
  text: string;
}

interface SSECompletePayload {
  assistant_message_id: string;
  finish_reason: string;
  message: {
    id: string;
    role: "assistant";
    content: string;
    metadata?: {
      live2d?: Live2DMeta;
    };
  };
}

interface SSEErrorPayload {
  error: string;
}

export interface StreamDelta {
  assistantMessageId: string;
  text: string;
  fullText: string;
  metadata: Live2DMeta | null;
}

export interface StreamStart {
  sessionId: string;
  assistantMessageId: string;
  metadata: Live2DMeta | null;
}

export interface SendMessageHandlers {
  onStart?: (payload: StreamStart) => void;
  onDelta?: (payload: StreamDelta) => void;
  onState?: (metadata: Live2DMeta | null) => void;
  onComplete?: (result: SSEStreamResult) => void;
}

export type FetchEventSourceFunction = (
  input: RequestInfo,
  init: FetchEventSourceInit
) => Promise<void>;

interface LeadChatTransportOptions {
  endpoint?: string;
  fetchEventSource?: FetchEventSourceFunction;
}

class LeadChatTransportError extends Error {
  constructor(message: string, options?: { cause?: unknown }) {
    super(message, options);
    this.name = "LeadChatTransportError";
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isLive2DMeta(value: unknown): value is Live2DMeta {
  if (!isObject(value)) {
    return false;
  }

  return (
    typeof value.state === "string" &&
    typeof value.emotion === "string" &&
    typeof value.motion === "string" &&
    typeof value.expression === "string"
  );
}

function parseEventPayload<T>(event: EventSourceMessage, label: string): T {
  try {
    return JSON.parse(event.data) as T;
  } catch (error) {
    throw new LeadChatTransportError(`Failed to parse ${label} event payload`, {
      cause: error,
    });
  }
}

function assertStartPayload(payload: unknown): asserts payload is SSEStartPayload {
  if (
    !isObject(payload) ||
    typeof payload.session_id !== "string" ||
    typeof payload.assistant_message_id !== "string" ||
    !isObject(payload.metadata) ||
    !isLive2DMeta(payload.metadata.live2d)
  ) {
    throw new LeadChatTransportError("Invalid start event payload");
  }
}

function assertStatePayload(payload: unknown): asserts payload is SSEStatePayload {
  if (
    !isObject(payload) ||
    typeof payload.assistant_message_id !== "string" ||
    !isObject(payload.metadata) ||
    !isLive2DMeta(payload.metadata.live2d)
  ) {
    throw new LeadChatTransportError("Invalid state event payload");
  }
}

function assertDeltaPayload(payload: unknown): asserts payload is SSEDeltaPayload {
  if (
    !isObject(payload) ||
    typeof payload.assistant_message_id !== "string" ||
    typeof payload.sequence !== "number" ||
    typeof payload.text !== "string"
  ) {
    throw new LeadChatTransportError("Invalid delta event payload");
  }
}

function assertCompletePayload(payload: unknown): asserts payload is SSECompletePayload {
  if (
    !isObject(payload) ||
    typeof payload.assistant_message_id !== "string" ||
    !isObject(payload.message) ||
    typeof payload.message.content !== "string"
  ) {
    throw new LeadChatTransportError("Invalid complete event payload");
  }
}

function assertErrorPayload(payload: unknown): asserts payload is SSEErrorPayload {
  if (!isObject(payload) || typeof payload.error !== "string") {
    throw new LeadChatTransportError("Invalid error event payload");
  }
}

export class LeadChatTransport {
  private readonly endpoint: string;
  private readonly fetchEventSourceImpl: FetchEventSourceFunction;
  private abortController: AbortController | null = null;

  constructor(options: LeadChatTransportOptions = {}) {
    this.endpoint = options.endpoint ?? "/api/chat";
    this.fetchEventSourceImpl = options.fetchEventSource ?? fetchEventSource;
  }

  cancel() {
    this.abortController?.abort();
    this.abortController = null;
  }

  async sendMessage(
    request: ChatRequest,
    handlers: SendMessageHandlers = {}
  ): Promise<SSEStreamResult> {
    this.cancel();

    const abortController = new AbortController();
    this.abortController = abortController;

    let sessionId = request.sessionId;
    let assistantMessageId = "";
    let fullText = "";
    let live2d: Live2DMeta | null = null;
    let completedResult: SSEStreamResult | null = null;
    let streamError: Error | null = null;
    const seenSequences = new Set<number>();

    try {
      await this.fetchEventSourceImpl(this.endpoint, {
        method: "POST",
        headers: {
          Accept: "text/event-stream",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          session_id: request.sessionId,
          message: request.message,
          trigger: request.trigger,
        }),
        signal: abortController.signal,
        openWhenHidden: true,
        async onopen(response) {
          const contentType = response.headers.get("content-type") ?? "";
          if (response.ok && contentType.includes(EventStreamContentType)) {
            return;
          }

          throw new LeadChatTransportError(
            `Unexpected SSE response: ${response.status}`
          );
        },
        onmessage: (event) => {
          if (event.event === "start") {
            const payload = parseEventPayload<SSEStartPayload>(event, "start");
            assertStartPayload(payload);
            sessionId = payload.session_id;
            assistantMessageId = payload.assistant_message_id;
            live2d = payload.metadata.live2d;
            handlers.onStart?.({
              sessionId,
              assistantMessageId,
              metadata: live2d,
            });
            return;
          }

          if (event.event === "state") {
            const payload = parseEventPayload<SSEStatePayload>(event, "state");
            assertStatePayload(payload);
            assistantMessageId = payload.assistant_message_id;
            live2d = payload.metadata.live2d;
            handlers.onState?.(live2d);
            return;
          }

          if (event.event === "delta") {
            const payload = parseEventPayload<SSEDeltaPayload>(event, "delta");
            assertDeltaPayload(payload);
            if (seenSequences.has(payload.sequence)) {
              return;
            }

            seenSequences.add(payload.sequence);
            assistantMessageId = payload.assistant_message_id;
            fullText += payload.text;
            handlers.onDelta?.({
              assistantMessageId,
              text: payload.text,
              fullText,
              metadata: live2d,
            });
            return;
          }

          if (event.event === "complete") {
            const payload = parseEventPayload<SSECompletePayload>(event, "complete");
            assertCompletePayload(payload);
            assistantMessageId = payload.assistant_message_id;
            fullText = payload.message.content;
            const completeLive2D = payload.message.metadata?.live2d;
            if (completeLive2D && isLive2DMeta(completeLive2D)) {
              live2d = completeLive2D;
            }
            completedResult = {
              assistantMessageId,
              fullText,
              metadata: {
                live2d,
              },
            };
            handlers.onComplete?.(completedResult);
            abortController.abort();
            return;
          }

          if (event.event === "error") {
            const payload = parseEventPayload<SSEErrorPayload>(event, "error");
            assertErrorPayload(payload);
            throw new LeadChatTransportError(payload.error);
          }
        },
        onclose() {
          if (!completedResult && !streamError) {
            throw new LeadChatTransportError("SSE stream closed before completion");
          }
        },
        onerror(error) {
          streamError =
            error instanceof Error
              ? error
              : new LeadChatTransportError("Unknown SSE transport error");
          throw streamError;
        },
      });
    } catch (error) {
      if (abortController.signal.aborted && completedResult) {
        return completedResult;
      }

      if (error instanceof Error) {
        throw error;
      }

      throw new LeadChatTransportError("Unknown SSE transport error");
    } finally {
      if (this.abortController === abortController) {
        this.abortController = null;
      }
    }

    if (completedResult) {
      return completedResult;
    }

    throw new LeadChatTransportError("SSE stream completed without a complete event");
  }
}
