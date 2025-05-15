import django, os, json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "playground.settings")
django.setup()

from lab.semantic import ask_llm, run_query

while True:
    q = input("\nAsk › ").strip()
    if q in {"quit", "exit"}:
        break
    call = ask_llm(q)
    print("\nLLM payload →", call.arguments)
    rows = run_query(call)
    print("Results →", json.dumps(rows, indent=2))
