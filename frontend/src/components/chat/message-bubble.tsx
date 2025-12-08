"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import { SourcesPanel } from "./sources-panel";
import { cn } from "@/lib/utils";
import { SourceItem } from "@/lib/api";
import { User, Bot, Copy, Check } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";

import "highlight.js/styles/github-dark.css";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  sources?: SourceItem[];
  isStreaming?: boolean;
}

export function MessageBubble({ role, content, sources, isStreaming }: MessageBubbleProps) {
  const isUser = role === "user";
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    toast.success("已复制到剪贴板");
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={cn("flex w-full gap-3 py-3 px-4", isUser ? "flex-row-reverse" : "flex-row")}>
      <Avatar className="h-7 w-7 shrink-0 mt-0.5">
        <AvatarFallback className={cn("text-xs", isUser ? "bg-primary text-primary-foreground" : "bg-muted border border-border")}>
          {isUser ? <User className="h-3.5 w-3.5" /> : <Bot className="h-3.5 w-3.5" />}
        </AvatarFallback>
      </Avatar>

      <div className={cn("flex max-w-[70%] flex-col gap-1", isUser ? "items-end" : "items-start")}>
        {/* 气泡和复制按钮容器 */}
        <div className={cn("group flex items-start gap-1", isUser ? "flex-row-reverse" : "flex-row")}>
          <div
            className={cn(
              "rounded-xl px-4 py-2.5 text-sm",
              isUser
                ? "bg-primary text-primary-foreground rounded-tr-sm"
                : "bg-muted/60 text-foreground rounded-tl-sm"
            )}
          >
            {isUser ? (
              <div className="whitespace-pre-wrap leading-relaxed">{content}</div>
            ) : (
              <div className="markdown-body prose prose-neutral dark:prose-invert max-w-none text-sm leading-relaxed">
                <ReactMarkdown 
                  remarkPlugins={[remarkGfm]} 
                  rehypePlugins={[rehypeHighlight]}
                  components={{
                    a: ({ node, ...props }) => <a target="_blank" rel="noopener noreferrer" className="text-primary hover:underline" {...props} />,
                    pre: ({ node, ...props }) => (
                      <div className="overflow-auto rounded-lg bg-muted/50 border border-border/50 p-3 my-3">
                        <pre {...props} className="!bg-transparent !p-0 !m-0" />
                      </div>
                    ),
                    code: ({ node, ...props }) => (
                      <code {...props} className="bg-muted/50 rounded px-1 py-0.5 font-mono text-xs" />
                    ),
                  }}
                >
                  {content}
                </ReactMarkdown>
                {isStreaming && (
                  <span className="inline-block w-1.5 h-4 ml-1 bg-primary animate-pulse align-middle" />
                )}
              </div>
            )}
          </div>
          {/* 复制按钮 - 悬浮在气泡旁边 */}
          {!isStreaming && content && (
            <button
              onClick={handleCopy}
              className="mt-1 p-1 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-foreground"
              title="复制"
            >
              {copied ? (
                <Check className="h-3.5 w-3.5 text-green-500" />
              ) : (
                <Copy className="h-3.5 w-3.5" />
              )}
            </button>
          )}
        </div>

        {/* 引用来源 - 紧贴气泡 */}
        {!isUser && sources && sources.length > 0 && (
          <SourcesPanel sources={sources} />
        )}
      </div>
    </div>
  );
}
