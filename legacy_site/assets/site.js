const NAV = [
  ["0", "⌂", "首页总览", "index.html", "home"],
  ["1", "↥", "数据导入", "data-import.html", "import"],
  ["2", "◉", "数据资源库", "data-library.html", "library"],
  ["3", "▱", "供应链地图", "supply-map.html", "map"],
  ["4", "◌", "风险敞口", "risk-exposure.html", "risk"],
  ["5", "☁", "压力测试", "stress-test.html", "stress"],
  ["6", "☷", "Agent 分析", "agent-analysis.html", "agent"],
  ["7", "▤", "报告导出", "report-export.html", "report"]
];

const NODES = [
  ["S002", "甜菜", "新疆甜菜供应商", "中国新疆", 0.293, 0.413, "高风险", "公开披露"],
  ["S003", "大豆", "爱荷华大豆供应商", "美国爱荷华", 0.149, 0.312, "低风险", "公开披露"],
  ["S008", "茶叶", "云南茶叶供应商", "中国云南", 0.088, 0.458, "高风险", "工作假设"],
  ["S005", "番茄", "山东番茄供应商", "中国山东", 0.085, 0.408, "高风险", "工作假设"],
  ["S010", "甘蔗", "广西甘蔗供应商", "中国广西", 0.053, 0.447, "高风险", "公开披露"],
  ["S001", "大豆", "巴西大豆供应商", "巴西马托格罗索", 0.067, 0.363, "中风险", "公开披露"],
  ["S004", "甘蔗", "云南甘蔗供应商", "中国云南", 0.050, 0.198, "低风险", "公开披露"]
];

const META = {
  home: ["项目总览 · PHASE 1 MVP", "甲公司上游原材料水风险总览", "植物基蛋白核心原料的采购组合水风险入口。数据来自公开披露与本地样本库匹配结果，工作假设字段将在报告中如实说明，不作为企业真实结论。"],
  import: ["工作流 · 第 1 步 / 共 7 步", "项目 / 数据导入", "选择行业与关键原材料，导入供应节点数据。系统会检查必填字段、坐标范围与采购权重合计，并将无法精确匹配的字段标记为工作假设。"],
  library: ["工作流 · 第 2 步 / 共 7 步", "数据资源库", "集中管理公开披露、AQUASTAT、Aqueduct 与本地样本库的数据来源，保留字段映射和证据链，便于后续替换 ABC 组最终口径。"],
  map: ["工作流 · 第 3 步 / 共 7 步", "供应链地图与位置匹配", "将供应节点表格转为空间视图：节点连接至匹配流域，点的大小表示采购权重，颜色表示节点所在地区水风险等级。"],
  risk: ["工作流 · 第 4 步 / 共 7 步", "风险敞口", "采购加权水风险敞口按公式 Ek = Σ(wi × ri,k) 计算。标星数值为权重缺失时的等权重估计，所有结果保留数据性质标记。"],
  stress: ["工作流 · 第 5 步 / 共 7 步", "压力测试", "用 C 组待确认的情景参数重算未来水压力上升、供应中断比例与关键节点敏感性，展示结构先完成，参数可集中替换。"],
  agent: ["工作流 · 第 6 步 / 共 7 步", "Agent 分析与管理建议", "Agent 负责理解问题、追问缺失字段、调用确定性工具与解释结果；不编造分数、供应商信息或计算结果。"],
  report: ["工作流 · 第 7 步 / 共 7 步", "报告导出", "把首页指标、数据来源、公式版本、压力情景和 Agent 建议汇总为可交付报告。未确定内容以占位字段保留，后续可替换。"]
};

function badge(text, tone = "gray") {
  return `<span class="badge ${tone}">${text}</span>`;
}

function metric(label, value, foot, tone) {
  return `<div class="panel metric ${tone}"><div class="metric-label">${label}</div><div class="metric-value">${value}</div><div class="muted">${foot}</div></div>`;
}

function progress(active) {
  return `<div class="progress">${NAV.map((item, i) => {
    const n = i + 1;
    const state = i < active ? "done" : i === active ? "active" : "";
    const mark = i < active ? "✓" : n;
    const sub = i < active ? "已完成" : i === active ? "进行中" : "未开始";
    return `<div class="step ${state}"><div class="bubble">${mark}</div><div>${item[2]}</div><div>${sub}</div></div>`;
  }).join("")}</div>`;
}

