"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  Check,
  X,
  Loader2,
  ChevronDown,
  ChevronRight,
  Eye,
  EyeOff,
  Server,
  Cloud,
} from "lucide-react";
import { useAppStore } from "@/lib/store";
import { ProviderConfig, ValidateProviderResponse } from "@/lib/api";

// 提供商图标
const providerIcons: Record<string, React.ReactNode> = {
  ollama: <Server className="h-4 w-4" />,
  openai: <Cloud className="h-4 w-4" />,
  qwen: <Cloud className="h-4 w-4" />,
  deepseek: <Cloud className="h-4 w-4" />,
  zhipu: <Cloud className="h-4 w-4" />,
  siliconflow: <Cloud className="h-4 w-4" />,
  gemini: <Cloud className="h-4 w-4" />,
  kimi: <Cloud className="h-4 w-4" />,
  vllm: <Server className="h-4 w-4" />,
};

interface ProviderState {
  apiKey: string;
  baseUrl: string;
  isValidating: boolean;
  validated: boolean;
  valid: boolean;
  message: string;
  models: {
    llm?: string[];
    embedding?: string[];
    rerank?: string[];
  };
}

interface ModelProviderConfigProps {
  onProviderValidated?: (provider: string, models: ValidateProviderResponse["models"]) => void;
}

