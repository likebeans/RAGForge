"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Send, Loader2, Database, Sparkles, MessageSquare, Search } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { SourceItem, Message } from "@/lib/api";
import { MessageBubble } from "@/components/chat/message-bubble";
import { ProviderModelSelector } from "@/components/settings";

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceItem[];
  isStreaming?: boolean;
}

const RETRIEVERS = [
  { value: "dense", label: "Dense (向量)" },
  { value: "bm25", label: "BM25 (稀疏)" },
  { value: "hybrid", label: "Hybrid (混合)" },
  { value: "hyde", label: "HyDE (假设文档)" },
  { value: "fusion", label: "Fusion (融合)" },
];

interface ChatViewProps {
  conversationId?: string; // undefined 表示新对话
}

export function ChatView({ conversationId }: ChatViewProps) {
  const router = useRouter();
  const { 
    client, 
    isConnected, 
    knowledgeBases, 
    selectedKbId, 
    selectKnowledgeBase, 
    refreshKnowledgeBases,
    setCurrentConversationId,
    refreshConversations,
    defaultModels,
    setDefaultModel,
    providerConfigs,
    providerCatalog,
    setProviderCatalog,
  } = useAppStore();
  
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [retriever, setRetriever] = useState("hybrid");
  const [llmProvider, setLlmProvider] = useState(defaultModels.llm?.provider || "");
  const [llmModel, setLlmModel] = useState(defaultModels.llm?.model || "");
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // 取消当前流式请求
  const abortCurrentRequest = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
  }, []);

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      abortCurrentRequest();
    };
  }, [abortCurrentRequest]);

  // 同步 conversationId 到 store（用于 sidebar 高亮）
  useEffect(() => {
    setCurrentConversationId(conversationId || null);
  }, [conversationId, setCurrentConversationId]);

  useEffect(() => {
    setLlmProvider(defaultModels.llm?.provider || "");
    setLlmModel(defaultModels.llm?.model || "");
  }, [defaultModels]);

  // 加载知识库列表
  useEffect(() => {
    if (client && isConnected) {
      refreshKnowledgeBases();
    }
  }, [client, isConnected, refreshKnowledgeBases]);

  useEffect(() => {
    if (client && isConnected && Object.keys(providerCatalog).length === 0) {
      client.listProviders().then(setProviderCatalog).catch(() => undefined);
    }
  }, [client, isConnected, providerCatalog, setProviderCatalog]);

  // 加载对话消息
  useEffect(() => {
    if (!conversationId || !client) {
      setMessages([]);
      return;
    }

    const loadMessages = async () => {
      try {
        const detail = await client.getConversation(conversationId);
        const loadedMessages: ChatMessage[] = detail.messages.map((msg: Message) => ({
          id: msg.id,
          role: msg.role,
          content: msg.content,
          sources: msg.sources,
          isStreaming: false,
        }));
        setMessages(loadedMessages);
      } catch (error) {
        console.error("Failed to load conversation messages:", error);
        toast.error("加载对话失败");
        router.push("/chat");
      }
    };
    loadMessages();
  }, [conversationId, client, router]);

  // 自动滚动
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleLlmProviderChange = (provider: string) => {
    setLlmProvider(provider);
    setLlmModel("");
    setDefaultModel("llm", provider ? { provider, model: "" } : null);
  };

  const handleLlmModelChange = (model: string) => {
    setLlmModel(model);
    if (llmProvider) {
      setDefaultModel("llm", { provider: llmProvider, model });
    }
  };

  const handleSubmit = async () => {
    if (!input.trim() || isLoading) return;
    if (!client) {
      toast.error("请先配置 API Key");
      return;
    }
    if (!selectedKbId) {
      toast.error("请先选择知识库");
      return;
    }

    // 取消之前的请求
    abortCurrentRequest();

    // 如果是新对话，先创建
    let activeConversationId = conversationId;
    if (!activeConversationId) {
      try {
        const title = input.trim().slice(0, 50);
        const newConv = await client.createConversation(title, [selectedKbId]);
        activeConversationId = newConv.id;
        // 刷新侧边栏对话列表
        refreshConversations();
        // 静默更新 URL（不触发页面重新渲染）
        window.history.replaceState(null, "", `/chat/${activeConversationId}`);
        // 同步 store 状态
        setCurrentConversationId(activeConversationId);
      } catch (error) {
        toast.error("创建对话失败");
        return;
      }
    }

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
    };

    const assistantMessage: ChatMessage = {
      id: (Date.now() + 1).toString(),
      role: "assistant",
      content: "",
      isStreaming: true,
    };

    setMessages((prev) => [...prev, userMessage, assistantMessage]);
    setInput("");
    setIsLoading(true);

    // 保存用户消息到后端
    client.addMessage(activeConversationId!, "user", userMessage.content).catch((err) => {
      console.error("Failed to save user message:", err);
    });

    // 用于收集助手消息的完整内容和来源
    let finalContent = "";
    let finalSources: SourceItem[] = [];
    const llmOverride =
      llmProvider && llmModel
        ? {
            provider: llmProvider,
            model: llmModel,
            api_key: providerConfigs[llmProvider]?.apiKey,
            base_url: providerConfigs[llmProvider]?.baseUrl,
          }
        : undefined;

    try {
      abortRef.current = client.streamRAG(
        userMessage.content,
        [selectedKbId],
        retriever,
        5,
        // onSources
        (sources) => {
          finalSources = sources;
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessage.id ? { ...msg, sources } : msg
            )
          );
        },
        // onContent
        (chunk) => {
          finalContent += chunk;
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessage.id
                ? { ...msg, content: msg.content + chunk }
                : msg
            )
          );
        },
        // onDone
        () => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessage.id
                ? { ...msg, isStreaming: false }
                : msg
            )
          );
          setIsLoading(false);
          
          // 保存助手消息到后端
          if (finalContent) {
            client.addMessage(activeConversationId!, "assistant", finalContent, retriever, finalSources).catch((err) => {
              console.error("Failed to save assistant message:", err);
            });
          }
        },
        // onError
        (error) => {
          toast.error(`生成失败: ${error}`);
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantMessage.id
                ? { ...msg, content: `错误: ${error}`, isStreaming: false }
                : msg
            )
          );
          setIsLoading(false);
        },
        { llmOverride }
      );
    } catch (error) {
      toast.error(`请求失败: ${(error as Error).message}`);
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex h-full flex-col relative bg-background">
      {/* 顶部工具栏 - 简化版 */}
      <div className="absolute top-0 left-0 right-0 z-10 flex items-center justify-between p-4 bg-background/80 backdrop-blur-sm border-b border-border/40">
        <div className="flex items-center gap-2">
          <Select value={selectedKbId || ""} onValueChange={selectKnowledgeBase}>
            <SelectTrigger className="w-[200px] border-none shadow-none bg-muted/50 hover:bg-muted focus:ring-0">
              <Database className="mr-2 h-4 w-4 text-muted-foreground" />
              <SelectValue placeholder="选择知识库" />
            </SelectTrigger>
            <SelectContent>
              {knowledgeBases.map((kb) => (
                <SelectItem key={kb.id} value={kb.id}>
                  {kb.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={retriever} onValueChange={setRetriever}>
            <SelectTrigger className="w-[140px] border-none shadow-none bg-transparent hover:bg-muted/50 focus:ring-0 text-muted-foreground">
              <SelectValue placeholder="检索器" />
            </SelectTrigger>
            <SelectContent>
              {RETRIEVERS.map((r) => (
                <SelectItem key={r.value} value={r.value}>
                  {r.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <div className="w-[280px]">
            <ProviderModelSelector
              type="llm"
              providerValue={llmProvider}
              modelValue={llmModel}
              onProviderChange={handleLlmProviderChange}
              onModelChange={handleLlmModelChange}
              label=""
            />
          </div>
        </div>
      </div>

      {/* 消息列表 */}
      <div className="flex-1 min-h-0 overflow-auto pt-14">
        <div className="mx-auto max-w-3xl px-4 h-full">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full py-8 text-center">
              {/* 主图标 */}
              <div className="relative mb-4">
                <div className="absolute inset-0 bg-primary/20 rounded-full blur-xl animate-pulse" />
                <div className="relative bg-gradient-to-br from-primary/10 to-primary/5 p-4 rounded-2xl border border-primary/10">
                  <Sparkles className="h-8 w-8 text-primary" />
                </div>
              </div>
              
              {/* 标题 */}
              <h2 className="text-xl font-semibold tracking-tight mb-2">
                知识库智能问答
              </h2>
              <p className="text-sm text-muted-foreground max-w-md mb-4 leading-relaxed">
                基于 RAG 技术，从您的知识库中检索相关内容，为您提供准确、有据可查的回答。
              </p>
              
              {/* 功能卡片 */}
              <div className="grid grid-cols-3 gap-3 max-w-lg w-full">
                <div className="flex flex-col items-center p-3 rounded-lg bg-muted/30 border border-border/40 hover:bg-muted/50 transition-colors">
                  <div className="w-8 h-8 rounded-lg bg-blue-500/10 flex items-center justify-center mb-2">
                    <Database className="h-4 w-4 text-blue-500" />
                  </div>
                  <span className="text-xs font-medium">知识库检索</span>
                </div>
                
                <div className="flex flex-col items-center p-3 rounded-lg bg-muted/30 border border-border/40 hover:bg-muted/50 transition-colors">
                  <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center mb-2">
                    <Search className="h-4 w-4 text-emerald-500" />
                  </div>
                  <span className="text-xs font-medium">多检索器</span>
                </div>
                
                <div className="flex flex-col items-center p-3 rounded-lg bg-muted/30 border border-border/40 hover:bg-muted/50 transition-colors">
                  <div className="w-8 h-8 rounded-lg bg-amber-500/10 flex items-center justify-center mb-2">
                    <MessageSquare className="h-4 w-4 text-amber-500" />
                  </div>
                  <span className="text-xs font-medium">引用来源</span>
                </div>
              </div>
              
              {/* 快速开始提示 */}
              {!selectedKbId && (
                <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground bg-muted/30 px-3 py-1.5 rounded-full">
                  <Database className="h-3 w-3" />
                  <span>请先在上方选择一个知识库</span>
                </div>
              )}
            </div>
          )}

          {messages.length > 0 && (
            <div className="py-4 space-y-4">
              {messages.map((msg) => (
                <MessageBubble
                  key={msg.id}
                  role={msg.role}
                  content={msg.content}
                  sources={msg.sources}
                  isStreaming={msg.isStreaming}
                />
              ))}
              <div ref={scrollRef} />
            </div>
          )}
        </div>
      </div>

      {/* 输入区 */}
      <div className="shrink-0 py-3 px-4 border-t border-border/40 bg-background">
        <div className="mx-auto max-w-2xl">
          <div className="relative flex items-end gap-2 bg-muted/40 border border-input rounded-lg p-1.5 focus-within:ring-1 focus-within:ring-ring focus-within:border-ring transition-all">
            <Textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入问题... (Shift+Enter 换行)"
              className="min-h-[40px] max-h-[160px] w-full resize-none border-none bg-transparent shadow-none focus-visible:ring-0 px-2.5 py-2 text-sm"
              disabled={isLoading || !isConnected}
            />
            <Button
              onClick={handleSubmit}
              disabled={isLoading || !input.trim() || !isConnected}
              size="icon"
              className="h-8 w-8 shrink-0 rounded-md"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
