"use client";

import { useState, useEffect } from "react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { Check, X, RefreshCw, Loader2, Plus, Trash2, Copy, Key, AlertCircle, Eye, EyeOff, Server, Cpu } from "lucide-react";
import { useAppStore } from "@/lib/store";
import { APIKeyInfo } from "@/lib/api";
import { ModelProviderConfig, DefaultModelConfig } from "@/components/settings";

export default function SettingsPage() {
  const { apiKey, apiBase, setApiKey, setApiBase, client, isConnected, setConnected } = useAppStore();
  
  const [localApiKey, setLocalApiKey] = useState(apiKey);
  const [localApiBase, setLocalApiBase] = useState(apiBase);
  const [isTesting, setIsTesting] = useState(false);
  
  // API Key 管理状态
  const [currentRole, setCurrentRole] = useState<string | null>(null);
  const [apiKeys, setApiKeys] = useState<APIKeyInfo[]>([]);
  const [isLoadingKeys, setIsLoadingKeys] = useState(false);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [newKeyRole, setNewKeyRole] = useState<"admin" | "write" | "read">("read");
  const [newKeyName, setNewKeyName] = useState("");
  const [isCreatingKey, setIsCreatingKey] = useState(false);
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<string | null>(null);
  const [showApiKey, setShowApiKey] = useState(false);

  useEffect(() => {
    setLocalApiKey(apiKey);
    setLocalApiBase(apiBase);
  }, [apiKey, apiBase]);

  // 加载当前角色和 API Keys
  useEffect(() => {
    if (client && isConnected) {
      loadCurrentRole();
    }
  }, [client, isConnected]);

  const loadCurrentRole = async () => {
    if (!client) return;
    try {
      const info = await client.getCurrentKeyInfo();
      setCurrentRole(info.role);
      if (info.role === "admin") {
        loadAPIKeys();
      }
    } catch {
      setCurrentRole(null);
    }
  };

  const loadAPIKeys = async () => {
    if (!client) return;
    setIsLoadingKeys(true);
    try {
      const result = await client.listAPIKeys();
      setApiKeys(result.items || []);
    } catch (error) {
      console.error("Failed to load API keys:", error);
    } finally {
      setIsLoadingKeys(false);
    }
  };

  const handleSave = () => {
    setApiKey(localApiKey);
    setApiBase(localApiBase);
    toast.success("配置已保存");
  };

  const handleTestConnection = async () => {
    if (!localApiKey) {
      toast.error("请输入 API Key");
      return;
    }

    setIsTesting(true);
    try {
      const response = await fetch(`${localApiBase}/health`);
      if (!response.ok) throw new Error("Health check failed");
      
      const kbResponse = await fetch(`${localApiBase}/v1/knowledge-bases`, {
        headers: { Authorization: `Bearer ${localApiKey}` },
      });
      
      if (!kbResponse.ok) {
        const error = await kbResponse.json().catch(() => ({}));
        throw new Error(error.detail || `HTTP ${kbResponse.status}`);
      }

      // 测试成功后自动保存配置并更新 store
      setApiKey(localApiKey);
      setApiBase(localApiBase);
      setConnected(true);
      toast.success("连接成功，配置已保存");
    } catch (error) {
      setConnected(false);
      toast.error(`连接失败: ${(error as Error).message}`);
    } finally {
      setIsTesting(false);
    }
  };

  const handleCreateKey = async () => {
    if (!client) return;
    setIsCreatingKey(true);
    try {
      const result = await client.createAPIKey(newKeyRole, newKeyName || undefined);
      setNewlyCreatedKey(result.key);
      toast.success("API Key 创建成功");
      loadAPIKeys();
    } catch (error) {
      toast.error(`创建失败: ${(error as Error).message}`);
    } finally {
      setIsCreatingKey(false);
    }
  };

  const handleDeleteKey = async (keyId: string) => {
    if (!client) return;
    if (!confirm("确定删除此 API Key？")) return;
    try {
      await client.deleteAPIKey(keyId);
      toast.success("API Key 已删除");
      loadAPIKeys();
    } catch (error) {
      toast.error(`删除失败: ${(error as Error).message}`);
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success("已复制到剪贴板");
  };

  const roleColors: Record<string, string> = {
    admin: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    write: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
    read: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  };

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold">设置</h1>
        <p className="text-muted-foreground">配置 API 连接和模型选项</p>
      </div>

      <Tabs defaultValue="api" className="space-y-4">
        <TabsList>
          <TabsTrigger value="api" className="flex items-center gap-2">
            <Server className="h-4 w-4" />
            API 配置
          </TabsTrigger>
          <TabsTrigger value="models" className="flex items-center gap-2">
            <Cpu className="h-4 w-4" />
            模型提供商
          </TabsTrigger>
        </TabsList>

        <TabsContent value="api" className="space-y-6">
      {/* API 配置 */}
      <Card>
        <CardHeader>
          <CardTitle>API 配置</CardTitle>
          <CardDescription>配置后端 API 连接信息</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="apiBase">API 地址</Label>
            <div className="flex gap-2">
              <Input
                id="apiBase"
                value={localApiBase}
                onChange={(e) => setLocalApiBase(e.target.value)}
                placeholder="http://localhost:8020"
                className="flex-1"
              />
              <Button
                variant="outline"
                size="icon"
                onClick={() => copyToClipboard(localApiBase)}
                title="复制 API 地址"
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="apiKey">API Key</Label>
            <div className="flex gap-2">
              <Input
                id="apiKey"
                type={showApiKey ? "text" : "password"}
                value={localApiKey}
                onChange={(e) => setLocalApiKey(e.target.value)}
                placeholder="kb_sk_..."
                className="flex-1"
              />
              <Button
                variant="outline"
                size="icon"
                onClick={() => setShowApiKey(!showApiKey)}
                title={showApiKey ? "隐藏 API Key" : "显示 API Key"}
              >
                {showApiKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
              <Button
                variant="outline"
                size="icon"
                onClick={() => copyToClipboard(localApiKey)}
                title="复制 API Key"
              >
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="flex items-center justify-between pt-4">
            <div className="flex items-center gap-2">
              <span className="text-sm text-muted-foreground">状态:</span>
              <Badge variant={isConnected ? "default" : "secondary"}>
                {isConnected ? (
                  <><Check className="h-3 w-3 mr-1" />已连接</>
                ) : (
                  <><X className="h-3 w-3 mr-1" />未连接</>
                )}
              </Badge>
              {currentRole && (
                <Badge className={roleColors[currentRole]}>
                  {currentRole}
                </Badge>
              )}
            </div>

            <div className="flex gap-2">
              <Button variant="outline" onClick={handleTestConnection} disabled={isTesting}>
                {isTesting ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <RefreshCw className="h-4 w-4 mr-2" />}
                测试连接
              </Button>
              <Button onClick={handleSave}>保存</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* API Key 管理 (仅 admin 可见) */}
      {currentRole === "admin" && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Key className="h-5 w-5" />
                  API Key 管理
                </CardTitle>
                <CardDescription>管理租户的 API Keys</CardDescription>
              </div>
              <Button onClick={() => { setShowCreateDialog(true); setNewlyCreatedKey(null); setNewKeyName(""); }}>
                <Plus className="h-4 w-4 mr-2" />
                创建 Key
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {isLoadingKeys ? (
              <div className="flex justify-center py-8">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : apiKeys.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                暂无其他 API Keys
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Key 前缀</TableHead>
                    <TableHead>名称</TableHead>
                    <TableHead>角色</TableHead>
                    <TableHead>创建时间</TableHead>
                    <TableHead className="w-16"></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {apiKeys.map((key) => (
                    <TableRow key={key.id}>
                      <TableCell className="font-mono">{key.prefix}...</TableCell>
                      <TableCell>{key.name || "-"}</TableCell>
                      <TableCell>
                        <Badge className={roleColors[key.role]}>{key.role}</Badge>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(key.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="text-destructive hover:text-destructive"
                          onClick={() => handleDeleteKey(key.id)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      {/* 关于 */}
      <Card>
        <CardHeader>
          <CardTitle>关于</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-1">
          <p>RAG Pipeline Console v1.0.0</p>
          <p>后端: Self-RAG Pipeline</p>
        </CardContent>
      </Card>
        </TabsContent>

        <TabsContent value="models" className="space-y-6">
          {isConnected ? (
            <div className="space-y-4">
              <ModelProviderConfig />
              <DefaultModelConfig />
            </div>
          ) : (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                请先在 API 配置中连接后端服务
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>

      {/* 创建 API Key 对话框 */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>创建新 API Key</DialogTitle>
            <DialogDescription>
              创建一个新的 API Key，请注意保存，Key 仅在创建时显示一次。
            </DialogDescription>
          </DialogHeader>

          {newlyCreatedKey ? (
            <div className="space-y-4">
              <div className="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
                <div className="flex items-center gap-2 text-green-700 dark:text-green-300 mb-2">
                  <Check className="h-4 w-4" />
                  <span className="font-medium">API Key 创建成功</span>
                </div>
                <div className="flex items-center gap-2">
                  <code className="flex-1 p-2 bg-background rounded text-sm break-all">
                    {newlyCreatedKey}
                  </code>
                  <Button size="icon" variant="outline" onClick={() => copyToClipboard(newlyCreatedKey)}>
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
              </div>
              <div className="flex items-start gap-2 text-amber-600 dark:text-amber-400 text-sm">
                <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                <span>请立即复制并保存此 Key，关闭对话框后将无法再次查看。</span>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label>名称 (可选)</Label>
                <Input
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  placeholder="例如: 生产环境"
                />
              </div>
              <div className="space-y-2">
                <Label>角色</Label>
                <Select value={newKeyRole} onValueChange={(v) => setNewKeyRole(v as "admin" | "write" | "read")}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="admin">admin - 全部权限</SelectItem>
                    <SelectItem value="write">write - 读写权限</SelectItem>
                    <SelectItem value="read">read - 只读权限</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          <DialogFooter>
            {newlyCreatedKey ? (
              <Button onClick={() => setShowCreateDialog(false)}>完成</Button>
            ) : (
              <>
                <Button variant="outline" onClick={() => setShowCreateDialog(false)}>取消</Button>
                <Button onClick={handleCreateKey} disabled={isCreatingKey}>
                  {isCreatingKey && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                  创建
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
