#!/usr/bin/env bash
set -euo pipefail

# =====================================================
# 注册 pdf-analysis skill 到 OpenClaw 配置
# =====================================================

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/openclaw/skills"
SKILL_KEY="pdf-analysis"
SKILL_DIR="$SKILLS_DIR/$SKILL_KEY"

# 检查依赖
if ! command -v openclaw >/dev/null 2>&1; then
  echo "openclaw 未安装或不在 PATH 中。" >&2
  exit 1
fi

if ! command -v jq >/dev/null 2>&1; then
  echo "jq 未安装或不在 PATH 中。" >&2
  exit 1
fi

if [[ ! -f "$SKILL_DIR/SKILL.md" ]]; then
  echo "未找到 skill 文件: $SKILL_DIR/SKILL.md" >&2
  exit 1
fi

# 配置 OpenClaw 加载 skills 目录
CONFIG_FILE="$HOME/.openclaw/openclaw.json"
if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "未找到 OpenClaw 配置文件: $CONFIG_FILE" >&2
  echo "请先运行 openclaw 完成初始化。" >&2
  exit 1
fi

# 将 skills 目录加入 OpenClaw extraDirs
tmp_config="$(mktemp)"
jq --arg d "$SKILLS_DIR" '
  .skills = (.skills // {}) |
  .skills.load = (.skills.load // {}) |
  .skills.load.extraDirs = ((.skills.load.extraDirs // []) + [$d] | unique)
' "$CONFIG_FILE" >"$tmp_config"
mv "$tmp_config" "$CONFIG_FILE"

# 赋予脚本执行权限
chmod +x "$SKILL_DIR/scripts/ragforge_pdf.py"

echo "✅ pdf-analysis skill 已注册到 OpenClaw。"
echo "   Skill 目录: $SKILL_DIR"
echo "   配置文件: $CONFIG_FILE"
echo ""
echo "📝 下一步："
echo "   1. 如需覆盖默认回退逻辑，可编辑 $SKILL_DIR/config.env 配置 RAGFORGE_API_KEY"
echo "   2. 重启 OpenClaw Gateway（openclaw gateway restart）"
echo "   3. 对 OpenClaw 说：'帮我分析这个 PDF 文件并导出 Excel，同时入库到项目管理知识库' 即可触发 pdf-analysis skill"
