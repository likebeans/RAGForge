# 创新药项目筛选过滤功能开发方案

## 1. 项目概述

### 1.1 目标

基于「创新药项目管理表模板1.0.xlsx」的数据结构，在 yaoyan 系统中新增**项目筛选过滤**功能，支持：

- 多维度条件筛选
- 数据导入/导出（Excel）
- 项目详情查看与编辑

### 1.2 数据来源分析

Excel 模板包含 **7 大类、25 个字段**：

| 分类 | 字段 |
|------|------|
| **基础信息** | 项目/药物名称、靶点、靶点类型、作用机制 |
| **研发属性** | 药物类型、药物剂型、研究阶段 |
| **核心价值** | 适应症、适应症类型、项目亮点、差异化创新点 |
| **临床数据** | 主要药效指标、主要安全性指标、当前标准疗法及疗效 |
| **竞争与专利** | 赛道竞争情况、专利情况、专利布局 |
| **估值与评分** | 报价与估值、项目估值、公司估值、综合评分、战略匹配度 |
| **辅助管理** | 研发机构、项目负责人/创始人、风险提示 |

---

## 2. 数据库设计

### 2.1 主表：drug_projects

```sql
CREATE TABLE drug_projects (
    id SERIAL PRIMARY KEY,
    
    -- 基础信息
    project_name VARCHAR(200) NOT NULL,          -- 项目/药物名称
    target VARCHAR(100),                          -- 靶点
    target_type VARCHAR(50),                      -- 靶点类型（GPCR、激酶、抗体靶点等）
    mechanism VARCHAR(500),                       -- 作用机制
    
    -- 研发属性
    drug_type VARCHAR(50),                        -- 药物类型（小分子药、生物药、ADC等）
    dosage_form VARCHAR(50),                      -- 药物剂型（片剂、注射剂、胶囊等）
    research_stage VARCHAR(50),                   -- 研究阶段（临床前、I期、II期、III期、上市申请）
    
    -- 核心价值
    indication VARCHAR(200),                      -- 适应症
    indication_type VARCHAR(100),                 -- 适应症类型（肿瘤、自身免疫性疾病等）
    project_highlights TEXT,                      -- 项目亮点
    differentiation TEXT,                         -- 差异化创新点
    
    -- 临床数据
    efficacy_indicators TEXT,                     -- 主要药效指标
    safety_indicators TEXT,                       -- 主要安全性指标
    current_therapy TEXT,                         -- 当前标准疗法及疗效
    
    -- 竞争与专利
    competition_status TEXT,                      -- 赛道竞争情况
    patent_status TEXT,                           -- 专利情况
    patent_layout TEXT,                           -- 专利布局
    
    -- 估值与评分
    asking_price DECIMAL(15, 2),                  -- 报价与估值（万元）
    project_valuation DECIMAL(15, 2),             -- 项目估值（万元）
    company_valuation DECIMAL(15, 2),             -- 公司估值（万元）
    overall_score DECIMAL(3, 1),                  -- 综合评分（0-10）
    strategic_fit_score DECIMAL(3, 1),            -- 战略匹配度（0-10）
    
    -- 辅助管理
    research_institution VARCHAR(200),            -- 研发机构
    project_leader VARCHAR(200),                  -- 项目负责人/创始人
    risk_notes TEXT,                              -- 风险提示
    
    -- 系统字段
    created_by VARCHAR(36) REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE
);

-- 索引
CREATE INDEX idx_drug_projects_name ON drug_projects(project_name);
CREATE INDEX idx_drug_projects_target ON drug_projects(target);
CREATE INDEX idx_drug_projects_drug_type ON drug_projects(drug_type);
CREATE INDEX idx_drug_projects_stage ON drug_projects(research_stage);
CREATE INDEX idx_drug_projects_indication ON drug_projects(indication);
CREATE INDEX idx_drug_projects_score ON drug_projects(overall_score);
```

### 2.2 枚举值字典表

