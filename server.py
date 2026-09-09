from __future__ import annotations
import json, math, tempfile, uuid
from pathlib import Path
from typing import Any
import numpy as np
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

ROOT=Path(__file__).resolve().parent
load_dotenv(ROOT/'.env')

from tools.data_tool import read_user_file, suggest_mapping, apply_mapping, validate_normalized, load_demo_procurement
from tools.resolved_input_builder import build_baseline_request, DATA_RELEASE_ID
from tools.baseline_tool import calculate_baseline, validate_input_schema, validate_output_schema, d_api
from tools.scenario_tool import run_scenario
from tools.export_tool import export_risk_report
from agent.router import route_intent
from agent.risk_brief import baseline_brief, scenario_brief, data_audit_brief
from agent.llm_adapter import rewrite_with_llm, configured as llm_configured
from core.logging_utils import log_event, read_logs, new_run_id, now_iso

app=FastAPI(title='Water Risk Copilot API', version='3.0-competition')


def clean_scalar(v: Any):
    if isinstance(v, (np.integer,)): return int(v)
    if isinstance(v, (np.floating,)):
        x=float(v); return None if math.isnan(x) or math.isinf(x) else x
    if isinstance(v, (np.bool_,)): return bool(v)
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)): return None
    return v

def jsonable(x: Any):
    if isinstance(x, pd.DataFrame): return [{str(k):jsonable(v) for k,v in row.items()} for row in x.to_dict(orient='records')]
    if isinstance(x, pd.Series): return {str(k):jsonable(v) for k,v in x.to_dict().items()}
    if isinstance(x, dict): return {str(k):jsonable(v) for k,v in x.items()}
    if isinstance(x, (list,tuple,set)): return [jsonable(v) for v in x]
    return clean_scalar(x)

class ConfirmRequest(BaseModel):
    records:list[dict]; mapping:list[dict]; weight_mode:str='0-1'; human_confirmed:bool=False; task:str='baseline'
class ResolveRequest(BaseModel):
    records:list[dict]; run_id:str; theta:dict|None=None
class BaselineRequest(BaseModel):
    request:dict
class ScenarioRequest(BaseModel):
    baseline:dict; scenario_type:str; material:str; year:int=2050; path:str='BAU'; failure_fraction:float=1.0; inventory:float=0.10
class ChatRequest(BaseModel):
    message:str; selected_task:str|None=None; role:str='risk'; validation:dict|None=None; resolved_request:dict|None=None; baseline:dict|None=None; scenario:dict|None=None
class ExportRequest(BaseModel):
    baseline:dict; scenario:dict|None=None; validation:dict|None=None; resolved_request:dict|None=None; snapshot_id:str=''; role:str='risk'

@app.get('/api/health')
def health():
    return {'status':'ok','app':'Water Risk Copilot','version':'3.0-competition','timestamp':now_iso(),
            'baseline_engine':getattr(d_api,'ENGINE_VERSION','unknown'), 'data_release_id':DATA_RELEASE_ID}

@app.get('/api/demo/{material}')
def demo(material:str):
    if material not in ['甘蔗','甜菜','大豆']: raise HTTPException(404,'未知材料')
    df=load_demo_procurement(material)
    mapping=[
        {'system_field':'enterprise','source_column':'enterprise','required':False},
        {'system_field':'material','source_column':'material','required':True},
        {'system_field':'node_id','source_column':'node_id','required':False},
        {'system_field':'node_name','source_column':'node_name','required':False},
        {'system_field':'purchase_weight','source_column':'purchase_weight','required':True},
        {'system_field':'year','source_column':'year','required':False},
    ]
    return {'status':'success','records':jsonable(df),'mapping':mapping,
            'warning':'示范采购权重为 A 类研究假设，不代表真实企业采购。'}

