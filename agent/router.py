from __future__ import annotations

def route_intent(message: str, selected_task: str | None = None) -> dict:
    """Deterministic safety router; optional LLM planning can sit above this later."""
    if selected_task in {"data_audit", "baseline", "scenario", "explain"}:
        return {"intent": selected_task, "scenario_type": None, "confidence": 1.0, "source": "user_selected"}
    s=(message or '').lower()
    if any(k in s for k in ['缺失','缺口','字段','完整','数据质量','coverage','unknown','proxy','冲突']):
        return {"intent":"data_audit","scenario_type":None,"confidence":0.92,"source":"rule_router"}
    scenario=None
    if any(k in s for k in ['失效','断供','中断','node failure']): scenario='NodeFailure'
    elif any(k in s for k in ['未来','2030','2050','2080','future']): scenario='AqueductFuture'
    elif any(k in s for k in ['极端干旱','历史干旱','extreme drought']): scenario='ExtremeDrought'
    elif any(k in s for k in ['峰值','旺季','关键期','peak']): scenario='PeakSeason'
    if scenario:
        return {"intent":"scenario","scenario_type":scenario,"confidence":0.95,"source":"rule_router"}
    if any(k in s for k in ['baseline','基准','prwi','节点风险','风险最高','贡献最高','节点','优先管理','路径','驱动']):
        return {"intent":"baseline","scenario_type":None,"confidence":0.90,"source":"rule_router"}
    return {"intent":"explain","scenario_type":None,"confidence":0.72,"source":"rule_router"}
