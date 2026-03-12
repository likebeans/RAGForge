# 项目入库 API 使用指南

> **服务地址**：`http://<服务器IP>:3002`
> **认证方式**：Bearer Token（JWT）
> **Content-Type**：`application/json`

---

## Step 1 — 登录获取 Token

```bash
curl -X POST http://<host>:3002/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "your_password"}'
```

**响应：**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

> 后续所有请求在 Header 中带上：`Authorization: Bearer <access_token>`

---

## Step 2 — 新增项目（入库）

### 接口信息

| 项目 | 值 |
|------|-----|
| **方法** | `POST` |
| **路径** | `/api/projects` |
| **权限** | 管理员 |

> `id` 无需传递，服务端自动生成 UUID。

### 请求体字段说明

> 只有 `project_name` 必填，其余字段全部可选。

#### 基本信息（写入 `project_master` 表）

| 字段 | 类型 | 必填 | 说明 | 示例 |
|------|------|------|------|------|
| `project_name` | string | **是** | 项目名称（唯一，不可重复） | `"BTK抑制剂"` |
| `target_name` | string | 否 | 靶点名称（自动匹配/创建靶点记录） | `"BTK"` |
| `indication` | string | 否 | 适应症 | `"B细胞淋巴瘤"` |
| `dev_phase` | enum | 否 | 研发阶段，见下方枚举表 | `"PHASE_II"` |
| `overall_status` | enum | 否 | 项目状态，默认 `SCREENING` | `"IN_PROGRESS"` |
| `overall_score` | float | 否 | 综合评分 0~10 | `7.5` |

#### 研发详情（写入 `project_details` 表）

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `drug_type` | string | 药物类型 | `"small_molecule"` / `"biologic"` / `"adc"` |
| `dosage_form` | string | 剂型 | `"tablet"` / `"injection"` / `"capsule"` |
| `mechanism` | string | 作用机制 | `"BTK共价不可逆抑制"` |
| `project_highlights` | string | 项目亮点 | `"高选择性，脑渗透率强"` |
| `differentiation` | string | 差异化优势 | `"vs. 伊布替尼耐药突变有效"` |
| `current_therapy` | string | 当前标准疗法 | `"利妥昔单抗+化疗"` |
| `efficacy_indicators` | object | 药效指标 JSON | `{"ORR": "75%", "PFS": "18个月"}` |
| `safety_indicators` | object | 安全性指标 JSON | `{"Grade3_AE": "12%"}` |

#### 商业估值（写入 `project_valuations` 表）

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `asking_price` | float | 报价（万元） | `15000` |
| `project_valuation` | float | 项目估值（万元） | `80000` |
| `company_valuation` | float | 公司估值（万元） | `200000` |
| `strategic_fit_score` | float | 战略匹配度 0~10 | `8.0` |
| `valuation_date` | string | 估值日期，ISO8601，默认当天 | `"2026-03-12T00:00:00"` |

#### 研究信息（写入 `research_details` 表）

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `market_json` | object | 市场信息 | `{"market_size_bn": 5.2, "cagr": "18%"}` |
| `competitor_data` | object | 竞品数据 | `{"competitors": ["伊布替尼", "泽布替尼"]}` |
| `patent_json` | object | 专利信息 | `{"patent_no": "CN20251234"}` |
| `policy_impact` | string | 政策影响 | `"已纳入优先审评"` |

#### 管理信息（写入 `project_management_info` 表）

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `risk_notes` | string | 风险提示 | `"三期数据Q3揭盲，存在数据风险"` |
| `follow_up_records` | array | 跟进记录列表 | `[{"date": "2026-03-01", "note": "首次接触"}]` |

---

### 完整请求示例