function rows() {
  return NODES.map(n => {
    const tone = n[6] === "高风险" ? "red" : n[6] === "中风险" ? "amber" : "green";
    const dataTone = n[7] === "工作假设" ? "amber" : "green";
    return `<tr><td>${n[0]}</td><td>${n[1]}</td><td>${n[2]} · ${n[3]}</td><td class="num">${n[4].toFixed(3)}</td><td class="num">${n[5].toFixed(3)}</td><td>${badge(n[6], tone)}</td><td>${badge(n[7], dataTone)}</td></tr>`;
  }).join("");
}

function homePage() {
  return `
    <div class="tabs"><span class="tab active">总览</span><span class="tab">按原材料</span><span class="tab">按产地</span></div>
    <section class="grid overview">
      <div class="panel"><div class="mini-grid"><div><div class="muted">行业分类</div><div class="strong">C14 食品制造业</div></div><div><div class="muted">关键原材料</div><div class="strong">大豆 / 甘蔗 / 甜菜等</div></div><div><div class="muted">评估年度</div><div class="strong">2026</div></div><div><div class="muted">供应节点数</div><div class="strong">10 个</div></div></div><div style="margin-top:16px;">${badge("数据性质：公开披露 5", "green")}${badge("工作假设 4", "amber")}${badge("模拟 1", "gray")}${badge("位置匹配 100%", "green")}${badge("数据质量 A", "amber")}</div></div>
      <div class="panel"><div class="muted">状态标识图例</div>${badge("已确定","green")}${badge("工作假设","amber")}${badge("待验证","red")}${badge("暂不纳入","gray")}</div>
    </section>
    <section class="grid metrics" style="margin-top:18px;">${metric("采购加权水风险敞口 Ek", "0.32<small> / 1.0</small>", "Σ wi × ri,k · 置信 中", "amberbar")}${metric("高风险采购占比 Ph", "52<small>%</small>", "阈值 r ≥ 0.4 · 4 节点", "redbar")}${metric("采购集中度 HHI", "0.16", "按供应节点权重估计", "greenbar")}${metric("Top 3 节点贡献占比", "66<small>%</small>", "用于定位优先调查对象", "redbar")}</section>
    <section class="grid two" style="margin-top:18px;">
      <div class="panel"><strong>分析流程 · 端到端进度</strong><div class="muted">每一步均可回看输入、公式版本与运行时间。</div>${progress(5)}<strong>按原材料产区分解敞口</strong><div class="bars">${["甜菜,185,redbar,12.1%","大豆,97,amberbar,6.4%","茶叶,62,amberbar,4.0%","甘蔗,58,greenbar,3.7%","番茄,53,amberbar,3.5%","玉米,22,greenbar,1.1%"].map(s => { const [name,h,t,v] = s.split(","); return `<div class="bar-wrap"><div class="bar ${t}" style="height:${h}px"><span>${v}</span></div><div class="muted">${name}</div></div>`; }).join("")}</div></div>
      <div class="grid"><div class="panel-tight"><strong>数据质量提示</strong><div class="list" style="margin-top:14px;"><div class="list-item"><span class="bullet amber"></span><div><strong>采购权重合计已归一化</strong><div class="muted">当前权重和 100%，系统按统一口径计算敞口。</div></div></div><div class="list-item"><span class="bullet"></span><div><strong>公开披露与工作假设分层标记</strong><div class="muted">样例数据中区分真实披露、工作假设和模拟数据。</div></div></div><div class="list-item"><span class="bullet"></span><div><strong>ABC 组信息保留替换空间</strong><div class="muted">行业范围、数据链路、压力情景参数确认后集中替换。</div></div></div></div></div><div class="panel-tight"><strong>快速入口</strong><p class="muted"><a href="data-import.html">加载统一 10 节点演示样本</a><br><a href="risk-exposure.html">查看敞口复核表</a><br><a href="/copilot/">进入 AI Water Risk Copilot（真实计算）</a></p></div></div>
    </section>`;
}

