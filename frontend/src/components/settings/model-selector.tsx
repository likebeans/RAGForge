"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAppStore } from "@/lib/store";
import { Loader2 } from "lucide-react";

export type ModelType = "llm" | "embedding" | "rerank";

interface ModelSelectorProps {
  type: ModelType;
  provider: string;
  value?: string;
  onChange?: (model: string) => void;
  label?: string;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export function ModelSelector({
  type,
  provider,
  value,
  onChange,
  label,
  placeholder = "选择模型",
  disabled = false,
  className,
}: ModelSelectorProps) {
  const { client, isConnected, providerConfigs, upsertProviderConfig } = useAppStore();
  const [models, setModels] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const providerConfig = providerConfigs[provider];
  // 防止重复加载
  const loadedRef = useRef<string | null>(null);

  const loadModels = useCallback(async () => {
    if (!client || !provider) return;
    // 防止重复请求同一个 provider + type
    const key = `${provider}:${type}`;
    if (loadedRef.current === key) return;
    loadedRef.current = key;
    
    setIsLoading(true);
    try {
      const config = providerConfigs[provider];
      const result = await client.getProviderModels(provider, config?.apiKey, config?.baseUrl);
      const modelList = result[type] || [];
      setModels(modelList);
      upsertProviderConfig(provider, { models: result });
    } catch (error) {
      console.error("Failed to load models:", error);
      setModels([]);
      loadedRef.current = null; // 失败后允许重试
    } finally {
      setIsLoading(false);
    }
  }, [client, provider, type, providerConfigs, upsertProviderConfig]);

  useEffect(() => {
    if (!client || !isConnected || !provider) {
      setModels([]);
      loadedRef.current = null;
      return;
    }
    const cached = providerConfig?.models?.[type];
    if (cached && cached.length > 0) {
      setModels(cached);
      setIsLoading(false);
      loadedRef.current = `${provider}:${type}`;
      return;
    }
    loadModels();
  }, [client, isConnected, provider, type]); // 移除 providerConfig?.models 依赖

  const typeLabels: Record<ModelType, string> = {
    llm: "LLM 模型",
    embedding: "Embedding 模型",
    rerank: "Rerank 模型",
  };

  return (
    <div className={className}>
      {label !== undefined ? (
        label && <Label className="mb-2 block">{label}</Label>
      ) : (
        <Label className="mb-2 block">{typeLabels[type]}</Label>
      )}
      <Select value={value} onValueChange={onChange} disabled={disabled || isLoading}>
        <SelectTrigger>
          {isLoading ? (
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>加载中...</span>
            </div>
          ) : (
            <SelectValue placeholder={placeholder} />
          )}
        </SelectTrigger>
        <SelectContent>
          {models.length === 0 ? (
            <div className="p-2 text-sm text-muted-foreground text-center">
              暂无可用模型
            </div>
          ) : (
            models.map((model) => (
              <SelectItem key={model} value={model}>
                {model}
              </SelectItem>
            ))
          )}
        </SelectContent>
      </Select>
    </div>
  );
}

// 简化版：提供商+模型组合选择器
interface ProviderModelSelectorProps {
  type: ModelType;
  providerValue?: string;
  modelValue?: string;
  onProviderChange?: (provider: string) => void;
  onModelChange?: (model: string) => void;
  label?: string;
  disabled?: boolean;
  className?: string;
  providers?: { id: string; name: string; supports?: Partial<Record<ModelType, boolean>>; validated?: boolean }[];
  requireValidated?: boolean;
}

export function ProviderModelSelector({
  type,
  providerValue,
  modelValue,
  onProviderChange,
  onModelChange,
  label,
  disabled = false,
  className,
  providers,
  requireValidated = true,
}: ProviderModelSelectorProps) {
  const { providerCatalog, providerConfigs } = useAppStore();
  const catalogProviders =
    providers ??
    Object.entries(providerCatalog).map(([id, meta]) => ({
      id,
      name: meta.name,
      supports: meta.supports,
      validated: providerConfigs[id]?.validated,
    }));

  const availableProviders = catalogProviders
    .filter((p) => {
      if (requireValidated && !p.validated) return false;
      if (p.supports && p.supports[type] === false) return false;
      return true;
    })
    .sort((a, b) => a.name.localeCompare(b.name));

  const typeLabels: Record<ModelType, string> = {
    llm: "LLM",
    embedding: "Embedding",
    rerank: "Rerank",
  };

  return (
    <div className={className}>
      {label !== undefined ? (
        label && <Label className="mb-2 block">{label}</Label>
      ) : (
        <Label className="mb-2 block">{typeLabels[type]} 配置</Label>
      )}
      <div className="flex gap-2">
        <Select
          value={providerValue}
          onValueChange={onProviderChange}
          disabled={disabled || availableProviders.length === 0}
        >
          <SelectTrigger className="w-[140px]">
            <SelectValue placeholder="提供商" />
          </SelectTrigger>
          <SelectContent>
            {availableProviders.length === 0 ? (
              <div className="px-2 py-1.5 text-sm text-muted-foreground">
                无可用提供商
              </div>
            ) : (
              availableProviders.map((p) => (
                <SelectItem key={p.id} value={p.id}>
                  {p.name}
                </SelectItem>
              ))
            )}
          </SelectContent>
        </Select>
        <div className="flex-1">
          <ModelSelector
            type={type}
            provider={providerValue || ""}
            value={modelValue}
            onChange={onModelChange}
            label=""
            placeholder="选择模型"
            disabled={disabled || !providerValue}
          />
        </div>
      </div>
    </div>
  );
}
