import json, yaml, openai
from importlib import import_module
from django.apps import apps
from pydantic import BaseModel, Field, ValidationError

SCHEMA = yaml.safe_load(open("lab/schema.yml"))

search_tool = {
    "name": "build_django_query",
    "description": "Turn plain English into a Django filter payload.",
    "parameters": {
        "type": "object",
        "properties": {
            "model": {"type": "string", "enum": list(SCHEMA.keys())},
            "filters": {"type": "object", "additionalProperties": {"type": "string"}},
        },
        "required": ["model", "filters"],
    },
}


class Payload(BaseModel):
    model: str
    filters: dict[str, str]


ALIASES = SCHEMA["aliases"]


def canonical(value):
    return ALIASES.get(value.lower(), value)


def ask_llm(question):
    system = "You know this schema:\n" + json.dumps(SCHEMA, indent=2)
    user = {"role": "user", "content": question}
    resp = openai.chat.completions.create(
        model="gpt-4.1-nano-2025-04-14",
        temperature=0,
        tools=[search_tool],
        messages=[{"role": "system", "content": system}, user],
    )
    return resp.choices[0].message.tool_call


def run_query(call):
    payload = Payload(**json.loads(call.arguments))
    Model = apps.get_model("lab", payload.model)
    filters = {k: canonical(v) for k, v in payload.filters.items()}
    qs = Model.objects.filter(**filters)
    return list(qs.values())[:20]  # cap at 20 rows for demo
