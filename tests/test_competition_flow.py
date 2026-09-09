from fastapi.testclient import TestClient
import server

c=TestClient(server.app)

def test_end_to_end_demo():
    d=c.get('/api/demo/甘蔗').json()
    x=c.post('/api/confirm',json={'records':d['records'],'mapping':d['mapping'],'weight_mode':'0-1','human_confirmed':True,'task':'baseline'}).json()
    assert x['status'] in {'success','partial'}
    r=c.post('/api/resolve-input',json={'records':x['records'],'run_id':x['run_id']}).json()
    assert r['status']=='success'
    b=c.post('/api/baseline',json={'request':r['resolved_request']}).json()
    assert b['status']=='success'
    assert b['materials'][0]['PRWI'] is not None
    assert b['schema_validation']['input_valid'] is True
    assert b['schema_validation']['output_valid'] is True
    s=c.post('/api/scenario',json={'baseline':b,'scenario_type':'NodeFailure','material':'甘蔗','failure_fraction':1.0,'inventory':0.1}).json()
    assert s['status'] in {'success','partial'}
    assert s['baseline_input_hash']==b['input_hash']

def test_d_complete_golden_status():
    q=c.get('/api/qa').json()
    complete=[x for x in q['cases'] if x['case']=='complete'][0]
    assert complete['actual_status']=='success'
    assert complete['checks']['input_schema'] is True
    assert complete['checks']['output_schema'] is True

def test_no_scenario_without_valid_baseline():
    bad={'run_id':'x','status':'insufficient','materials':[]}
    r=c.post('/api/scenario',json={'baseline':bad,'scenario_type':'NodeFailure','material':'甘蔗'}).json()
    assert r['status']=='insufficient'
