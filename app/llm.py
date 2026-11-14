"""Hostinger AI Router through the OpenAI SDK. Settings come from .env.

No response_format: not every model behind a router supports JSON mode, so the
prompt asks for JSON and the reply is parsed leniently instead.
"""
import json
import os
import re

from openai import OpenAI

_client = None


class NotConfigured(Exception):
    pass


def _get_client():
    global _client
    if _client is None:
        if not (os.environ.get("AI_ROUTER_BASE_URL") and os.environ.get("AI_ROUTER_API_KEY")):
            raise NotConfigured("AI_ROUTER_BASE_URL and AI_ROUTER_API_KEY are not set")
        _client = OpenAI(base_url=os.environ["AI_ROUTER_BASE_URL"],
                         api_key=os.environ["AI_ROUTER_API_KEY"], timeout=30, max_retries=1)
    return _client


def parse_json(reply):
    """First JSON object in the reply, ignoring ```json fences or chatter around it."""
    m = re.search(r"\{.*\}", reply or "", re.S)
    if not m:
        raise ValueError("model reply contained no JSON object")
    return json.loads(m.group(0))


def ask_json(system, user):
    r = _get_client().chat.completions.create(
        model=os.environ.get("AI_ROUTER_MODEL", ""),
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        temperature=0)
    return parse_json(r.choices[0].message.content)
