# RetailCare Agentic Call Center Demo

An end-to-end AI call center demo for a Greek retail shop. This solution uses Azure Communication Services (ACS) for call handling, Azure AI Speech for Greek STT/TTS, and Azure OpenAI for the agentic intelligence.

## Features
- **Voice-first Interface**: Automatic speech recognition and synthesis in Greek (`el-GR`).
- **Intent Recognition**: Automatically distinguishes between complaints and information requests.
- **Agentic Ticketing**: Automatically creates GitHub Issues for customer complaints with appropriate labels and urgency.
- **Knowledge Base**: Answers common retail questions from a local FAQ knowledge base.
- **Simulation Mode**: Test the AI logic without requiring a real phone line.

## Architecture
- **Azure Functions (Python)**: Serverless backend.
- **ACS Call Automation**: Manages the call lifecycle and media.
- **Azure OpenAI**: Orchestrates the conversation and tool calling.
- **GitHub Issues**: Lightweight ticketing system.

## Prerequisites
1. **Azure Subscription**:
   - Create an **Azure Communication Services** resource.
   - Create an **Azure AI Speech** resource (region: `westeurope` recommended).
   - Create an **Azure OpenAI** resource and deploy a model (e.g., `gpt-4o`).
2. **GitHub**:
   - A repository to host the tickets.
   - A Fine-grained Personal Access Token (PAT) with `issues:write` permissions.
3. **Local Tools**:
   - [Azure Functions Core Tools](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local)
   - Python 3.11+

## Configuration
Create a `.env` file (see `.env.example`) or set environment variables:

```bash
# ACS
ACS_CONNECTION_STRING="your_connection_string"
ACS_CALLBACK_URL="https://your-domain.com/api/acs/events"

# Speech
SPEECH_KEY="your_speech_key"
SPEECH_REGION="westeurope"

# OpenAI
AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
AZURE_OPENAI_KEY="your_key"
AZURE_OPENAI_DEPLOYMENT="gpt-4o"

# GitHub
GITHUB_OWNER="username"
GITHUB_REPO="repo_name"
GITHUB_TOKEN="your_pat"
```

## Local Development & Testing

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run Locally**:
   ```bash
   func start
   ```

3. **Simulate a Call (No Phone Needed)**:
   Use the `/api/dev/simulate` endpoint to test the agent logic.

   **Example Request (Complaint)**:
   ```bash
   curl -X POST http://localhost:7071/api/dev/simulate \
     -H "Content-Type: application/json" \
     -d '{"text": "Θέλω να αναφέρω ένα πρόβλημα. Η παραγγελία μου #12345 δεν έχει έρθει ακόμα και έχω καθυστέρηση 5 ημέρες."}'
   ```

   **Example Request (Information)**:
   ```bash
   curl -X POST http://localhost:7071/api/dev/simulate \
     -H "Content-Type: application/json" \
     -d '{"text": "Ποιο είναι το ωράριο του καταστήματος το Σάββατο;"}'
   ```

## Deployment to Azure

1. **Deploy Function App**: Use VS Code Azure Functions extension or Azure CLI.
2. **Required app setting (Python v2)**  
   In Azure Portal → Function App → **Configuration** → **Application settings**, add:
   - **Name**: `AzureWebJobsFeatureFlags`
   - **Value**: `EnableWorkerIndexing`  

   Without this, the host reports "0 functions found" and your HTTP triggers will not load. Save and restart the app after adding it.
3. **Configure ACS Webhook**:
   - Go to your ACS resource in Azure Portal.
   - Navigate to **Events**.
   - Create an **Event Subscription**.
   - Endpoint Type: **Webhook**.
   - Endpoint URL: `https://<your-app>.azurewebsites.net/api/acs/events`.
   - Filter Events: Select `Call Connected`, `Recognize Completed`, `Call Disconnected`.

## Project Structure
- `function_app.py`: Azure Functions entry points.
- `src/agent.py`: LLM logic and tool calling.
- `src/acs.py`: ACS media and call control logic.
- `src/github_issues.py`: Ticketing integration.
- `src/faq.py`: Knowledge base search.
- `src/state.py`: Session management.
- `data/faq_el.json`: Local FAQ data in Greek.