function importPage() {
  return `<section class="grid two"><div class="panel"><h3>1 · 行业与原材料</h3><div class="muted">行业分类（GB/T 4754-2017）</div><p>${badge("C13 农副食品加工业","gray")}${badge("C14 食品制造业","teal")}${badge("C15 酒 / 饮料 / 精制茶制造业","gray")}${badge("+ 自定义（待 A 组确认）","gray")}</p><div class="muted">关键原材料（与行业联动）</div><p>${badge("甘蔗","gray")}${badge("大豆","teal")}${badge("玉米","gray")}${badge("番茄","gray")}${badge("原奶","gray")}${badge("棕榈","gray")}${badge("茶叶","gray")}</p><div class="grid three" style="margin-top:22px;"><div class="select-card"><div class="muted">L1</div><strong>国家 / 原材料 / 权重</strong></div><div class="select-card"><div class="muted">L2</div><strong>省 / 州 / 供应商</strong></div><div class="select-card active"><div class="muted">L3 ✓</div><strong>经纬度 / 流域 ID</strong></div></div></div><div class="panel"><h3>2 · 导入方式</h3><div class="upload-box"><div><div style="font-size:34px;color:var(--teal);">↥</div><strong>拖拽或选择 CSV / Excel 文件</strong><div class="muted">supply_nodes_甲公司_v3.csv · 10 行 · 已上传</div></div></div><div class="grid two" style="margin-top:18px;"><span class="button">加载统一样本</span><span class="button">手工录入单个节点</span></div><hr style="border:0;border-top:1px solid var(--line);margin:22px 0;"><h3>字段映射</h3><p class="muted">“供应商名称” → <strong>supplier_name</strong><br>“采购金额 / 权重” → <strong>purchase_weight</strong><br>“经度 / 纬度” → <strong>lon / lat</strong></p></div></section><section class="grid four" style="margin-top:18px;">${metric("数据质量等级", "A<small> 86/100</small>", "公开披露 + 工作假设分层", "amberbar")}${metric("校验通过", "10<small> / 10 节点</small>", "坐标与权重字段完整", "greenbar")}${metric("采购权重合计", "100<small>%</small>", "已自动归一化", "greenbar")}${metric("数据性质构成", "5 / 4 / 1", "公开披露 / 假设 / 模拟", "amberbar")}</section><section class="panel" style="margin-top:18px;"><h3>节点预览与校验结果</h3><table><thead><tr><th>节点</th><th>原材料</th><th>供应商 / 产地</th><th>采购权重</th><th>风险分数</th><th>风险等级</th><th>数据性质</th></tr></thead><tbody>${rows()}</tbody></table></section>`;
}

function libraryPage() {
  return `<section class="grid three"><div class="panel"><h3>Aqueduct 4.0</h3><p class="muted">用于基准水压力、未来水压力、干旱与洪涝风险等空间指标匹配。</p>${badge("v2026.1","gray")}${badge("水风险指标","teal")}</div><div class="panel"><h3>AQUASTAT / FAO</h3><p class="muted">用于国家层面用水、农业用水与缺水背景补充。</p>${badge("国家级数据","gray")}${badge("公开来源","green")}</div><div class="panel"><h3>企业公开披露</h3><p class="muted">用于供应节点、供应商、原材料和采购范围的初始验证。</p>${badge("可追溯","green")}${badge("待复核","amber")}</div></section><section class="grid two" style="margin-top:18px;"><div class="panel"><h3>字段字典</h3><table><thead><tr><th>字段</th><th>含义</th><th>状态</th></tr></thead><tbody><tr><td>supplier_name</td><td>供应商名称</td><td>${badge("已确定","green")}</td></tr><tr><td>material</td><td>原材料类别</td><td>${badge("待 A 组最终确认","amber")}</td></tr><tr><td>basin_id</td><td>匹配流域编号</td><td>${badge("B 组口径","teal")}</td></tr><tr><td>scenario_factor</td><td>压力测试情景参数</td><td>${badge("待 C 组确认","amber")}</td></tr></tbody></table></div><div class="panel"><h3>证据链状态</h3><div class="list"><div class="list-item"><span class="bullet green"></span><div><strong>公开披露 5 个节点</strong><div class="muted">可作为当前样例的确定来源。</div></div></div><div class="list-item"><span class="bullet amber"></span><div><strong>工作假设 4 个节点</strong><div class="muted">报告中保留假设声明，后续替换真实数据。</div></div></div><div class="list-item"><span class="bullet"></span><div><strong>模拟数据 1 个节点</strong><div class="muted">仅用于界面和流程演示，不进入真实结论。</div></div></div></div></div></section>`;
}

