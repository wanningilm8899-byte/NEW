from __future__ import annotations
from typing import Any


def _pct(v):
    try: return f"{float(v)*100:.1f}%"
    except Exception: return "—"

def _num(v, n=4):
    try: return f"{float(v):.{n}f}"
    except Exception: return "—"

def _material(baseline: dict, material: str | None = None):
    mats=baseline.get('materials') or []
    if not mats: return None
    if material:
        for m in mats:
            if str(m.get('material'))==str(material): return m
    return mats[0]

def data_audit_brief(validation: dict | None, resolved_request: dict | None = None) -> str:
    validation=validation or {}
    status=validation.get('status','unknown')
    lines=[f"### 数据准备状态：{status}"]
    cov=validation.get('coverage') or {}
    for k,v in cov.items(): lines.append(f"- {k} 已知采购覆盖：{_pct(v)}")
    for w in validation.get('warnings') or []: lines.append(f"- ⚠ {w}")
    for g in validation.get('data_gaps') or []: lines.append(f"- 缺口：{g}")
    if resolved_request:
        lines.append(f"- 数据版本：{resolved_request.get('data_version','—')}")
        lines.append(f"- 已组装材料数：{len(resolved_request.get('materials') or [])}")
    lines.append("- 原则：Unknown 不等于 0；未解决的关键字段不会由 AI 生成或静默填充。")
    return '\n'.join(lines)


def baseline_brief(baseline: dict, material: str | None = None, role: str='risk') -> str:
    if not baseline:
        return "尚无 Baseline 结果。"
    st=baseline.get('status')
    if st in {'insufficient','conflict','error'}:
        lines=[f"### Baseline 当前状态：{st}"]
        if st=='insufficient': lines.append("- 关键字段未解决，因此系统不生成正式 PRWI。")
        if st=='conflict': lines.append("- 存在数据冲突，等待人工确认后再计算。")
        if st=='error': lines.append("- 输入格式、单位、范围或模型参数未通过校验。")
        for w in baseline.get('warnings') or []: lines.append(f"- ⚠ {w}")
        for e in baseline.get('errors') or []: lines.append(f"- 错误：{e}")
        for g in baseline.get('missing_fields') or []: lines.append(f"- 缺失：{g}")
        return '\n'.join(lines)

    m=_material(baseline,material)
    if not m: return "Baseline 没有所选材料结果。"
    lines=[f"### {m.get('material')} Baseline 解释"]
    lines.append(f"- PRWI：**{_num(m.get('PRWI'))}**；采购覆盖 {_pct(m.get('procurement_coverage'))}，可评分覆盖 {_pct(m.get('scored_coverage'))}。")
    lines.append(f"- 计算模式：**{m.get('calculation_mode',baseline.get('calculation_mode'))}**；综合证据可信度：**{m.get('overall_confidence','Unknown')}**。")
    if m.get('PRWI_lower') is not None:
        lines.append(f"- 风险区间：{_num(m.get('PRWI_lower'))} – {_num(m.get('PRWI_upper'))}；Unknown={_pct(m.get('unknown_share'))}。")
    top=m.get('top_nodes') or []
    if top:
        t=top[0]; lines.append(f"- 对采购组合贡献最大的节点是 **{t.get('node_name') or t.get('node_id')}**，贡献份额 {_pct(t.get('share'))}。")
    nodes=[n for n in m.get('nodes',[]) if n.get('R') is not None]
    if nodes:
        rmax=max(nodes,key=lambda n:n.get('R') or -1)
        lines.append(f"- 节点自身风险强度最高的是 **{rmax.get('node_name') or rmax.get('node_id')}**（R={_num(rmax.get('R'))}）。这与“贡献最大节点”可能不同，因为 C = W × R。")
        # Use node path values rather than D path_share, so the explanation does not invent values.
        weighted={'WS':0.0,'DR':0.0,'SV':0.0}
        for n in nodes:
            w=n.get('W') or 0
            for k,f in [('WS','Path_WS'),('DR','Path_DR'),('SV','Path_SV')]:
                if n.get(f) is not None: weighted[k]+=w*n[f]
        dom=max(weighted,key=weighted.get)
        lines.append(f"- 按节点路径结果加权汇总，当前主要驱动路径为 **{dom}**；AI 只解释程序字段，不重新计算或改写 PRWI。")
    if m.get('proxy_fields'):
        lines.append(f"- 本次使用 {len(m.get('proxy_fields'))} 个批准 Proxy 字段，结论必须与代理身份一起展示。")
    if m.get('warnings'):
        for w in m['warnings']: lines.append(f"- ⚠ {w}")

    role=role or 'risk'
    if role=='procurement':
        lines += ["### 采购负责人建议", "- 优先核验 Top Contribution 节点的真实采购份额、库存与可替代供应能力。", "- 不要只按地点 R 排序调整采购，应同时看节点贡献 C、采购集中度和 Scenario 供应缺口。"]
    elif role=='esg':
        lines += ["### ESG 负责人建议", "- 优先补齐 Low/Unknown 证据字段，并保留 V/P/A/S、来源、版本和参考期。", "- 对高风险但低证据可信度节点先做数据核验，不把低可信度误读为低风险。"]
    else:
        lines += ["### 风险管理负责人建议", "- 将高贡献节点纳入压力测试，重点观察 PRWI、风险集中度与供应缺口是否同时恶化。", "- Baseline 是相对筛查指标，不等同于损失概率或财务损失预测。"]
    return '\n'.join(lines)


