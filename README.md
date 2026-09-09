# 水脉 WaterPulse × AI Water Risk Copilot｜比赛整合版

版本：Integrated Competition V3｜2026-09-10

## 这是什么

本项目把学姐原 `water-risk-mvp` 的研究展示网站与 F 组 Water Risk Copilot AI Agent 合并为一个可部署网站：

- `/`：保留学姐原网站的视觉结构、地图/数据/方法展示，明确标记为“研究展示层”。
- `/copilot/`：F 组正式 AI Agent，可进行用户输入、字段映射、数据治理、D Baseline、Scenario、AI 解释、证据追溯、QA、报告与日志。
- `/api/*`：FastAPI 后端真实接口。

这样不需要继续依赖原 GitHub Pages 才能完成比赛演示；部署到 Railway 后一个网址即可同时访问展示层与 AI Agent。

## 为什么这样整合

原仓库实际有两套形态：

1. Streamlit MVP：`app.py + pages/ + utils/`，可交互但仍为早期规则/模拟计算版本。
2. GitHub Pages 静态站：`static_site/`，即之前公开链接使用的展示页面，数据主要写在 `site.js` 中。

比赛终版不能继续以旧静态数字作为正式结论，因此本整合版保留它的设计和展示价值，同时把正式可复算计算统一放进 Copilot。

## 当前技术链

用户资料 / Excel / CSV
→ 意图与字段需求
→ 字段映射与人工确认
→ B/C 数据查询适配器
→ `resolved_input` / D Baseline Schema
→ D `baseline_api.py v1.2`
→ Scenario
→ AI 角色化解释
→ Evidence / Version / Logs
→ Word 导出

正式风险数字不由大模型生成。

## 目录

```text
WaterPulse_Integrated_Competition/
├─ server.py                         # FastAPI 主入口
├─ main.py
├─ legacy_site/                      # 学姐原 GitHub Pages 展示层（已加 Copilot 入口）
├─ copilot_static/                   # F 组 AI Agent 前端
├─ agent/                            # Agent Router / 风险简报 / 可选 LLM
├─ tools/                            # 数据、Baseline、Scenario、导出工具
├─ deterministic/d_baseline/        # D Baseline API / Schema / 黄金样例
├─ engines/                          # Scenario 引擎
├─ data/                             # 当前注册数据快照
├─ tests/
├─ logs/
├─ outputs/
├─ requirements.txt
├─ railway.json
└─ Procfile
```

## 本地运行

```bash
pip install -r requirements.txt
uvicorn server:app --host 0.0.0.0 --port 7860
```

打开：

- 研究展示：http://127.0.0.1:7860/
- AI Copilot：http://127.0.0.1:7860/copilot/
- 健康检查：http://127.0.0.1:7860/api/health

## Railway 部署

### 最重要

不要只把本项目 ZIP 上传到 GitHub。

必须先解压，然后把 `server.py`、`requirements.txt`、`railway.json`、`legacy_site/`、`copilot_static/` 等实际文件提交到 GitHub 仓库根目录。

Railway 启动命令：

```bash
uvicorn server:app --host 0.0.0.0 --port $PORT
```

部署后根域名即为研究展示网站，点击侧边栏 **AI Water Risk Copilot** 可进入正式 Agent。

## 当前边界

- 学姐旧页面中的 2026-08 MVP 静态指标仍保留用于展示历史页面设计，但页面顶部已明确标记为“研究展示层”，不应作为比赛最终风险结论。
- 正式风险结果以 `/copilot/` 调用 D Baseline / Scenario 后生成的 JSON、Evidence 与日志为准。
- 宋梓铭最终数据查询 kernel 到位后，仅替换 `tools/query_adapter.py`，不需要重写前端和 Agent。
- D 的黄金样例若与 D 当前 API 存在不一致，QA 页面会显示，不由 F 静默修改公式。
- Scenario 最终仍需由 E/D 对齐唯一 Baseline 内核后做最终验收。

## 验证

当前整合包已完成：

- `/` 展示层可访问
- `/copilot/` Agent 可访问
- `/api/health` 正常
- 现有自动测试：`3 passed`

