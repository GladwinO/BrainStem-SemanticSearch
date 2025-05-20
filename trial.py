import django, os, json, os, sys # sys good for production code

from dotenv import load_dotenv
from lab.semantic import ask_llm, run_query

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "playground.settings")
django.setup()

## This section is for local API connection ##
load_dotenv() # Load environment variables from .env file

try:
    key = os.environ["OPENAI_API_KEY"]
except KeyError:
    print("Error: OPENAI_API_KEY environment variable is required")
    sys.exit(1) # good for production code

###############################################

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
