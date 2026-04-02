import {
  Conversation,
  ConversationContent,
  ConversationScrollButton,
} from "@/components/ai-elements/conversation";
import {
  Message,
  MessageContent,
  MessageResponse,
} from "@/components/ai-elements/message";
import {
  PromptInput,
  PromptInputBody,
  PromptInputButton,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
} from "@/components/ai-elements/prompt-input";
import { Suggestion, Suggestions } from "@/components/ai-elements/suggestion";
import { cn } from "@/lib/utils";
import { Bot, Mic, Paperclip, Star } from "lucide-react";

type DemoMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
};

const quickPrompts = [
  "今天状态怎么样？",
  "给我一个晚安陪伴脚本",
  "模拟一次轻松闲聊",
];

const demoMessages: DemoMessage[] = [
  {
    id: "m-1",
    role: "assistant",
    content:
      "欢迎回来，我已经为你预留好了 Live2D 角色区域。右侧会承载对话历史、状态提示和输入栏。",
    timestamp: "14:36",
  },
  {
    id: "m-2",
    role: "user",
    content: "我想做一个更像陪伴型角色的首页布局，聊天区放在右边。",
    timestamp: "14:37",
  },
  {
    id: "m-3",
    role: "assistant",
    content:
      "已按三栏结构规划：左侧导航、中央角色舞台、右侧聊天面板。你之后只需要把 Live2D 渲染接进中间区域即可。",
    timestamp: "14:38",
  },
];

export function HomeChatPanel() {
  return (
    <aside className="flex w-[420px] min-w-[420px] shrink-0 flex-col p-5 xl:w-[480px] xl:min-w-[480px]">
      <div className="flex items-center justify-between gap-4 rounded-[1.75rem] border border-sky-200/80 bg-white/75 px-4 py-4 backdrop-blur-xl">
        <div>
          <p className="font-medium text-sky-500 text-xs uppercase tracking-[0.3em]">
            Dialogue Dock
          </p>
          <h2 className="mt-2 font-semibold text-sky-950 text-xl">对话历史与输入栏</h2>
          <p className="mt-1 text-slate-500 text-sm">使用 ai-elements 组件拼出静态展示页。</p>
        </div>

        <div className="flex items-center gap-2 text-sky-700 text-xs">
          <span className="rounded-full border border-sky-200 bg-sky-50 px-3 py-1.5">
            Demo Session
          </span>
        </div>
      </div>

      <div className="mt-4 flex min-h-0 flex-1 flex-col overflow-hidden rounded-[2rem] border border-sky-200/80 bg-white/70 shadow-[0_24px_70px_rgba(148,197,255,0.25)] backdrop-blur-2xl">
        <div className="flex items-center justify-between border-sky-200/70 border-b px-4 py-4">
          <div>
            <p className="font-medium text-sky-950 text-sm">当前会话</p>
            <p className="mt-1 text-slate-500 text-xs">右侧保留消息历史与发送区</p>
          </div>

          <div className="flex items-center gap-2 rounded-full border border-sky-200 bg-sky-50 px-3 py-1.5 text-sky-700 text-xs">
            <Star className="size-3.5 text-sky-400" />
            3 条历史消息
          </div>
        </div>

        <Conversation className="min-h-0 flex-1">
          <ConversationContent className="gap-5 px-4 py-5">
            {demoMessages.map((message) => {
              const isUser = message.role === "user";

              return (
                <Message className="max-w-full" from={message.role} key={message.id}>
                  <div className={cn("flex items-end gap-3", isUser && "justify-end")}>
                    {!isUser && (
                      <div className="flex size-9 shrink-0 items-center justify-center rounded-2xl border border-sky-200 bg-sky-100 text-sky-500">
                        <Bot className="size-4" />
                      </div>
                    )}

                    <MessageContent
                      className={cn(
                        "max-w-[85%] rounded-[1.5rem] border px-4 py-3 shadow-lg backdrop-blur-sm",
                        isUser
                          ? "border-sky-300/30 bg-sky-300 text-sky-950"
                          : "border-sky-100 bg-white text-slate-700"
                      )}
                    >
                      <div
                        className={cn(
                          "mb-2 flex items-center gap-2 text-[11px] uppercase tracking-[0.24em]",
                          isUser ? "text-sky-900/65" : "text-sky-400"
                        )}
                      >
                        <span>{isUser ? "User" : "Assistant"}</span>
                        <span className="text-[10px] tracking-[0.18em]">{message.timestamp}</span>
                      </div>

                      <MessageResponse className="text-sm leading-6">
                        {message.content}
                      </MessageResponse>
                    </MessageContent>
                  </div>
                </Message>
              );
            })}
          </ConversationContent>

          <ConversationScrollButton className="border-sky-200 bg-white text-sky-700 hover:bg-sky-50" />
        </Conversation>

        <div className="border-sky-200/70 border-t px-4 py-4">
          <Suggestions className="pb-3">
            {quickPrompts.map((prompt) => (
              <Suggestion
                className="border-sky-200 bg-white text-sky-700 hover:bg-sky-50"
                key={prompt}
                suggestion={prompt}
              />
            ))}
          </Suggestions>

          <PromptInput
            className="rounded-[1.75rem] border border-sky-200 bg-white/90 p-2 shadow-[inset_0_1px_0_rgba(255,255,255,0.45)]"
            onSubmit={() => undefined}
          >
            <PromptInputBody>
              <PromptInputTextarea
                className="min-h-24 text-slate-700 placeholder:text-sky-300"
                placeholder="当前为静态展示页，后续接入接口后这里会变成真正的对话输入栏。"
              />
            </PromptInputBody>

            <PromptInputFooter className="mt-1 border-sky-200 border-t pt-2">
              <PromptInputTools>
                <PromptInputButton
                  className="border-sky-200 bg-sky-50 text-sky-600 hover:bg-sky-100"
                  disabled
                >
                  <Paperclip className="size-4" />
                </PromptInputButton>
                <PromptInputButton
                  className="border-sky-200 bg-sky-50 text-sky-600 hover:bg-sky-100"
                  disabled
                >
                  <Mic className="size-4" />
                </PromptInputButton>
              </PromptInputTools>

              <div className="flex items-center gap-3">
                <span className="hidden text-sky-400 text-xs sm:inline">Static preview only</span>
                <PromptInputSubmit
                  className="bg-sky-400 text-white hover:bg-sky-500"
                  disabled
                />
              </div>
            </PromptInputFooter>
          </PromptInput>
        </div>
      </div>
    </aside>
  );
}
