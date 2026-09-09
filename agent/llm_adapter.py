from __future__ import annotations
import os, requests


def configured() -> bool:
    return all([os.getenv('LLM_BASE_URL'), os.getenv('LLM_API_KEY'), os.getenv('LLM_MODEL')])


def rewrite_with_llm(system_prompt: str, user_prompt: str, fallback: str) -> str:
    """Optional OpenAI-compatible Chat Completions call. Falls back safely on any error."""
    if not configured():
        return fallback
    try:
        base=os.environ['LLM_BASE_URL'].rstrip('/')
        if not base.endswith('/v1'):
            base += '/v1'
        r=requests.post(
            base + '/chat/completions',
            headers={'Authorization':f"Bearer {os.environ['LLM_API_KEY']}", 'Content-Type':'application/json'},
            json={
                'model':os.environ['LLM_MODEL'],
                'temperature':0.2,
                'messages':[{'role':'system','content':system_prompt},{'role':'user','content':user_prompt}],
            }, timeout=45)
        r.raise_for_status()
        return r.json()['choices'][0]['message']['content'].strip()
    except Exception:
        return fallback
