"use client";

import { useState, useMemo } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/lib/store";
import { Check, ChevronDown, Search, ExternalLink, Bot, Sparkles, ArrowUpDown } from "lucide-react";
import { cn } from "@/lib/utils";
import Link from "next/link";

export type ModelType = "llm" | "embedding" | "rerank";

// 提供商图标配置
const PROVIDER_ICONS: Record<string, { icon: string; color: string }> = {
  ollama: { icon: "🦙", color: "text-blue-600" },
  openai: { icon: "🤖", color: "text-green-600" },
  qwen: { icon: "🔮", color: "text-purple-600" },
  zhipu: { icon: "🧠", color: "text-blue-500" },
  siliconflow: { icon: "🌊", color: "text-cyan-600" },
  gemini: { icon: "💎", color: "text-yellow-600" },
  deepseek: { icon: "🔍", color: "text-indigo-600" },
  kimi: { icon: "🌙", color: "text-orange-600" },
  cohere: { icon: "🔗", color: "text-pink-600" },
  vllm: { icon: "⚡", color: "text-amber-600" },
};

// 提供商中文名
const PROVIDER_NAMES: Record<string, string> = {
  ollama: "Ollama",
  openai: "OpenAI",
  qwen: "通义千问",
  zhipu: "智谱 AI",
  siliconflow: "硅基流动",
  gemini: "Gemini",
  deepseek: "DeepSeek",
  kimi: "Kimi",
  cohere: "Cohere",
  vllm: "vLLM",
};

interface ModelOption {
  provider: string;
  providerName: string;
  model: string;
}

interface AllModelsSelectorProps {
  type: ModelType;
  value?: { provider: string; model: string };
  onChange?: (value: { provider: string; model: string }) => void;
  label?: string;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export function AllModelsSelector({
  type,
  value,
  onChange,
  label,
  placeholder = "选择模型",
  disabled = false,
  className,
}: AllModelsSelectorProps) {
  const { providerCatalog, providerConfigs } = useAppStore();
  const [open, setOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  // 聚合所有已验证提供商的模型
  const allModels = useMemo(() => {
    const models: ModelOption[] = [];
    
    Object.entries(providerConfigs).forEach(([providerId, config]) => {
      // 只展示已验证的提供商
      if (!config.validated) return;
      
      // 检查该提供商是否支持该类型
      const catalogInfo = providerCatalog[providerId];
      if (catalogInfo?.supports && catalogInfo.supports[type] === false) return;
      
      // 获取该类型的模型列表
      const modelList = config.models?.[type] || [];
      modelList.forEach((model) => {
        models.push({
          provider: providerId,
          providerName: PROVIDER_NAMES[providerId] || catalogInfo?.name || providerId,
          model,
        });
      });
    });
    
    return models;
  }, [providerConfigs, providerCatalog, type]);

  // 按提供商分组
  const groupedModels = useMemo(() => {
    const groups: Record<string, ModelOption[]> = {};
    
    allModels.forEach((item) => {
      const query = searchQuery.toLowerCase();
      // 搜索过滤
      if (query && !item.model.toLowerCase().includes(query) && 
          !item.providerName.toLowerCase().includes(query)) {
        return;
      }
      
      if (!groups[item.provider]) {
        groups[item.provider] = [];
      }
      groups[item.provider].push(item);
    });
    
    return groups;
  }, [allModels, searchQuery]);

  // 当前选中的显示文本
  const displayText = useMemo(() => {
    if (!value?.provider || !value?.model) return null;
    const providerName = PROVIDER_NAMES[value.provider] || providerCatalog[value.provider]?.name || value.provider;
    return `${providerName} / ${value.model}`;
  }, [value, providerCatalog]);

  const typeLabels: Record<ModelType, string> = {
    llm: "LLM 模型",
    embedding: "Embedding 模型",
    rerank: "Rerank 模型",
  };

  const typeIcons: Record<ModelType, React.ReactNode> = {
    llm: <Bot className="h-4 w-4" />,
    embedding: <Sparkles className="h-4 w-4" />,
    rerank: <ArrowUpDown className="h-4 w-4" />,
  };

  const handleSelect = (provider: string, model: string) => {
    onChange?.({ provider, model });
    setOpen(false);
    setSearchQuery("");
  };

  const isEmpty = Object.keys(groupedModels).length === 0;

  return (
    <div className={className}>
      {label !== undefined ? (
        label && <Label className="mb-2 block">{label}</Label>
      ) : (
        <Label className="mb-2 block">{typeLabels[type]}</Label>
      )}
      
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            disabled={disabled || allModels.length === 0}
            className="w-full justify-between font-normal h-10"
          >
            {displayText ? (
              <span className="flex items-center gap-2">
                {typeIcons[type]}
                <span className="truncate">{displayText}</span>
              </span>
            ) : (
              <span className="text-muted-foreground">{placeholder}</span>
            )}
            <ChevronDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[400px] p-0" align="start">
          {/* 搜索框 */}
          <div className="flex items-center border-b px-3">
            <Search className="mr-2 h-4 w-4 shrink-0 opacity-50" />
            <Input
              placeholder="搜索模型"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="border-0 focus-visible:ring-0 focus-visible:ring-offset-0"
            />
          </div>
          
          {/* 模型列表 */}
          <div className="max-h-[300px] overflow-y-auto">
            {isEmpty ? (
              <div className="p-4 text-center text-sm text-muted-foreground">
                {searchQuery ? "没有找到匹配的模型" : "暂无可用模型，请先在设置中配置模型提供商"}
              </div>
            ) : (
              Object.entries(groupedModels).map(([providerId, models]) => {
                const iconInfo = PROVIDER_ICONS[providerId];
                const providerName = PROVIDER_NAMES[providerId] || providerCatalog[providerId]?.name || providerId;
                
                return (
                  <div key={providerId}>
                    {/* 提供商分组标题 */}
                    <div className="px-3 py-2 text-xs font-medium text-muted-foreground bg-muted/50 sticky top-0">
                      {iconInfo?.icon && <span className="mr-1">{iconInfo.icon}</span>}
                      {providerName}
                    </div>
                    {/* 模型列表 */}
                    {models.map((item) => {
                      const isSelected = value?.provider === item.provider && value?.model === item.model;
                      return (
                        <div
                          key={`${item.provider}-${item.model}`}
                          className={cn(
                            "flex items-center gap-2 px-3 py-2 cursor-pointer hover:bg-accent",
                            isSelected && "bg-accent"
                          )}
                          onClick={() => handleSelect(item.provider, item.model)}
                        >
                          <span className={cn("w-4 h-4", iconInfo?.color || "text-muted-foreground")}>
                            {iconInfo?.icon || "📦"}
                          </span>
                          <span className="flex-1 truncate">{item.model}</span>
                          {isSelected && <Check className="h-4 w-4 text-primary" />}
                        </div>
                      );
                    })}
                  </div>
                );
              })
            )}
          </div>
          
          {/* 底部链接 */}
          <div className="border-t p-2">
            <Link 
              href="/settings" 
              className="flex items-center gap-1 text-xs text-primary hover:underline px-2"
              onClick={() => setOpen(false)}
            >
              模型设置
              <ExternalLink className="h-3 w-3" />
            </Link>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  );
}