```sql
CREATE TABLE dict_items (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,    -- 字典分类
    code VARCHAR(50) NOT NULL,        -- 编码
    label VARCHAR(100) NOT NULL,      -- 显示名称
    sort_order INTEGER DEFAULT 0,     -- 排序
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(category, code)
);

-- 初始数据
INSERT INTO dict_items (category, code, label, sort_order) VALUES
-- 靶点类型
('target_type', 'gpcr', 'GPCR', 1),
('target_type', 'kinase', '激酶', 2),
('target_type', 'antibody', '抗体靶点', 3),
('target_type', 'ion_channel', '离子通道', 4),
('target_type', 'nuclear_receptor', '核受体', 5),
('target_type', 'other', '其他', 99),

-- 药物类型
('drug_type', 'small_molecule', '小分子药', 1),
('drug_type', 'biologic', '生物药', 2),
('drug_type', 'adc', 'ADC', 3),
('drug_type', 'cell_therapy', '细胞治疗', 4),
('drug_type', 'gene_therapy', '基因治疗', 5),
('drug_type', 'other', '其他', 99),

-- 药物剂型
('dosage_form', 'tablet', '片剂', 1),
('dosage_form', 'injection', '注射剂', 2),
('dosage_form', 'capsule', '胶囊', 3),
('dosage_form', 'oral_solution', '口服液', 4),
('dosage_form', 'patch', '贴剂', 5),
('dosage_form', 'other', '其他', 99),

-- 研究阶段
('research_stage', 'preclinical', '临床前', 1),
('research_stage', 'phase1', 'I期', 2),
('research_stage', 'phase2', 'II期', 3),
('research_stage', 'phase3', 'III期', 4),
('research_stage', 'nda', '上市申请', 5),
('research_stage', 'approved', '已上市', 6),

-- 适应症类型
('indication_type', 'oncology', '肿瘤', 1),
('indication_type', 'autoimmune', '自身免疫性疾病', 2),
('indication_type', 'infectious', '感染性疾病', 3),
('indication_type', 'cardiovascular', '心血管疾病', 4),
('indication_type', 'neurological', '神经系统疾病', 5),
('indication_type', 'metabolic', '代谢性疾病', 6),
('indication_type', 'rare_disease', '罕见病', 7),
('indication_type', 'other', '其他', 99);
```

---

## 3. API 设计

### 3.1 项目管理接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/projects` | 分页查询项目列表（支持筛选） |
| GET | `/api/projects/{id}` | 获取项目详情 |
| POST | `/api/projects` | 创建项目 |
| PUT | `/api/projects/{id}` | 更新项目 |
| DELETE | `/api/projects/{id}` | 删除项目 |

### 3.2 筛选查询参数

```
GET /api/projects?
    page=1&
    page_size=20&
    keyword=关键词&                    # 模糊搜索（名称、靶点、适应症）
    target_type=gpcr,kinase&          # 靶点类型（多选）
    drug_type=small_molecule&         # 药物类型（多选）
    research_stage=phase2,phase3&     # 研究阶段（多选）
    indication_type=oncology&         # 适应症类型（多选）
    score_min=7&                      # 综合评分最小值
    score_max=10&                     # 综合评分最大值
    valuation_min=1000&               # 估值最小值（万元）
    valuation_max=50000&              # 估值最大值（万元）
    sort_by=overall_score&            # 排序字段
    sort_order=desc                   # 排序方向
```

### 3.3 导入/导出接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/projects/import` | 导入 Excel 文件 |
| GET | `/api/projects/export` | 导出为 Excel（支持筛选条件） |
| GET | `/api/projects/template` | 下载导入模板 |

**导入请求**：
```
POST /api/projects/import
Content-Type: multipart/form-data

file: <Excel文件>
mode: append | replace  # 追加或替换
```

**导出请求**：
```
GET /api/projects/export?
    format=xlsx&
    <筛选参数...>
```

### 3.4 字典接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/dicts/{category}` | 获取字典项列表 |
| GET | `/api/dicts` | 获取所有字典（用于筛选器初始化） |

---

## 4. 前端设计

### 4.1 页面结构

