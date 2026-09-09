from __future__ import annotations
from collections import defaultdict
from typing import Any

from tools.query_adapter import resolve_location, lookup_water_risk, lookup_material_parameters

DATA_RELEASE_ID = "integrated-mvp-2026-09-06"


def _meta(source_ref: str | None, data_status: str | None, confidence: str | None,
          approved_proxy: bool = False, proxy_value: float | None = None) -> dict:
    out = {
        "source_ref": source_ref or "Unknown",
        "data_status": data_status if data_status in {"V", "P", "A", "S"} else "A",
        "confidence": confidence if confidence in {"High", "Medium", "Low"} else "Low",
    }
    if approved_proxy:
        out["approved_proxy"] = True
    if proxy_value is not None:
        out["proxy_value"] = proxy_value
    return out


def build_baseline_request(records: list[dict], run_id: str, data_version: str = DATA_RELEASE_ID,
                           theta: dict | None = None) -> dict:
    """Turn confirmed user rows + registered B/C data into D's baseline_input.schema.json shape.

    The builder never invents missing professional values. Missing values remain None and are
    handed to D's deterministic validation/calculation layer.
    """
    if not records:
        return {
            "run_id": run_id,
            "enterprise_id": "UNKNOWN",
            "data_version": data_version,
            "theta": theta or {"WS": 1/3, "DR": 1/3, "SV": 1/3},
            "materials": [],
            "_builder_warnings": ["没有已确认的采购记录"],
        }

    enterprise = str(records[0].get("enterprise") or "ENTERPRISE_USER").strip() or "ENTERPRISE_USER"
    grouped: dict[str, list[dict]] = defaultdict(list)
    warnings: list[str] = []
    query_trace: list[dict] = []

    for rec in records:
        material = str(rec.get("material") or "").strip()
        grouped[material].append(dict(rec))

    materials = []
    for material, rows in grouped.items():
        mp_resp = lookup_material_parameters(material, data_release_id=data_version)
        mp = mp_resp.get("data") or {}
        warnings.extend(mp_resp.get("warnings") or [])
        query_trace.append({"tool": "lookup_material_parameters", "material": material,
                            "status": mp_resp.get("status"), "data_release_id": mp_resp.get("data_release_id")})

        material_params = {
            "BWD": mp.get("BWD"),
            "DYS": mp.get("DYS"),
            "DYS_unit": "score_0_1",
            "CTS": mp.get("CTS"),
            "OA": mp.get("OA"),
        }
        material_field_meta = {}
        for f in ("BWD", "DYS", "CTS", "OA"):
            material_field_meta[f] = _meta(
                mp.get("source_ref"),
                (mp.get("data_type") or {}).get(f),
                (mp.get("confidence") or {}).get(f),
            )

        nodes = []
        sum_w = 0.0
        for rec in rows:
            node_id = str(rec.get("node_id") or "").strip()
            node_name = str(rec.get("node_name") or "").strip()
            if not node_id and node_name:
                loc = resolve_location(node_name, material)
                query_trace.append({"tool": "resolve_location", "query": node_name,
                                    "material": material, "status": loc.get("status")})
                warnings.extend(loc.get("warnings") or [])
                if loc.get("data"):
                    node_id = str(loc["data"].get("node_id") or "")
                    node_name = str(loc["data"].get("node_name") or node_name)

            wr = lookup_water_risk(node_id, year=rec.get("year"), data_release_id=data_version)
            query_trace.append({"tool": "lookup_water_risk", "node_id": node_id,
                                "status": wr.get("status"), "data_release_id": wr.get("data_release_id")})
            warnings.extend(wr.get("warnings") or [])
            h = wr.get("data") or {}
            vals = h.get("values") or {}

            try:
                W = float(rec.get("purchase_weight")) if rec.get("purchase_weight") not in (None, "") else None
            except Exception:
                W = None
            if isinstance(W, (int, float)):
                sum_w += W

            user_source_type = str(rec.get("source_type") or "V-user-confirmed")
            procurement_status = "A" if user_source_type.startswith("A") else "V"
            procurement_conf = str(rec.get("confidence") or "High")

            hazard_status = h.get("data_type") if h.get("data_type") in {"V", "P", "A", "S"} else "V"
            hazard_conf = h.get("confidence") if h.get("confidence") in {"High", "Medium", "Low"} else "Low"
            hazard_source = h.get("source_ref") or "Unknown"

            node = {
                "node_id": node_id or (node_name or "UNRESOLVED_NODE"),
                "node_name": node_name or h.get("node_name") or node_id,
                "spatial_level": "pfaf/basin" if h.get("pfaf_id") else "user_provided_or_unresolved",
                "country": "",
                "pfaf_id": str(h.get("pfaf_id") or ""),
                "reference_period": rec.get("year") or h.get("reference_period") or "Unknown",
                "W": W,
                "WS": (vals.get("WS") or {}).get("value"),
                "WS_unit": "aqueduct_score_0_5",
                "SV": (vals.get("SV") or {}).get("value"),
                "SV_unit": "aqueduct_score_0_5",
                "DR": (vals.get("DR") or {}).get("value"),
                # keep node-level material params empty so D uses material_params fallback
                "BWD": None,
                "DYS": None,
                "DYS_unit": "score_0_1",
                "CTS": None,
                "OA": None,
                "field_meta": {
                    "W": _meta("user_confirmed_enterprise_input", procurement_status, procurement_conf),
                    "WS": _meta(hazard_source, hazard_status, hazard_conf),
                    "SV": _meta(hazard_source, hazard_status, hazard_conf),
                    "DR": _meta(hazard_source, hazard_status, hazard_conf),
                    "BWD": material_field_meta["BWD"],
                    "DYS": material_field_meta["DYS"],
                    "CTS": material_field_meta["CTS"],
                    "OA": material_field_meta["OA"],
                },
            }
            nodes.append(node)

        U = max(0.0, 1.0 - sum_w)
        # if >1, leave U=0 and let D validation return error instead of silently normalizing
        if sum_w > 1.0:
            U = 0.0

        materials.append({
            "material": material,
            "U": round(U, 10),
            "material_params": material_params,
            "field_meta": material_field_meta,
            "nodes": nodes,
        })

    req = {
        "run_id": run_id,
        "enterprise_id": enterprise,
        "data_version": data_version,
        "theta": theta or {"WS": 1/3, "DR": 1/3, "SV": 1/3},
        "materials": materials,
    }
    req["_builder_warnings"] = list(dict.fromkeys(warnings))
    req["_query_trace"] = query_trace
    return req
