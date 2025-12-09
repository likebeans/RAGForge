"use client";

import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ProviderModelSelector } from "./model-selector";
import { useAppStore } from "@/lib/store";
import { AlertCircle } from "lucide-react";

export function DefaultModelConfig() {
  const {
    providerConfigs,
    providerCatalog,
    defaultModels,
    setDefaultModel,
  } = useAppStore();

  const [llmProvider, setLlmProvider] = useState(defaultModels.llm?.provider || "");
  const [llmModel, setLlmModel] = useState(defaultModels.llm?.model || "");
  const [embedProvider, setEmbedProvider] = useState(defaultModels.embedding?.provider || "");
  const [embedModel, setEmbedModel] = useState(defaultModels.embedding?.model || "");
  const [rerankProvider, setRerankProvider] = useState(defaultModels.rerank?.provider || "");
  const [rerankModel, setRerankModel] = useState(defaultModels.rerank?.model || "");

  const validatedProviders = useMemo(
    () =>
      Object.entries(providerConfigs)
        .filter(([, cfg]) => cfg?.validated)
        .map(([id]) => ({
          id,
          name: providerCatalog[id]?.name || id,
          supports: providerCatalog[id]?.supports,
          validated: true,
        })),
    [providerCatalog, providerConfigs]
  );

  useEffect(() => {
    setLlmProvider(defaultModels.llm?.provider || "");
    setLlmModel(defaultModels.llm?.model || "");
    setEmbedProvider(defaultModels.embedding?.provider || "");
    setEmbedModel(defaultModels.embedding?.model || "");
    setRerankProvider(defaultModels.rerank?.provider || "");
    setRerankModel(defaultModels.rerank?.model || "");
  }, [defaultModels]);

  const handleProviderChange = (type: "llm" | "embedding" | "rerank", provider: string) => {
    if (type === "llm") {
      setLlmProvider(provider);
      setLlmModel("");
    } else if (type === "embedding") {
      setEmbedProvider(provider);
      setEmbedModel("");
    } else {
      setRerankProvider(provider);
      setRerankModel("");
    }
    setDefaultModel(type, provider ? { provider, model: "" } : null);
  };

  const handleModelChange = (type: "llm" | "embedding" | "rerank", model: string) => {
    if (type === "llm") {
      setLlmModel(model);
      if (llmProvider) setDefaultModel("llm", { provider: llmProvider, model });
    } else if (type === "embedding") {
      setEmbedModel(model);
      if (embedProvider) setDefaultModel("embedding", { provider: embedProvider, model });
    } else {
      setRerankModel(model);
      if (rerankProvider) setDefaultModel("rerank", { provider: rerankProvider, model });
    }
  };

  const hasValidated = validatedProviders.length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>默认模型</CardTitle>
        <CardDescription>为聊天与检索设置默认的 LLM / Embedding / Rerank 模型（仅显示已验证的提供商）</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {hasValidated ? (
          <>
            <ProviderModelSelector
              type="llm"
              providers={validatedProviders}
              providerValue={llmProvider}
              modelValue={llmModel}
              onProviderChange={(v) => handleProviderChange("llm", v)}
              onModelChange={(v) => handleModelChange("llm", v)}
            />
            <ProviderModelSelector
              type="embedding"
              providers={validatedProviders}
              providerValue={embedProvider}
              modelValue={embedModel}
              onProviderChange={(v) => handleProviderChange("embedding", v)}
              onModelChange={(v) => handleModelChange("embedding", v)}
            />
            <ProviderModelSelector
              type="rerank"
              providers={validatedProviders}
              providerValue={rerankProvider}
              modelValue={rerankModel}
              onProviderChange={(v) => handleProviderChange("rerank", v)}
              onModelChange={(v) => handleModelChange("rerank", v)}
            />
          </>
        ) : (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <AlertCircle className="h-4 w-4" />
            请先验证至少一个模型提供商
          </div>
        )}
      </CardContent>
    </Card>
  );
}
