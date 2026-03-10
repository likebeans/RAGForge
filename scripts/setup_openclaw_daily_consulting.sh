#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/openclaw/skills"
SKILL_KEY="innovation-daily"
SKILL_DIR="$SKILLS_DIR/$SKILL_KEY"
JOB_NAME="${JOB_NAME:-daily-innovation-consulting}"
CRON_EXPR="${CRON_EXPR:-0 9 * * *}"
TZ_NAME="${TZ_NAME:-Asia/Shanghai}"
RUN_NOW="${RUN_NOW:-1}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-1800}"

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

CONFIG_FILE="$HOME/.openclaw/openclaw.json"
if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "未找到 OpenClaw 配置文件: $CONFIG_FILE" >&2
  exit 1
fi

tmp_config="$(mktemp)"
jq --arg d "$SKILLS_DIR" '
  .skills = (.skills // {}) |
  .skills.load = (.skills.load // {}) |
  .skills.load.extraDirs = ((.skills.load.extraDirs // []) + [$d] | unique)
' "$CONFIG_FILE" >"$tmp_config"
mv "$tmp_config" "$CONFIG_FILE"

feishu_key="$(
  openclaw sessions --all-agents --json \
  | jq -r '[.sessions[] | select((.key | type == "string") and (.key | test("^agent:[^:]+:feishu:[^:]+:")))] | max_by(.updatedAt) | .key // ""'
)"

if [[ -z "$feishu_key" ]]; then
  echo "未找到飞书会话目标。请先和飞书机器人产生一次会话后重试。" >&2
  exit 1
fi

feishu_target="$(awk -F: '{print $NF}' <<<"$feishu_key")"
if [[ -z "$feishu_target" ]]; then
  echo "飞书目标解析失败，原始会话键: $feishu_key" >&2
  exit 1
fi

sources_csv="$(awk 'NF { printf "%s%s", (seen ? ", " : ""), $0; seen=1 }' "$SKILL_DIR/sources.txt")"

read -r -d '' prompt <<EOF || true
请严格使用 ${SKILL_KEY} skill 生成今日创新药资讯，并输出中文。
仅允许使用以下权威来源白名单：${sources_csv}
必须包含：
1) 重点速览（3-5条）
2) 详细资讯（每条含 标题/日期/来源/要点/链接）
3) 监管与临床信号
4) 风险提示
请确保结论可追溯，避免使用非白名单来源作为结论依据。
EOF

jobs_json="$(openclaw cron list --all --json)"
existing_job_id="$(jq -r --arg name "$JOB_NAME" '.jobs[]? | select(.name == $name) | .id' <<<"$jobs_json" | head -n1)"

if [[ -n "$existing_job_id" ]]; then
  openclaw cron edit "$existing_job_id" \
    --enable \
    --name "$JOB_NAME" \
    --cron "$CRON_EXPR" \
    --tz "$TZ_NAME" \
    --timeout-seconds "$TIMEOUT_SECONDS" \
    --light-context \
    --session isolated \
    --announce \
    --channel feishu \
    --to "$feishu_target" \
    --agent main \
    --message "$prompt" >/dev/null
  job_id="$existing_job_id"
else
  job_json="$(
    openclaw cron add \
      --name "$JOB_NAME" \
      --cron "$CRON_EXPR" \
      --tz "$TZ_NAME" \
      --timeout-seconds "$TIMEOUT_SECONDS" \
      --light-context \
      --session isolated \
      --announce \
      --channel feishu \
      --to "$feishu_target" \
      --agent main \
      --message "$prompt" \
      --json
  )"
  job_id="$(jq -r '.id' <<<"$job_json")"
fi

echo "已配置 daily 咨询推送任务。"
echo "job_id: $job_id"
echo "feishu_target: $feishu_target"
echo "cron: $CRON_EXPR ($TZ_NAME)"

if [[ "$RUN_NOW" == "1" ]]; then
  echo "正在执行 run-now 验证..."
  openclaw cron run "$job_id" --expect-final --timeout 180000
  echo "run-now 已触发。"
fi

echo "最近一次运行记录："
openclaw cron runs --id "$job_id" --limit 1