@app.post('/api/upload')
async def upload(file:UploadFile=File(...)):
    suffix=Path(file.filename or '').suffix.lower()
    if suffix not in ['.csv','.xlsx','.xls','.docx','.pdf']: raise HTTPException(400,'仅支持 CSV/XLSX/XLS/DOCX/PDF')
    payload=await file.read(); tmp=ROOT/'outputs'/f'upload_{uuid.uuid4().hex[:10]}{suffix}'; tmp.write_bytes(payload)
    try:
        res=read_user_file(str(tmp)); df=res.get('data') if isinstance(res.get('data'),pd.DataFrame) else pd.DataFrame()
        mapping=suggest_mapping(list(df.columns)) if res.get('kind')=='table' else pd.DataFrame([
            {'system_field':'enterprise','source_column':'enterprise','required':False}, {'system_field':'material','source_column':'material','required':True},
            {'system_field':'node_id','source_column':'node_id','required':False}, {'system_field':'node_name','source_column':'node_name','required':False},
            {'system_field':'purchase_weight','source_column':'purchase_weight','required':True}, {'system_field':'year','source_column':'year','required':False},])
        msg=(f'已读取表格 {len(df)} 行 × {len(df.columns)} 列。请确认字段映射后再进入计算。' if res.get('kind')=='table'
             else '已生成候选供应链记录。文档抽取仅为候选数据，关键采购字段必须人工确认。')
        log_event({'event':'upload_parse','filename':file.filename,'kind':res.get('kind'),'rows':len(df)})
        return {'status':'success','kind':res.get('kind'),'records':jsonable(df),'mapping':jsonable(mapping),'message':msg,'text_preview':(res.get('text') or '')[:12000]}
    finally:
        try: tmp.unlink(missing_ok=True)
        except Exception: pass

@app.post('/api/confirm')
def confirm(req:ConfirmRequest):
    if not req.human_confirmed: return {'status':'insufficient','message':'请先人工确认关键字段映射与采购口径。'}
    raw=pd.DataFrame(req.records); mp=pd.DataFrame(req.mapping); normalized=apply_mapping(raw,mp,req.weight_mode)
    validation=validate_normalized(normalized); run_id='R-'+new_run_id(); snapshot_id='snap-'+run_id
    log_event({'run_id':run_id,'event':'input_confirmed','snapshot_id':snapshot_id,'task':req.task,'status':validation.get('status'),'rows':len(normalized),'validation':validation})
    return {'status':validation.get('status'),'run_id':run_id,'snapshot_id':snapshot_id,'records':jsonable(normalized),'validation':jsonable(validation),'audit_brief':data_audit_brief(validation)}

@app.post('/api/resolve-input')
def resolve_input(req:ResolveRequest):
    built=build_baseline_request(req.records, req.run_id, DATA_RELEASE_ID, req.theta)
    schema_errors=validate_input_schema(built)
    status='error' if schema_errors else 'success'
    # note: D will determine partial/insufficient/conflict at calculation time
    log_event({'run_id':req.run_id,'event':'resolved_input','status':status,'data_version':built.get('data_version'),
               'query_trace':built.get('_query_trace',[]),'builder_warnings':built.get('_builder_warnings',[]),'schema_errors':schema_errors})
    return {'status':status,'resolved_request':jsonable(built),'schema_errors':schema_errors,
            'warnings':built.get('_builder_warnings',[]),'query_trace':built.get('_query_trace',[])}

@app.post('/api/baseline')
def baseline(req:BaselineRequest):
    result=calculate_baseline(req.request)
    log_event({'run_id':result.get('run_id'),'event':'baseline','status':result.get('status'),'calculation_mode':result.get('calculation_mode'),
               'input_hash':result.get('input_hash'),'engine_version':result.get('engine_version'),'formula_version':result.get('formula_version'),
               'data_version':result.get('data_version'),'warnings':result.get('warnings'),'missing_fields':result.get('missing_fields')})
    result['brief']=baseline_brief(result)
    return jsonable(result)

@app.post('/api/scenario')
def scenario(req:ScenarioRequest):
    result=run_scenario(req.baseline,req.scenario_type,req.material,req.year,req.path,req.failure_fraction,req.inventory)
    log_event({'run_id':req.baseline.get('run_id'),'event':'scenario','status':result.get('status'),'scenario_type':req.scenario_type,
               'baseline_input_hash':result.get('baseline_input_hash'),'scenario_version':result.get('scenario_version'),'warnings':result.get('warnings')})
    result['brief']=scenario_brief(result,req.baseline)
    return jsonable(result)

