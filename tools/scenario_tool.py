from __future__ import annotations
import json
from pathlib import Path
import pandas as pd

from core.paths import DATA_DIR
from engines import scenario_engine as se

SCENARIO_VERSION = "scenario-adapter-2.1-d-baseline-authoritative"


def _material_output(baseline_result: dict, material: str) -> dict | None:
    for m in baseline_result.get("materials", []):
        if str(m.get("material")) == str(material):
            return m
    return None


def _d_to_e_baseline_df(baseline_result: dict, material: str) -> pd.DataFrame:
    m = _material_output(baseline_result, material)
    if not m:
        return pd.DataFrame()
    rows = []
    ent = baseline_result.get("enterprise_id") or "ENTERPRISE"
    for n in m.get("nodes", []):
        if n.get("R") is None or n.get("C") is None:
            continue
        rows.append({
            "node_id": n.get("node_id"), "material": material, "enterprise": ent,
            "node_name": n.get("node_name"), "weight": n.get("W"),
            "bwd": n.get("BWD"), "dys": n.get("DYS"), "cts": n.get("CTS"), "oa": n.get("OA"),
            "dr": n.get("DR"), "path_ws": n.get("Path_WS"), "path_dr": n.get("Path_DR"),
            "path_sv": n.get("Path_SV"), "R": n.get("R"), "C": n.get("C"),
            "contribution_share": n.get("contribution_share"), "rank": n.get("rank"),
            "status": "Scored",
        })
    return pd.DataFrame(rows)


def _load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / name, encoding="utf-8-sig")


def _params() -> dict:
    return json.loads((DATA_DIR / "scenario_params.json").read_text(encoding="utf-8"))


def run_scenario(baseline_result: dict, scenario_type: str, material: str,
                 year: int = 2050, path: str = "BAU", failure_fraction: float = 1.0,
                 inventory: float = 0.10) -> dict:
    m = _material_output(baseline_result, material)
    if not m:
        return {"status": "insufficient", "data": None, "warnings": [],
                "data_gaps": ["Baseline 中没有所选材料"], "scenario_version": SCENARIO_VERSION}
    if baseline_result.get("status") in {"insufficient", "conflict", "error"} or m.get("status") != "success":
        return {"status": "insufficient", "data": None,
                "warnings": ["Scenario 要求所选材料具有有效完整 Baseline；partial/insufficient 不继续正式情景计算。"],
                "data_gaps": m.get("missing_fields", []), "scenario_version": SCENARIO_VERSION,
                "baseline_run_id": baseline_result.get("run_id"), "baseline_input_hash": baseline_result.get("input_hash")}

    base = _d_to_e_baseline_df(baseline_result, material)
    if base.empty:
        return {"status": "insufficient", "data": None, "warnings": [],
                "data_gaps": ["没有可用于 Scenario 的已评分节点"], "scenario_version": SCENARIO_VERSION}

    th0 = baseline_result.get("theta") or {"WS": 1/3, "DR": 1/3, "SV": 1/3}
    theta = {"ws": th0.get("WS", 1/3), "dr": th0.get("DR", 1/3), "sv": th0.get("SV", 1/3)}
    warnings = []

    try:
        if scenario_type == "PeakSeason":
            monthly = _load_csv("monthly_ws.csv")
            df = se.scenario_peak_season(base, monthly, theta)
            sel = df[df["material"] == material].copy()
            data = {
                "summary": [{
                    "material": material,
                    "PRWI_baseline": round(float(base["C"].sum()), 6),
                    "PRWI_scenario": round(float(sel["C_peak"].sum()), 6),
                    "PRWI_delta": round(float(sel["C_peak"].sum() - base["C"].sum()), 6),
                }],
                "node_table": sel[["node_id", "node_name", "R", "R_peak", "R_delta", "C", "C_peak", "rank_peak"]].to_dict("records"),
            }
        elif scenario_type == "AqueductFuture":
            future = _load_csv("future_ws_sv.csv")
            if "demo" in future.columns and (future["demo"] == 1).any():
                warnings.append("Future 数据包含 demo=1 / S 类演示数据，只能作为机制演示，不是正式未来预测。")
            node, combo = se.scenario_future(base, future, theta)
            combo = combo[(combo["material"] == material) & (combo["year"] == year) & (combo["path"] == path)]
            node = node[(node["material"] == material) & (node["year"] == year) & (node["path"] == path)]
            data = {"summary": combo.to_dict("records"), "node_table": node.to_dict("records"), "demo": bool(warnings)}
        elif scenario_type == "ExtremeDrought":
            extreme = _load_csv("extreme_drought.csv")
            p = _params()
            df = se.scenario_extreme_drought(base, extreme, p, theta)
            sel = df[df["material"] == material].copy()
            data = {
                "summary": [{
                    "material": material,
                    "PRWI_baseline": round(float(base["C"].sum()), 6),
                    "PRWI_scenario": round(float(sel["C_ed"].sum(skipna=True)), 6),
                    "PRWI_delta": round(float(sel["C_ed"].sum(skipna=True) - base["C"].sum()), 6),
                }],
                "node_table": sel[["node_id", "node_name", "event_status", "R", "R_ed", "R_delta_ed", "C", "C_ed", "lambda_source"]].to_dict("records"),
            }
            warnings.append("极端干旱供应侧 λ 为 reference 时，仅作机制说明，不应表述为已验证真实减产。")
        elif scenario_type == "NodeFailure":
            p = _params()
            p["node_failure"]["failure_fraction_f"] = float(failure_fraction)
            p["node_failure"]["inventory_I"] = float(inventory)
            res = se.scenario_node_failure(base, p).get(material)
            if not res:
                raise ValueError("NodeFailure 未返回所选材料结果")
            # DataFrames -> records
            data = {k: (v.to_dict("records") if hasattr(v, "to_dict") else v) for k, v in res.items()}
        else:
            return {"status": "error", "data": None, "warnings": [],
                    "data_gaps": [f"未知 scenario_type: {scenario_type}"], "scenario_version": SCENARIO_VERSION}
    except Exception as e:
        return {"status": "error", "data": None, "warnings": [], "data_gaps": [str(e)],
                "scenario_version": SCENARIO_VERSION, "baseline_run_id": baseline_result.get("run_id"),
                "baseline_input_hash": baseline_result.get("input_hash")}

    return {
        "status": "partial" if warnings else "success",
        "scenario_type": scenario_type,
        "material": material,
        "data": data,
        "warnings": warnings,
        "data_gaps": [],
        "baseline_run_id": baseline_result.get("run_id"),
        "baseline_input_hash": baseline_result.get("input_hash"),
        "data_version": baseline_result.get("data_version"),
        "scenario_version": SCENARIO_VERSION,
    }