def scenario_brief(scenario: dict, baseline: dict | None = None, role: str='risk') -> str:
    if not scenario or scenario.get('data') is None:
        lines=["### Scenario 暂不可用"]
        for x in (scenario or {}).get('warnings') or []: lines.append(f"- ⚠ {x}")
        for x in (scenario or {}).get('data_gaps') or []: lines.append(f"- 缺口：{x}")
        return '\n'.join(lines)
    typ=scenario.get('scenario_type')
    d=scenario.get('data') or {}
    lines=[f"### {typ} 压力测试"]
    if typ=='NodeFailure':
        lines.append(f"- 失效目标：**{d.get('target_node_name') or d.get('target_node_id')}**；Gross Loss={_pct(d.get('gross_loss'))}。")
        lines.append(f"- 库存使用 {_pct(d.get('inventory_used'))}，替代分配 {_pct(d.get('replacement_allocated'))}，未满足需求 **{_pct(d.get('unmet_demand'))}**。")
        lines.append(f"- Conditional PRWI={_num(d.get('conditional_PRWI'))}；Procurement HHI={_num(d.get('procurement_hhi'))}；Risk HHI={_num(d.get('risk_hhi'))}。")
        lines.append("- 注意：节点失效可能让剩余风险质量下降，但同时造成供应缺口；两者必须分开解释。")
    else:
        s=(d.get('summary') or [{}])[0]
        pb=s.get('PRWI_baseline'); ps=s.get('PRWI_scenario',s.get('PRWI_future')); delta=s.get('PRWI_delta')
        lines.append(f"- Baseline={_num(pb)}；Scenario={_num(ps)}；ΔPRWI={_num(delta)}。")
        if d.get('demo'): lines.append("- ⚠ Future 含 S/demo 数据，只能用于机制演示，不得表述为确定预测。")
    for w in scenario.get('warnings') or []: lines.append(f"- ⚠ {w}")
    if role=='procurement': lines.append("- 采购：关注替代容量、集中度、未满足需求和高贡献节点的备选来源。")
    elif role=='esg': lines.append("- ESG：明确区分观测事实、Scenario 假设和 Demo 数据身份，并保留来源。")
    else: lines.append("- 风控：比较 Baseline 与 Scenario 的风险侧和供应侧变化，不把风险分变化直接等同于财务损失。")
    return '\n'.join(lines)