```
/projects                    # 项目列表页
├── 筛选面板（左侧/顶部）
│   ├── 关键词搜索框
│   ├── 靶点类型（多选下拉）
│   ├── 药物类型（多选下拉）
│   ├── 研究阶段（多选标签）
│   ├── 适应症类型（多选下拉）
│   ├── 综合评分（滑块范围）
│   ├── 估值范围（数值输入）
│   └── 重置/应用按钮
├── 工具栏
│   ├── 导入按钮
│   ├── 导出按钮
│   └── 新建按钮
├── 项目表格/卡片列表
│   ├── 支持列排序
│   ├── 支持分页
│   └── 支持行点击查看详情
└── 项目详情抽屉/弹窗

/projects/{id}               # 项目详情页（可选）
```

### 4.2 组件设计

```
src/pages/
├── Projects/
│   ├── index.jsx            # 项目列表主页
│   ├── ProjectFilter.jsx    # 筛选面板组件
│   ├── ProjectTable.jsx     # 表格组件
│   ├── ProjectCard.jsx      # 卡片组件（可选）
│   ├── ProjectDetail.jsx    # 详情抽屉
│   ├── ProjectForm.jsx      # 新建/编辑表单
│   └── ImportDialog.jsx     # 导入对话框
```

### 4.3 筛选交互

1. **即时筛选**：筛选条件变化后自动刷新列表
2. **URL 同步**：筛选条件同步到 URL 参数，支持分享/书签
3. **筛选标签**：已选条件显示为标签，支持单独删除
4. **保存筛选**：用户可保存常用筛选条件组合（可选）

---

## 5. 技术实现

### 5.1 后端实现

**目录结构**：
```
backend/app/
├── models/
│   ├── project.py           # 项目模型
│   └── dict_item.py         # 字典模型
├── schemas/
│   └── project.py           # Pydantic schemas
├── services/
│   ├── project_service.py   # 项目服务
│   └── import_service.py    # 导入导出服务
├── api/routes/
│   ├── projects.py          # 项目路由
│   └── dicts.py             # 字典路由
```

**依赖新增**：
```toml
# pyproject.toml
[project.dependencies]
openpyxl = "^3.1.0"          # Excel 读写
```

### 5.2 前端实现

**依赖新增**：
```json
// package.json
{
  "dependencies": {
    "xlsx": "^0.18.5"        // Excel 解析（可选，后端处理更安全）
  }
}
```

---

## 6. 开发计划

### 6.1 任务分解

| 阶段 | 任务 | 预估时间 |
|------|------|---------|
| **P1** | 数据库迁移（表结构+初始数据） | 1 小时 |
| **P2** | 后端 CRUD API | 2 小时 |
| **P3** | 后端筛选查询 | 1.5 小时 |
| **P4** | 后端导入/导出 | 2 小时 |
| **P5** | 前端列表页+筛选 | 3 小时 |
| **P6** | 前端详情+表单 | 2 小时 |
| **P7** | 前端导入/导出 | 1.5 小时 |
| **P8** | 测试与优化 | 2 小时 |

**总计：约 15 小时**

### 6.2 里程碑

| 里程碑 | 完成标准 |
|--------|---------|
| **M1: 可查询** | 数据库表创建，项目 CRUD API 可用 |
| **M2: 可筛选** | 前端筛选页面可用，支持多条件组合 |
| **M3: 可导入导出** | Excel 导入导出功能完整 |

---

## 7. 扩展考虑

### 7.1 未来功能

- **筛选条件保存**：用户保存常用筛选组合
- **数据统计图表**：按阶段/类型/适应症统计
- **项目对比**：多项目并排对比
- **审批流程**：项目评审流程
- **权限控制**：不同角色查看不同项目

### 7.2 性能优化

- 大数据量时考虑 Elasticsearch 全文检索
- 导出大量数据时使用异步任务+下载链接
- 前端虚拟滚动处理长列表

---

## 文档版本

| 版本 | 日期 | 修改内容 |
|------|------|---------|
| v1.0 | 2026-01-26 | 初始版本 |
