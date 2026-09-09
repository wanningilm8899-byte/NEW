from __future__ import annotations
import importlib.util
import json
from pathlib import Path
from typing import Any
from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1]
D_DIR = ROOT / "deterministic" / "d_baseline"
SCHEMA_PATH = D_DIR / "schemas" / "baseline_input.schema.json"
OUT_SCHEMA_PATH = D_DIR / "schemas" / "calculation_output.schema.json"

# D's original package remains untouched under deterministic/d_baseline.
# Import exactly that engine, so Agent and direct Python use the same calculation code.
spec_calc = importlib.util.spec_from_file_location("baseline_calculator", D_DIR / "baseline_calculator.py")
calc_mod = importlib.util.module_from_spec(spec_calc)
spec_calc.loader.exec_module(calc_mod)
import sys
sys.modules["baseline_calculator"] = calc_mod

spec = importlib.util.spec_from_file_location("d_baseline_api", D_DIR / "baseline_api.py")
d_api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d_api)

INPUT_SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
OUTPUT_SCHEMA = json.loads(OUT_SCHEMA_PATH.read_text(encoding="utf-8"))


def _strip_internal_fields(request: dict) -> dict:
    return {k: v for k, v in request.items() if not str(k).startswith("_")}


def validate_input_schema(request: dict) -> list[str]:
    clean = _strip_internal_fields(request)
    errs = sorted(Draft7Validator(INPUT_SCHEMA).iter_errors(clean), key=lambda e: list(e.path))
    return [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errs]


def validate_output_schema(result: dict) -> list[str]:
    errs = sorted(Draft7Validator(OUTPUT_SCHEMA).iter_errors(result), key=lambda e: list(e.path))
    return [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errs]


def calculate_baseline(request: dict) -> dict:
    """Formal F→D adapter. No risk arithmetic is implemented here."""
    schema_errors = validate_input_schema(request)
    if schema_errors:
        return {
            "run_id": request.get("run_id", "UNKNOWN"),
            "input_hash": None,
            "enterprise_id": request.get("enterprise_id"),
            "data_version": request.get("data_version"),
            "engine_version": getattr(d_api, "ENGINE_VERSION", "baseline-engine-unknown"),
            "formula_version": getattr(d_api, "FORMULA_VERSION", "unknown"),
            "parameter_version": getattr(d_api, "PARAMETER_VERSION", "unknown"),
            "theta": request.get("theta") or {"WS": 1/3, "DR": 1/3, "SV": 1/3},
            "calculated_at": None,
            "status": "error",
            "calculation_mode": "none",
            "errors": ["输入 JSON 未通过 baseline_input.schema.json"] + schema_errors,
            "materials": [], "warnings": [], "assumptions": [], "source_refs": [],
            "missing_fields": [], "proxy_fields": [], "excluded_nodes": [],
            "schema_validation": {"input_valid": False, "output_valid": None},
        }

    clean = _strip_internal_fields(request)
    result = d_api.calculate_baseline(clean)
    out_errors = validate_output_schema(result)
    result["schema_validation"] = {
        "input_valid": True,
        "output_valid": len(out_errors) == 0,
        "output_errors": out_errors,
    }
    # F-side trace only; numerical fields are untouched.
    result["agent_adapter_version"] = "f-d-adapter-1.0"
    result["builder_warnings"] = request.get("_builder_warnings", [])
    result["query_trace"] = request.get("_query_trace", [])
    return result