```bash
TOKEN="your_access_token_here"

curl -X POST http://<host>:3002/api/projects \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "BTK抑制剂-新一代",
    "target_name": "BTK",
    "indication": "慢性淋巴细胞白血病",
    "dev_phase": "PHASE_II",
    "overall_status": "IN_PROGRESS",
    "overall_score": 8.2,

    "drug_type": "small_molecule",
    "dosage_form": "tablet",
    "mechanism": "BTK共价不可逆抑制，克服C481S耐药突变",
    "project_highlights": "对伊布替尼耐药患者有效",
    "asking_price": 20000,
    "project_valuation": 100000,
    "strategic_fit_score": 8.5,

    "market_json": {"market_size_bn": 8.5, "cagr": "22%"},
    "risk_notes": "尚未完成PK/PD研究"
  }'
```

### 成功响应（`200 OK`）

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "project_name": "BTK抑制剂-新一代",
  "target_id": "TGT-BTK",
  "target_name": "BTK",
  "indication": "慢性淋巴细胞白血病",
  "dev_phase": "PHASE_II",
  "overall_status": "IN_PROGRESS",
  "overall_score": 8.2,
  "drug_type": "small_molecule",
  "dosage_form": "tablet",
  "asking_price": 20000.0,
  "created_at": "2026-03-12T07:44:38Z"
}
```

---

## Step 3 — 查询已入库项目

### 获取列表

```bash
curl "http://<host>:3002/api/projects?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"
```

**支持的筛选参数：**

| 参数 | 说明 | 示例 |
|------|------|------|
| `keyword` | 按项目名/适应症模糊搜索 | `"BTK"` |
| `drug_type` | 按药物类型精确过滤 | `"small_molecule"` |
| `dev_phase` | 按研发阶段过滤 | `"PHASE_II"` |
| `score_min` | 评分下限 | `7` |
| `score_max` | 评分上限 | `9` |
| `sort_by` | 排序字段（`created_at` / `overall_score` / `project_name`） | `"overall_score"` |
| `sort_order` | 排序方向 `asc` / `desc` | `"desc"` |

### 获取单条详情

```bash
curl "http://<host>:3002/api/projects/<project_id>" \
  -H "Authorization: Bearer $TOKEN"
```

---

## Step 4 — 更新项目

### 接口信息

| 项目 | 值 |
|------|-----|
| **方法** | `PUT` |
| **路径** | `/api/projects/<project_id>` |
| **权限** | 管理员 |

> 所有字段均为可选，只传需要修改的字段。

```bash
curl -X PUT http://<host>:3002/api/projects/<project_id> \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project_name": "BTK抑制剂-新一代（更名）",
    "overall_score": 9.0,
    "detail": {
      "mechanism": "更新后的作用机制描述"
    }
  }'
```

---

## 枚举值参考

### `dev_phase` 研发阶段

| 传值 | 含义 |
|------|------|
| `PRE_CLINICAL` | 临床前 |
| `PHASE_I` | I 期 |
| `PHASE_II` | II 期 |
| `PHASE_III` | III 期 |
| `NDA` | 上市申请 |
| `APPROVED` | 已上市 |

### `overall_status` 项目状态

| 传值 | 含义 |
|------|------|
| `SCREENING` | 初筛（默认） |
| `IN_PROGRESS` | 进行中 |
| `MONITORING` | 监控 |
| `ARCHIVED` | 归档 |
| `RESTARTED` | 已重启 |

### `drug_type` 药物类型（常用值）

| 传值 | 含义 |
|------|------|
| `small_molecule` | 小分子药 |
| `biologic` | 生物制品（抗体等） |
| `adc` | 抗体偶联药物 |
| `cell_therapy` | 细胞治疗 |
| `gene_therapy` | 基因治疗 |

---

## 常见错误

| HTTP 状态码 | 原因 | 解决方法 |
|------------|------|---------|
| `401` | Token 未提供或已过期 | 重新登录获取 Token |
| `403` | 账号无管理员权限 | 联系管理员授权 |
| `409` | `project_name` 已存在（唯一约束冲突） | 换一个不重复的项目名称 |
| `422` | 请求体字段有误（枚举值不对/必填项缺失） | 检查 `dev_phase` 等枚举字段是否使用英文常量 |
| `500` | 服务内部错误 | 联系后端负责人排查 |

---

> 💡 **Swagger 在线文档**：在测试环境访问 `http://<host>:3002/docs` 可直接在浏览器测试所有接口。