function mapPage() {
  const nodes = [["S002 甜菜·新疆",70,42,"risk-red"],["S003 大豆·美国",55,24,"risk-green"],["S008 茶叶·云南",27,38,"risk-red"],["S005 番茄·山东",76,45,"risk-red"],["S010 甘蔗·广西",33,65,"risk-red"],["S001 大豆·巴西",20,22,"risk-amber"],["S004 甘蔗·云南",47,63,"risk-green"]];
  return `<section class="grid map-layout"><div class="panel-tight"><h3>筛选</h3><div class="muted">原材料</div><p>${badge("大豆","teal")}${badge("甘蔗","teal")}${badge("甜菜","teal")}${badge("番茄","teal")}${badge("茶叶","teal")}</p><div class="muted">风险等级</div><p>${badge("高风险 · 4 节点","red")}${badge("中风险 · 1 节点","amber")}${badge("低风险 · 2 节点","green")}</p><div class="muted">图层</div><p>${badge("流域边界 开","teal")}${badge("点风险着色 开","teal")}${badge("Aqueduct 网格叠加 P2","gray")}</p></div><div class="panel"><h3>节点 — 流域拓扑视图</h3><p class="muted">布局非地理精确坐标，仅表示供应节点与流域匹配关系。</p><div class="map-canvas">${nodes.map(n => `<span class="map-node ${n[3]}" style="left:${n[1]}%;top:${n[2]}%;" data-label="${n[0]}"></span>`).join("")}${[[28,30,"risk-red"],[60,32,"risk-green"],[78,35,"risk-red"],[45,56,"risk-amber"],[22,64,"risk-green"]].map(b => `<span class="basin ${b[2]}" style="left:${b[0]}%;top:${b[1]}%;"></span>`).join("")}</div></div><div class="grid"><div class="panel-tight"><h3>节点详情 · S002</h3><p class="muted">原材料 <strong>甜菜</strong><br>供应商 / 产地 <strong>新疆甜菜供应商</strong><br>匹配流域 <strong>HB-3311</strong><br>采购权重 <strong>0.293</strong><br>风险得分 <strong>0.413</strong></p>${badge("数据源 Aqueduct 4.0","gray")}${badge("置信 中","amber")}</div><div class="panel-tight"><h3>匹配问题清单</h3><p class="muted"><strong>S008 · 需复核茶叶产区</strong><br>当前按省级匹配，建议补充精确坐标。<br><br><strong>S011 · 待 ABC 数据补全</strong><br>暂不进入当前 10 节点样本。</p><span class="button primary">返回数据导入修复</span></div></div></section>`;
}

function riskPage() {
  return `<section class="grid metrics">${metric("Ek 采购加权敞口", "0.32<small>/1.0</small>", "Σ 贡献 = 0.3155 · v0.3", "amberbar")}${metric("高风险采购占比 Ph", "52<small>%</small>", "阈值 r ≥ 0.4 · 4 节点", "redbar")}${metric("采购集中度 HHI", "0.16", "Σwi² · 10 节点", "greenbar")}${metric("Top 3 贡献占比", "66<small>%</small>", "S002 / S003 / S008", "redbar")}</section><section class="grid two" style="margin-top:18px;"><div class="panel"><h3>节点贡献复核表</h3><table><thead><tr><th>节点</th><th>原材料</th><th>供应商 / 产地</th><th>采购权重</th><th>风险分数</th><th>风险等级</th><th>数据性质</th></tr></thead><tbody>${rows()}</tbody></table></div><div class="grid"><div class="panel-tight"><h3>敏感性分析 · 缺失权重处理</h3><div class="scenario-row"><strong>当前采用</strong><div class="track"><div class="fill" style="width:58%"></div></div><strong>0.32</strong></div><div class="scenario-row"><strong>低权重情形</strong><div class="track"><div class="fill amber" style="width:52%"></div></div><strong>0.28</strong></div><div class="scenario-row"><strong>高权重情形</strong><div class="track"><div class="fill red" style="width:66%"></div></div><strong>0.36</strong></div><p class="muted">结果对权重假设中度敏感，建议优先补全高贡献节点。</p></div><div class="panel-tight"><h3>公式与版本</h3><p class="muted"><strong>Ek = Σ (wi × ri,k)</strong><br>wi = 采购金额占比<br>ri,k = 节点所在地风险指标（0–1 归一化）</p>${badge("公式 v0.3","teal")}${badge("阈值 r ≥ 0.4","gray")}</div></div></section><section class="panel" style="margin-top:18px;"><h3>改进潜力矩阵</h3><div class="scatter">${NODES.map((n, i) => { const x = Math.round(n[5] * 84 + 6); const y = Math.round(88 - n[4] * 190); const tone = n[6] === "高风险" ? "risk-red" : n[6] === "中风险" ? "risk-amber" : "risk-green"; return `<span class="point ${tone}" style="left:${x}%;top:${y}%">${i+1}<span>${n[0]}</span></span>`; }).join("")}</div></section>`;
}

