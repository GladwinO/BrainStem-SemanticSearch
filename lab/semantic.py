import json, yaml, openai
from importlib import import_module
from django.apps import apps
from pydantic import BaseModel, Field, ValidationError
from lab.query_defaults import apply_defaults

SCHEMA = yaml.safe_load(open("lab/schema.yml"))

MODELS = SCHEMA["models"]
ALIASES = SCHEMA["meta"]["aliases"]

search_tool = {
    "type": "function",
    "function": {
        "name": "build_django_query",
        "description": "Turn plain English into a Django filter payload. For recordings from brain regions, use Recording model with filters like brain_region='hippocampus'. For subject conditions, use subject__state format. Extract filters from a query about neural recordings or subjects. ALWAYS scan the query for potential filters before deciding on a model.",
        "parameters": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "enum": list(MODELS.keys())},
                "entities": {
                    "type": "object",
                    "description": "ALL entities mentioned in the query that could be filters",
                    "properties": {
                        "brain_regions": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Any brain regions mentioned (hippocampus, V1, etc.)",
                        },
                        "probe_types": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Any probe types mentioned (tetrode, neuropixels, etc.)",
                        },
                        "subject_states": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Any subject states mentioned (awake, sleeping, etc.)",
                        },
                    },
                },
                "filters": {
                    "type": "object",
                    "description": "Convert all identified entities into appropriate filters",
                },
            },
            "required": ["model", "entities", "filters"],
        },
    },
}


class Payload(BaseModel):
    model: str
    filters: dict[str, str]


def canonical(value):
    """Normalize filter values for case-insensitive matching and aliases."""
    if not value:
        return value

    value_lower = value.lower()

    # First check exact lowercase matches in aliases
    if value_lower in ALIASES:
        return ALIASES[value_lower]

    # Special cases for brain regions
    if value_lower == "v1" or value_lower == "v-1" or value_lower == "visual cortex":
        return "V1"
    if value_lower in ["hippocampus", "hippo", "hpc"]:
        return "Hippocampus"

    # Special cases for probe types
    if value_lower in ["neuropixel", "neuropixels", "npx"]:
        return "Neuropixels"
    if value_lower in ["tetrode", "tetrodes"]:
        return "Tetrode"

    # If no match found, return original with proper capitalization
    return value


def ask_llm(question):
    # First pass: Extract entities
    entities_prompt = f"Extract ALL entities from this query: '{question}'. Identify brain regions, probe types, and subject states."
    entities_resp = openai.chat.completions.create(
        model="gpt-4.1-nano-2025-04-14",
        temperature=0,
        messages=[{"role": "user", "content": entities_prompt}],
    )
    entities = entities_resp.choices[0].message.content

    # Second pass: Build query with highlighted entities
    system = f"""You know this schema:\n{json.dumps(SCHEMA, indent=2)}
    
    ENTITIES FOUND IN QUERY: {entities}
    
    Use these entities to create appropriate filters. For example, if 'tetrode' is found,
    include {{"probe_type": "Tetrode"}} in filters.
    STEP 1: ALWAYS scan for filtering terms first (brain regions, probe types, subject states)
    STEP 2: Choose the most appropriate model based on these terms
    STEP 3: Convert every relevant term into a filter

    Examples:
    Query: "show me tetrode recordings"
    Analysis: Contains 'tetrode' (a probe type)
    Response: {{"model": "Recording", "filters": {{"probe_type": "Tetrode"}}}}
    """
    user = {"role": "user", "content": question}
    resp = openai.chat.completions.create(
        model="gpt-4.1-nano-2025-04-14",
        temperature=0.2,
        tools=[search_tool],
        messages=[{"role": "system", "content": system}, user],
    )

    # Check if tool_calls exists and is not empty
    if not resp.choices[0].message.tool_calls:
        raise ValueError(
            "Unable to parse your query. Please try again with more details."
        )

    return resp.choices[0].message.tool_calls[0]


def run_query(call, question, debug=False):
    data = json.loads(call.function.arguments)

    # NEW CODE: Convert entities to filters if they exist
    if "entities" in data:
        if "filters" not in data:
            data["filters"] = {}

        # Brain regions → brain_region filter
        if "brain_regions" in data["entities"] and data["entities"]["brain_regions"]:
            brain_region = data["entities"]["brain_regions"][0]
            data["filters"]["brain_region"] = canonical(
                brain_region
            )  # Use canonical instead of direct assignment

        # Probe types → probe_type filter
        if "probe_types" in data["entities"] and data["entities"]["probe_types"]:
            probe_type = data["entities"]["probe_types"][0]
            data["filters"]["probe_type"] = canonical(
                probe_type
            )  # Use canonical instead

        # Subject states → subject__state filter
        if "subject_states" in data["entities"] and data["entities"]["subject_states"]:
            state = canonical(data["entities"]["subject_states"][0])  # Use canonical
            if data["model"] == "Recording":
                data["filters"]["subject__state"] = state
            elif data["model"] == "Subject":
                data["filters"]["state"] = state

    # Ensure filters exist to match Payload schema requirements
    if "filters" not in data:
        data["filters"] = {}

    # Rest of your existing keyword handling and defaults
    if debug:
        print("Before defaults →", json.dumps(data, indent=2))

    data = apply_defaults(data, question)

    if debug:
        print("After defaults →", json.dumps(data, indent=2))

    payload = Payload(**data)
    Model = apps.get_model("lab", payload.model)

    # Create case-insensitive filters by using __iexact lookup
    filters = {}
    for k, v in payload.filters.items():
        if isinstance(v, str) and not k.endswith("__iexact"):
            filters[f"{k}__iexact"] = canonical(v)
        else:
            filters[k] = canonical(v)

    qs = Model.objects.filter(**filters)

    # Check if results exist
    if not qs.exists():
        # No matching results
        return [
            {
                "message": "No results found",
                # query_details": {
                # "model": payload.model,
                # "filters_applied": filters,
                # "search_terms": question
                # },
                "suggestion": "Try a different search term or check spelling",
            }
        ]

    # Results exist, return them
    return list(qs.values())[:20]  # cap at 20 rows for demo
