import django, os, json

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "playground.settings")
django.setup()

from lab.semantic import ask_llm, run_query

while True:
    q = input("\nAsk › ").strip()
    if q in {"quit", "exit"}:
        break
    if not q:
        print("Please enter a query.")
        continue

    try:
        call = ask_llm(q)
        print("\nLLM payload →", call.function.arguments)
        rows = run_query(call, q)  # Pass the question too
        print("Results →", json.dumps(rows, indent=2))
    except ValueError as e:
        print(f"Error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