function stressPage() {
  return `<section class="grid three"><div class="panel"><h3>基准情景</h3><div class="metric-value">0.32</div><p class="muted">使用当前样例节点、当前权重与 Aqueduct 基准风险指标。</p>${badge("已计算","green")}</div><div class="panel"><h3>2030 水压力上升</h3><div class="metric-value">0.39</div><p class="muted">对高风险流域施加 C 组待确认的上升参数。</p>${badge("参数占位","amber")}</div><div class="panel"><h3>关键供应中断</h3><div class="metric-value">23<small>%</small></div><p class="muted">假设高贡献节点阶段性中断，估算受影响采购权重。</p>${badge("待业务确认","amber")}</div></section><section class="grid two" style="margin-top:18px;"><div class="panel"><h3>情景参数面板</h3><div class="scenario-row"><strong>未来水压力</strong><div class="track"><div class="fill red" style="width:66%"></div></div><span>+24%</span></div><div class="scenario-row"><strong>旱季供水下降</strong><div class="track"><div class="fill amber" style="width:42%"></div></div><span>-15%</span></div><div class="scenario-row"><strong>供应中断比例</strong><div class="track"><div class="fill" style="width:36%"></div></div><span>10%</span></div><p class="muted">这些参数为页面预留位，等 C 组最终信息确定后集中替换。</p></div><div class="panel"><h3>管理含义</h3><div class="list"><div class="list-item"><span class="bullet red"></span><div><strong>S002 与 S008 是优先复核对象</strong><div class="muted">贡献高且情景压力上升后更敏感。</div></div></div><div class="list-item"><span class="bullet amber"></span><div><strong>高风险采购占比可能从 52% 升至 61%</strong><div class="muted">依赖 C 组阈值确认，不作为最终预测。</div></div></div><div class="list-item"><span class="bullet green"></span><div><strong>低风险节点具备替代产能讨论价值</strong><div class="muted">可进入后续供应商策略分析。</div></div></div></div></div></section>`;
}

function agentPage() {
  return `<section class="grid two"><div class="panel"><h3>AI Water Risk Copilot · 正式交互入口</h3><p class="muted">原 2026-08 MVP 的 Agent 页面仅为规则演示。当前比赛版已升级为真实可调用数据查询、D Baseline、Scenario、证据追溯与导出的 AI Agent。</p><div style="margin-top:20px;"><a class="button primary" href="/copilot/">进入 AI Water Risk Copilot →</a></div><div style="margin-top:18px;">${badge("真实 Tool Calling 链路","green")}${badge("D Baseline v1.2","teal")}${badge("Scenario","teal")}${badge("Unknown/Proxy/Conflict 显式处理","amber")}</div></div><div class="panel"><h3>为什么保留这一页？</h3><div class="list"><div class="list-item"><span class="bullet green"></span><div><strong>研究展示层继续保留</strong><div class="muted">学姐原网站的页面结构、地图与可视化用于解释项目逻辑。</div></div></div><div class="list-item"><span class="bullet"></span><div><strong>正式计算移交 Copilot</strong><div class="muted">风险数字、Scenario 和管理建议以确定性程序与真实运行日志为准。</div></div></div><div class="list-item"><span class="bullet amber"></span><div><strong>静态页旧数字仅作历史原型</strong><div class="muted">不再作为最终比赛结论或正式风险值。</div></div></div></div></div></section>`;
}