@app.post('/api/chat')
def chat(req:ChatRequest):
    route=route_intent(req.message,req.selected_task)
    tools=[]
    if route['intent']=='data_audit':
        answer=data_audit_brief(req.validation,req.resolved_request); tools=['extract_supply_chain','match_water_risk','get_material_dependency']
    elif route['intent']=='baseline':
        if req.baseline:
            answer=baseline_brief(req.baseline,role=req.role); tools=['match_water_risk','get_material_dependency','calculate_baseline','generate_risk_brief']
        else:
            answer='该问题属于 Baseline 诊断，但当前尚无正式 Baseline。请先完成字段确认、数据补齐与确定性计算。'; tools=[]
    elif route['intent']=='scenario':
        if req.scenario:
            answer=scenario_brief(req.scenario,req.baseline,req.role); tools=['calculate_baseline','run_scenario','generate_risk_brief']
        else:
            answer='该问题属于 Scenario。系统必须先有有效 Baseline，再调用 Scenario；AI 不会在没有工具结果时生成情景数字。'; tools=[]
    else:
        if req.scenario: answer=scenario_brief(req.scenario,req.baseline,req.role); tools=['generate_risk_brief']
        elif req.baseline: answer=baseline_brief(req.baseline,role=req.role); tools=['generate_risk_brief']
        else: answer='请先完成数据确认和 Baseline。我可以解释驱动因素、节点优先级、数据缺口和管理建议，但不会凭语言生成风险数字。'
    rid=(req.baseline or {}).get('run_id') or ((req.resolved_request or {}).get('run_id'))
    system_prompt = (
        '你是 Water Risk Copilot 的解释层。只能解释已经由确定性工具返回的事实；'
        '不得新增或修改任何风险数字，不得把 Proxy/Demo/Assumption 说成观测事实；'
        '若输入中无数字，不得自行补数。回答要面向企业管理者，优先解释驱动因素、数据质量和可执行建议。'
    )
    if llm_configured():
        packed = json.dumps({
            'user_query': req.message, 'role': req.role, 'intent': route['intent'],
            'deterministic_answer': answer, 'tool_calls': tools,
            'baseline_status': (req.baseline or {}).get('status'),
            'scenario_status': (req.scenario or {}).get('status')
        }, ensure_ascii=False)
        answer = rewrite_with_llm(system_prompt, packed, answer)
    log_event({'run_id':rid or new_run_id(),'event':'agent_chat','user_query':req.message,'intent':route['intent'],'role':req.role,'tool_calls':tools,'llm_enabled':llm_configured()})
    return {'status':'success','intent':route['intent'],'scenario_type':route.get('scenario_type'),'confidence':route.get('confidence'),'router_source':route.get('source'),'tool_calls':tools,'llm_enabled':llm_configured(),'answer':answer}

@app.post('/api/export')
def export(req:ExportRequest):
    if not req.baseline: raise HTTPException(400,'请先运行 Baseline')
    path=export_risk_report(req.baseline,req.scenario,req.validation,req.resolved_request,req.snapshot_id,req.role)
    log_event({'run_id':req.baseline.get('run_id'),'event':'export_report','path':path,'snapshot_id':req.snapshot_id})
    return FileResponse(path,filename=Path(path).name,media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

@app.get('/api/logs')
def logs(): return {'status':'success','logs':read_logs(300)}

@app.get('/api/qa')
def qa():
    exdir=ROOT/'deterministic'/'d_baseline'/'examples'
    names=['complete','proxy','partial','insufficient','conflict','error']
    rows=[]
    for i,name in enumerate(names,1):
        inp=json.loads((exdir/f'example_{i}_{name}_input.json').read_text(encoding='utf-8'))
        exp=json.loads((exdir/f'example_{i}_{name}_output.json').read_text(encoding='utf-8'))
        out=calculate_baseline(inp)
        m_out=(out.get('materials') or [{}])[0]; m_exp=(exp.get('materials') or [{}])[0]
        checks={
            'input_schema': out.get('schema_validation',{}).get('input_valid') is True,
            'output_schema': out.get('schema_validation',{}).get('output_valid') is True,
            'status_match': out.get('status')==exp.get('status'),
            'mode_match': out.get('calculation_mode')==exp.get('calculation_mode'),
            'prwi_match': (m_out.get('PRWI')==m_exp.get('PRWI')),
        }
        rows.append({'case':name,'expected_status':exp.get('status'),'actual_status':out.get('status'),'expected_mode':exp.get('calculation_mode'),'actual_mode':out.get('calculation_mode'),
                     'checks':checks,'pass':all(checks.values())})
    return {'status':'success','cases':rows,'note':'D 原始文件保持不改；若某黄金样例不一致，应回到 D 包确认接口/预期输出，而不是由 F 静默改公式。'}

app.mount('/copilot',StaticFiles(directory=ROOT/'copilot_static',html=True),name='copilot')
app.mount('/',StaticFiles(directory=ROOT/'legacy_site',html=True),name='legacy')
