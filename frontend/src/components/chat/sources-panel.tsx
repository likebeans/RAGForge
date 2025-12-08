"use client";

import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";
import { FileText, ChevronDown, ChevronRight, ExternalLink } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { SourceItem } from "@/lib/api";

interface SourcesPanelProps {
  sources: SourceItem[];
}

// 根据分数获取颜色类名
function getScoreColor(score: number): { bg: string; bar: string; text: string } {
  if (score >= 0.8) {
    return {
      bg: "bg-emerald-50 dark:bg-emerald-950/30",
      bar: "bg-emerald-500",
      text: "text-emerald-700 dark:text-emerald-400"
    };
  }
  if (score >= 0.6) {
    return {
      bg: "bg-blue-50 dark:bg-blue-950/30",
      bar: "bg-blue-500",
      text: "text-blue-700 dark:text-blue-400"
    };
  }
  return {
    bg: "bg-amber-50 dark:bg-amber-950/30",
    bar: "bg-amber-500",
    text: "text-amber-700 dark:text-amber-400"
  };
}

export function SourcesPanel({ sources }: SourcesPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  if (!sources || sources.length === 0) return null;

  return (
    <Collapsible
      open={isOpen}
      onOpenChange={setIsOpen}
      className="mt-4 rounded-xl border border-border/60 bg-card/50 backdrop-blur-sm overflow-hidden transition-all duration-200"
    >
      {/* 触发器头部 */}
      <CollapsibleTrigger className="flex items-center gap-3 px-4 py-3 w-full hover:bg-muted/40 transition-colors text-left group">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-primary/10 group-hover:bg-primary/15 transition-colors">
          <FileText className="h-4 w-4 text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">引用来源</span>
            <Badge variant="secondary" className="text-xs px-2 h-5 font-normal">
              {sources.length} 条
            </Badge>
          </div>
          <p className="text-xs text-muted-foreground mt-0.5">
            点击展开查看检索到的相关文档片段
          </p>
        </div>
        <div className={cn(
          "transition-transform duration-200",
          isOpen && "rotate-180"
        )}>
          <ChevronDown className="h-4 w-4 text-muted-foreground" />
        </div>
      </CollapsibleTrigger>
      
      {/* 来源列表 */}
      <CollapsibleContent>
        <div className="px-4 pb-4 space-y-2 border-t border-border/40 pt-3">
          {sources.map((src, i) => {
            const colors = getScoreColor(src.score);
            const isExpanded = expandedIndex === i;
            
            return (
              <div 
                key={i} 
                className={cn(
                  "rounded-lg border border-border/40 overflow-hidden transition-all duration-200",
                  "hover:border-border hover:shadow-sm",
                  isExpanded && "ring-1 ring-primary/20"
                )}
              >
                {/* 来源项头部 */}
                <div 
                  className={cn(
                    "flex items-start gap-3 p-3 cursor-pointer transition-colors",
                    colors.bg
                  )}
                  onClick={() => setExpandedIndex(isExpanded ? null : i)}
                >
                  {/* 序号 */}
                  <div className={cn(
                    "flex items-center justify-center w-6 h-6 rounded-full text-xs font-semibold shrink-0",
                    colors.bar, "text-white"
                  )}>
                    {i + 1}
                  </div>
                  
                  {/* 标题和元信息 */}
                  <div className="flex-1 min-w-0 space-y-1.5">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-medium truncate" title={src.document_title || "未命名文档"}>
                        {src.document_title || "未命名文档"}
                      </span>
                      {src.chunk_id && (
                        <span className="text-[10px] text-muted-foreground px-1.5 py-0.5 bg-background/80 rounded shrink-0" title={`Chunk ID: ${src.chunk_id}`}>
                          #{src.chunk_id.slice(0, 6)}
                        </span>
                      )}
                    </div>
                    
                    {/* 相关度进度条 */}
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-1.5 bg-background/60 rounded-full overflow-hidden">
                        <div 
                          className={cn("h-full rounded-full transition-all duration-300", colors.bar)}
                          style={{ width: `${Math.min(src.score * 100, 100)}%` }}
                        />
                      </div>
                      <span className={cn("text-xs font-medium tabular-nums", colors.text)}>
                        {(src.score * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  
                  {/* 展开指示器 */}
                  <ChevronRight className={cn(
                    "h-4 w-4 text-muted-foreground shrink-0 transition-transform duration-200",
                    isExpanded && "rotate-90"
                  )} />
                </div>
                
                {/* 展开的文本内容 */}
                <div className={cn(
                  "overflow-hidden transition-all duration-200",
                  isExpanded ? "max-h-96" : "max-h-0"
                )}>
                  <div className="px-3 pb-3 pt-0">
                    <div className="p-3 bg-muted/30 rounded-lg border-l-2 border-primary/30">
                      <p className="text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap">
                        {src.text}
                      </p>
                    </div>
                  </div>
                </div>
                
                {/* 未展开时显示预览 */}
                {!isExpanded && (
                  <div className="px-3 pb-3 pt-0">
                    <p className="text-xs text-muted-foreground/70 line-clamp-2 leading-relaxed">
                      {src.text}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </CollapsibleContent>
    </Collapsible>
  );
}