function reportPage() {
  return `<section class="grid two"><div class="panel"><h3>报告结构</h3><div class="grid"><div class="report-section"><strong>1. 项目边界与数据声明</strong><span class="muted">行业、原材料、节点范围、公开披露与工作假设说明。</span></div><div class="report-section"><strong>2. 核心水风险指标</strong><span class="muted">Ek、Ph、HHI、Top3 贡献及公式版本。</span></div><div class="report-section"><strong>3. 节点清单与空间匹配</strong><span class="muted">供应商、产地、坐标/省级匹配、流域编号。</span></div><div class="report-section"><strong>4. 压力测试与管理建议</strong><span class="muted">C 组情景参数确认后替换最终解释。</span></div></div></div><div class="panel"><h3>导出状态</h3><div class="list"><div class="list-item"><span class="bullet green"></span><div><strong>可导出 CSV 复核表</strong><div class="muted">包含节点、权重、风险分数、贡献、来源。</div></div></div><div class="list-item"><span class="bullet amber"></span><div><strong>报告正文为草稿</strong><div class="muted">ABC 组口径确定后替换占位字段。</div></div></div><div class="list-item"><span class="bullet"></span><div><strong>远程预览已上线</strong><div class="muted">GitHub Pages 用于对外查看设计和结构。</div></div></div></div><p><span class="button primary">生成完整报告 →</span> <span class="button">导出节点清单 CSV</span></p></div></section>`;
}

const PAGES = { home: homePage, import: importPage, library: libraryPage, map: mapPage, risk: riskPage, stress: stressPage, agent: agentPage, report: reportPage };

function render() {
  const page = document.body.dataset.page || "home";
  const meta = META[page] || META.home;
  const navHtml = NAV.map(item => `<a class="nav-item ${item[4] === page ? "active" : ""}" href="${item[3]}"><span class="nav-muted">${item[1]}</span><span class="nav-muted">${item[0]}</span><span>${item[2]}</span></a>`).join("");
  document.getElementById("app").innerHTML = `<div class="app"><aside class="sidebar"><a class="logo" href="index.html"><span class="drop"></span><span><span class="brand">水脉 WaterPulse</span><span class="brand-sub">UPSTREAM WATER RISK<br>AGENT</span></span></a><div class="project"><div class="label">当前项目</div><strong>甲公司 · 植物基蛋白原料</strong><span>C14 食品制造业 · 2026 评估年度</span></div><div class="nav-title">分析流程</div>${navHtml}<div class="nav-title">智能决策</div><a class="nav-item copilot-entry" href="/copilot/"><span class="nav-muted">✦</span><span class="nav-muted">AI</span><span>AI Water Risk Copilot</span></a><div class="nav-title">系统</div><a class="nav-item" href="report-export.html"><span class="nav-muted">⚙</span><span class="nav-muted">·</span><span>设置 / 审计日志</span></a><div class="side-foot">● 研究展示与 AI Copilot 已合并<br><strong style="color:#fff;">Competition Integrated</strong><br>正式数值以确定性程序结果为准</div></aside><main><div class="topbar"><div class="crumb">水脉 WaterPulse / <strong>${NAV.find(n => n[4] === page)?.[2] || "首页总览"}</strong></div><div class="actions"><span class="chip"><span class="dot"></span>研究展示层</span><span class="chip">AI Copilot 已接入 · D Baseline v1.2</span></div></div><div class="kicker">${meta[0]}</div><h1>${meta[1]}</h1><p class="lead">${meta[2]}</p><div class="legacy-notice"><strong>研究展示层</strong>：本区域保留 2026-08 MVP 的页面与可视化结构；最终可复算 Baseline、Scenario、AI 解释和日志请进入 <a href="/copilot/">AI Water Risk Copilot</a>。</div>${PAGES[page] ? PAGES[page]() : homePage()}<footer>水脉 WaterPulse · 研究展示层。正式可复算分析请使用同站 AI Water Risk Copilot；所有正式风险数字以确定性程序 JSON 与运行日志为准。</footer></main></div>`;
}

render();