export function ModelProviderConfig({ onProviderValidated }: ModelProviderConfigProps) {
  const {
    client,
    isConnected,
    providerConfigs,
    setProviderCatalog,
    upsertProviderConfig,
    clearProviderConfig,
  } = useAppStore();
  const [providers, setProviders] = useState<Record<string, ProviderConfig>>({});
  const [providerStates, setProviderStates] = useState<Record<string, ProviderState>>({});
  const [expandedProviders, setExpandedProviders] = useState<Set<string>>(new Set());
  const [showApiKeys, setShowApiKeys] = useState<Set<string>>(new Set());
  const [isLoading, setIsLoading] = useState(true);

  // 加载提供商列表
  useEffect(() => {
    if (!client || !isConnected) return;
    loadProviders();
  }, [client, isConnected]);

  const loadProviders = async () => {
    if (!client) return;
    setIsLoading(true);
    try {
      const result = await client.listProviders();
      setProviders(result);
      setProviderCatalog(result);
      
      // 初始化每个提供商的状态
      const initialStates: Record<string, ProviderState> = {};
      for (const key of Object.keys(result)) {
        const saved = providerConfigs[key];
        initialStates[key] = {
          apiKey: saved?.apiKey || "",
          baseUrl: saved?.baseUrl || result[key].default_base_url,
          isValidating: false,
          validated: !!saved?.validated,
          valid: !!saved?.validated,
          message: saved?.validated ? "已验证" : "",
          models: saved?.models || {},
        };
      }
      setProviderStates(initialStates);
    } catch (error) {
      toast.error(`加载提供商列表失败: ${(error as Error).message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleValidate = async (providerId: string) => {
    if (!client) return;
    
    const state = providerStates[providerId];
    const config = providers[providerId];
    
    setProviderStates((prev) => ({
      ...prev,
      [providerId]: { ...prev[providerId], isValidating: true },
    }));

    try {
      const result = await client.validateProvider(
        providerId,
        config.api_key_required ? state.apiKey : undefined,
        state.baseUrl
      );
      
      setProviderStates((prev) => ({
        ...prev,
        [providerId]: {
          ...prev[providerId],
          isValidating: false,
          validated: true,
          valid: result.valid,
          message: result.message,
          models: result.models,
        },
      }));

      if (result.valid) {
        upsertProviderConfig(providerId, {
          apiKey: config.api_key_required ? state.apiKey : undefined,
          baseUrl: state.baseUrl,
          models: result.models,
          validated: true,
          validatedAt: new Date().toISOString(),
        });
        toast.success(`${config.name} 验证成功`);
        onProviderValidated?.(providerId, result.models);
      } else {
        upsertProviderConfig(providerId, { validated: false, models: {} });
        toast.error(result.message);
      }
    } catch (error) {
      setProviderStates((prev) => ({
        ...prev,
        [providerId]: {
          ...prev[providerId],
          isValidating: false,
          validated: true,
          valid: false,
          message: (error as Error).message,
          models: {},
        },
      }));
      upsertProviderConfig(providerId, { validated: false, models: {} });
      toast.error(`验证失败: ${(error as Error).message}`);
    }
  };

  const toggleExpand = (providerId: string) => {
    setExpandedProviders((prev) => {
      const next = new Set(prev);
      if (next.has(providerId)) {
        next.delete(providerId);
      } else {
        next.add(providerId);
      }
      return next;
    });
  };

  const toggleShowApiKey = (providerId: string) => {
    setShowApiKeys((prev) => {
      const next = new Set(prev);
      if (next.has(providerId)) {
        next.delete(providerId);
      } else {
        next.add(providerId);
      }
      return next;
    });
  };

  const handleClearConfig = (providerId: string) => {
    const fallbackBase = providers[providerId]?.default_base_url || "";
    clearProviderConfig(providerId);
    setProviderStates((prev) => ({
      ...prev,
      [providerId]: {
        apiKey: "",
        baseUrl: fallbackBase,
        isValidating: false,
        validated: false,
        valid: false,
        message: "",
        models: {},
      },
    }));
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>模型提供商配置</CardTitle>
        <CardDescription>
          配置各模型提供商的 API Key，验证后可查看可用模型
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {Object.entries(providers).map(([providerId, config]) => {
          const state = providerStates[providerId];
          const isExpanded = expandedProviders.has(providerId);
          const showKey = showApiKeys.has(providerId);

          return (
            <Collapsible
              key={providerId}
              open={isExpanded}
              onOpenChange={() => toggleExpand(providerId)}
            >
              <div className="border rounded-lg">
                <CollapsibleTrigger asChild>
                  <div className="flex items-center justify-between p-4 cursor-pointer hover:bg-muted/50">
                    <div className="flex items-center gap-3">
                      <span className="text-muted-foreground">
                        {providerIcons[providerId] || <Cloud className="h-4 w-4" />}
                      </span>
                      <div>
                        <div className="font-medium">{config.name}</div>
                        <div className="text-sm text-muted-foreground">
                          {config.description}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {state?.validated && (
                        <Badge variant={state.valid ? "default" : "secondary"}>
                          {state.valid ? (
                            <><Check className="h-3 w-3 mr-1" />已验证</>
                          ) : (
                            <><X className="h-3 w-3 mr-1" />未验证</>
                          )}
                        </Badge>
                      )}
                      <div className="flex gap-1">
                        {config.supports.llm && (
                          <Badge variant="outline" className="text-xs">LLM</Badge>
                        )}
                        {config.supports.embedding && (
                          <Badge variant="outline" className="text-xs">Embed</Badge>
                        )}
                        {config.supports.rerank && (
                          <Badge variant="outline" className="text-xs">Rerank</Badge>
                        )}
                      </div>
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </div>
                  </div>
                </CollapsibleTrigger>
                
                <CollapsibleContent>
                  <div className="px-4 pb-4 space-y-4 border-t pt-4">
                    {/* Base URL */}
                    <div className="space-y-2">
                      <Label>Base URL</Label>
                      <Input
                        value={state?.baseUrl || config.default_base_url}
                        onChange={(e) =>
                          setProviderStates((prev) => ({
                            ...prev,
                            [providerId]: { ...prev[providerId], baseUrl: e.target.value },
                          }))
                        }
                        placeholder={config.default_base_url}
                      />
                    </div>

                    {/* API Key (如果需要) */}
                    {config.api_key_required && (
                      <div className="space-y-2">
                        <Label>API Key</Label>
                        <div className="flex gap-2">
                          <Input
                            type={showKey ? "text" : "password"}
                            value={state?.apiKey || ""}
                            onChange={(e) =>
                              setProviderStates((prev) => ({
                                ...prev,
                                [providerId]: { ...prev[providerId], apiKey: e.target.value },
                              }))
                            }
                            placeholder="输入 API Key"
                            className="flex-1"
                          />
                          <Button
                            variant="outline"
                            size="icon"
                            onClick={() => toggleShowApiKey(providerId)}
                          >
                            {showKey ? (
                              <EyeOff className="h-4 w-4" />
                            ) : (
                              <Eye className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* 验证按钮 */}
                    <div className="flex items-center gap-2">
                      <Button
                        onClick={() => handleValidate(providerId)}
                        disabled={state?.isValidating || (config.api_key_required && !state?.apiKey)}
                      >
                        {state?.isValidating ? (
                          <><Loader2 className="h-4 w-4 mr-2 animate-spin" />验证中...</>
                        ) : (
                          "验证连接"
                        )}
                      </Button>
                      {(state?.validated || state?.apiKey) && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleClearConfig(providerId)}
                          disabled={state?.isValidating}
                        >
                          清除
                        </Button>
                      )}
                    </div>

                    {/* 验证结果 - 显示可用模型 */}
                    {state?.validated && state?.valid && (
                      <div className="space-y-3 pt-2">
                        {state.models.llm && state.models.llm.length > 0 && (
                          <div>
                            <Label className="text-sm text-muted-foreground">LLM 模型</Label>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {state.models.llm.slice(0, 10).map((model) => (
                                <Badge key={model} variant="secondary" className="text-xs">
                                  {model}
                                </Badge>
                              ))}
                              {state.models.llm.length > 10 && (
                                <Badge variant="outline" className="text-xs">
                                  +{state.models.llm.length - 10} 更多
                                </Badge>
                              )}
                            </div>
                          </div>
                        )}
                        {state.models.embedding && state.models.embedding.length > 0 && (
                          <div>
                            <Label className="text-sm text-muted-foreground">Embedding 模型</Label>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {state.models.embedding.map((model) => (
                                <Badge key={model} variant="secondary" className="text-xs">
                                  {model}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}
                        {state.models.rerank && state.models.rerank.length > 0 && (
                          <div>
                            <Label className="text-sm text-muted-foreground">Rerank 模型</Label>
                            <div className="flex flex-wrap gap-1 mt-1">
                              {state.models.rerank.map((model) => (
                                <Badge key={model} variant="secondary" className="text-xs">
                                  {model}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}

                    {/* 验证失败信息 */}
                    {state?.validated && !state?.valid && (
                      <div className="text-sm text-destructive">{state.message}</div>
                    )}
                  </div>
                </CollapsibleContent>
              </div>
            </Collapsible>
          );
        })}
      </CardContent>
    </Card>
  );
}
