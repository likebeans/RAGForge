"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { useAppStore } from "@/lib/store";
import { GroundInfo } from "@/lib/api";
import { Plus, Trash2, Database, Save } from "lucide-react";

export default function GroundListPage() {
  const router = useRouter();
  const { client, isConnected } = useAppStore();
  const [grounds, setGrounds] = useState<GroundInfo[]>([]);
  const [name, setName] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const load = async () => {
    if (!client || !isConnected) return;
    setIsLoading(true);
    try {
      const res = await client.listGrounds();
      setGrounds(res.items || []);
    } catch (error) {
      console.error(error);
      toast.error("加载 ground 列表失败");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [client, isConnected]);

  const createGround = async () => {
    if (!client) return;
    try {
      const ground = await client.createGround(name || undefined);
      toast.success("已创建 ground");
      setName("");
      router.push(`/compare/${ground.ground_id}`);
    } catch (error) {
      toast.error(`创建失败: ${(error as Error).message}`);
    }
  };

  const deleteGround = async (groundId: string, saved: boolean) => {
    if (!client) return;
    if (saved) {
      toast.error("已保存的 ground 不能直接删除");
      return;
    }
    if (!confirm("确定删除此 ground？临时知识库将一并删除。")) return;
    try {
      await client.deleteGround(groundId);
      toast.success("已删除");
      load();
    } catch (error) {
      toast.error(`删除失败: ${(error as Error).message}`);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Playground Ground</h1>
          <p className="text-muted-foreground">创建多个 ground，分别上传文件和测试不同流水线。</p>
        </div>
        <div className="flex items-center gap-2">
          <Input
            placeholder="输入名称（可选）"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-52"
          />
          <Button onClick={createGround} disabled={!isConnected}>
            <Plus className="h-4 w-4 mr-1" />
            新建 Ground
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {grounds.map((g) => (
          <Card key={g.ground_id} className="hover:shadow-md transition-shadow">
            <CardHeader className="pb-3">
              <CardTitle className="flex items-center gap-2">
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-primary/10">
                  <Database className="h-4 w-4 text-primary" />
                </span>
                {g.name}
                {g.saved ? (
                  <Badge variant="secondary" className="gap-1">
                    <Save className="h-3 w-3" />
                    已保存
                  </Badge>
                ) : (
                  <Badge variant="outline">临时</Badge>
                )}
              </CardTitle>
              <CardDescription>
                {g.document_count} 个文件 · {new Date(g.created_at).toLocaleString()}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex items-center justify-between">
              <Button variant="outline" onClick={() => router.push(`/compare/${g.ground_id}`)}>
                进入
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="text-destructive"
                onClick={() => deleteGround(g.ground_id, g.saved)}
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            </CardContent>
          </Card>
        ))}
        {grounds.length === 0 && !isLoading && (
          <div className="text-muted-foreground">暂无 ground，创建一个开始实验。</div>
        )}
      </div>
    </div>
  );
}
