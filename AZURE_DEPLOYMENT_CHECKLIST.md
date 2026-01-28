# Azure Functions deployment checklist (“0 functions found” fix)

If deployment succeeds but logs show **“0 functions found (Custom)”** / **“0 functions loaded”**, the host is not discovering your Python v2 functions. Use this checklist.

---

## 1. Why “0 functions (Custom)” happens

- **Deploy** can be fine (zip uploaded, Oryx build ran).
- The **host** scans for functions using a **metadata provider**.
- Log **“(Custom)”** = host is using the **Custom** provider, which looks for **`function.json`** files (old v1 layout).
- This project uses **Python v2**: functions are defined in **`function_app.py`** with **`@app.route(...)`**. There are no `function.json` files.
- So the host finds **zero** functions unless you turn on **worker indexing**, so the **Python worker** (not the host) discovers functions from your app.

---

## 2. Required: enable worker indexing (main fix)

In **Azure Portal** → your **Function App** → **Configuration** → **Application settings**:

| Name | Value |
|------|--------|
| `AzureWebJobsFeatureFlags` | `EnableWorkerIndexing` |

Then **Save** and **Restart** the app.

Without this, the host will keep reporting “0 functions found (Custom)” and your HTTP triggers will not load.

---

## 3. Other app settings to verify

In the same **Application settings**:

| Setting | Expected | Why |
|--------|----------|-----|
| `FUNCTIONS_WORKER_RUNTIME` | `python` | Must be exactly `python` so Azure runs the Python worker. |
| `AzureWebJobsStorage` | (connection string) | Required for the host; if missing, functions may not load. |

If either is wrong or missing, fix it, save, and restart.

---

## 4. Repo tree (top-level) — nothing missing or misplaced

This project’s **deployed root** looks like this (top-level only):

```
.
├── host.json
├── requirements.txt
├── function_app.py
├── data/
├── src/
│   ├── __init__.py
│   ├── acs.py
│   ├── agent.py
│   └── ...
└── (other files: README, .env.example, etc.)
```

- **`host.json`** — at root ✅  
- **`requirements.txt`** — at root ✅  
- **`function_app.py`** — at root ✅ with `app = func.FunctionApp(...)` and `@app.route(...)`  
- **`src/`** — only **imported** by `function_app.py`; no function definitions live here ✅  

So: **no file is missing or in the wrong place.** The “root causes” (host.json not at root, functions only under src/, missing function_app.py, no trigger decorators) do **not** apply to this repo. Azure still reports “0 functions (Custom)” because **without worker indexing the host never asks the Python worker to load `function_app.py`** — it only looks for `function.json` (Custom) and finds none.

---

## 5. What Azure expects at root (we have it)

Azure expects at the **project root** (what gets deployed as the app root):

- `host.json` ✅
- `requirements.txt` ✅
- `function_app.py` ✅ (entry point with `app = func.FunctionApp(...)` and `@app.route(...)`)

Your functions live in **`function_app.py`** at the root. The **`src/`** folder contains **modules** (imported by `function_app.py`), not function definitions—that’s correct. No `function.json` files are needed for Python v2.

---

## 6. Function definitions (this project is correct)

You use the **Python v2** model:

- `app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)`
- `@app.route(route="acs/events", methods=["POST"])`
- `@app.route(route="acs/callback", methods=["POST"])`
- etc.

So the **structure and decorators are fine**. The only thing that makes Azure “see” these functions after deploy is **worker indexing** (step 2).

---

## 7. Quick sanity check (about 60 seconds)

1. **Portal** → Function App → **Configuration** → **Application settings**  
   - `FUNCTIONS_WORKER_RUNTIME` = `python`  
   - `AzureWebJobsStorage` = present  
   - `AzureWebJobsFeatureFlags` = `EnableWorkerIndexing`

2. **Repo root** (deployed as app root):  
   - `host.json` exists  
   - `requirements.txt` exists  
   - `function_app.py` exists with `app = func.FunctionApp(...)` and `@app.route(...)`

3. **Restart** the Function App after any setting change.

---

## 8. V1 fallback: see env vars even when “0 functions found”

This project includes a **v1-style function** (`dev_env/` with `function.json`) so the host’s **Custom** metadata provider finds **at least one** function. That gives you a working endpoint to inspect configuration:

- **URL:** `https://<your-app>.azurewebsites.net/api/dev/env` (GET)
- **Returns:** JSON with `critical` (FUNCTIONS_WORKER_RUNTIME, AzureWebJobsFeatureFlags, etc.) and `all_vars` (masked secrets).

If you get **404** on `/api/dev/env` after deploy:

1. **Confirm `dev_env/` is in the deployed package**  
   Kudu: `https://<your-app>.scm.azurewebsites.net` → **Debug console** → **Bash** → run `ls -la /home/site/wwwroot` and `ls -la /home/site/wwwroot/dev_env`.  
   If `dev_env` is missing, the zip or Oryx may be dropping it. Deploy **without** remote build so the zip is used as-is (from Linux/macOS):  
   `pip install -r requirements.txt -t .python_packages/lib/site-packages` then  
   `func azure functionapp publish <APP_NAME> --no-build`.

2. **If `dev_env` is present but still 404**  
   On Linux Python the host may not discover `function.json` until worker indexing is on. Set **AzureWebJobsFeatureFlags** and **FUNCTIONS_WORKER_RUNTIME** (steps 2–3), then restart.

---

## Summary

- **Deploy success ≠ functions discovered.** The host must use the Python worker to index your `function_app.py`.
- **Fix:** Add `AzureWebJobsFeatureFlags` = `EnableWorkerIndexing`, ensure `FUNCTIONS_WORKER_RUNTIME` = `python` and `AzureWebJobsStorage` is set, then restart.
- Your repo layout and decorators are correct; no files need to be moved or renamed for “0 functions found” to be resolved.
- **V1 fallback:** Use `GET /api/dev/env` to see env vars even when only the v1 function is loaded.
