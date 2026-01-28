# V1-style function so Azure host finds at least ONE function via function.json.
# Use this to see env vars when worker indexing fails (0 functions found).
import json
import os
import azure.functions as func

CRITICAL = [
    "FUNCTIONS_WORKER_RUNTIME",
    "AzureWebJobsFeatureFlags",
    "AzureWebJobsStorage",
    "FUNCTIONS_EXTENSION_VERSION",
    "WEBSITE_SITE_NAME",
    "PYTHON_VERSION",
]


def main(req: func.HttpRequest) -> func.HttpResponse:
    env = {}
    for key, value in os.environ.items():
        if any(s in key.upper() for s in ["KEY", "SECRET", "PASSWORD", "TOKEN", "CONNECTION"]):
            env[key] = f"<SET:{len(value) or 0} chars>" if value else "<EMPTY>"
        else:
            env[key] = value
    critical = {k: os.environ.get(k, "<NOT SET>") for k in CRITICAL}
    body = json.dumps({"critical": critical, "all_vars": env}, indent=2)
    return func.HttpResponse(body, mimetype="application/json", status_code=200)
