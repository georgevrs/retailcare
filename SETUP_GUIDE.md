# Comprehensive Setup Guide: RetailCare AI Call Center

This guide provides step-by-step instructions to set up the Azure infrastructure, GitHub integration, and local environment for the RetailCare AI Call Center.

---

## 1. Azure Infrastructure Setup

### A. Azure Communication Services (ACS)
1. **Create Resource**: Search for "Communication Services" in the Azure Portal and create a new resource.
2. **Get Connection String**:
   - Go to the **Keys** blade under Settings.
   - Copy the **Primary Connection String**. This goes into `ACS_CONNECTION_STRING`.
3. **Get a Phone Number** (Required for real calls):
   - Go to **Phone Numbers** under "Voice & SMS".
   - Click **Get** and follow the prompts to acquire a number (Note: Availability depends on region/regulatory requirements).
4. **Identity & Auth**: Ensure the resource has "Cognitive Services User" role if you use managed identity (not required for this demo as we use connection strings).

### B. Azure AI Speech
1. **Create Resource**: Search for "Speech Services" and create a resource.
2. **Region**: Choose `westeurope` or `eastus` for best availability of Neural voices.
3. **Get Keys**:
   - Go to **Keys and Endpoint**.
   - Copy **Key 1** (`SPEECH_KEY`) and the **Location/Region** (`SPEECH_REGION`).

### C. Azure OpenAI
1. **Create Resource**: Search for "Azure OpenAI" and create a resource.
2. **Deploy Model**:
   - Go to **Azure AI Studio** (oai.azure.com).
   - Go to **Deployments** and click **Create new deployment**.
   - Select `gpt-4o` (or `gpt-4-turbo`).
   - Deployment Name: Use `gpt-4o` or match your `AZURE_OPENAI_DEPLOYMENT` env var.
3. **Get Keys**:
   - Go to **Keys and Endpoint** in the Azure Portal for the OpenAI resource.
   - Copy **Key 1** (`AZURE_OPENAI_KEY`) and the **Endpoint** (`AZURE_OPENAI_ENDPOINT`).

---

## 2. GitHub Ticketing Setup

1. **Target Repo**: Create a new GitHub repository or use an existing one.
2. **Generate PAT**:
   - Go to GitHub **Settings** > **Developer settings** > **Personal access tokens** > **Fine-grained tokens**.
   - Click **Generate new token**.
   - Repository access: **Only select repositories** (choose your repo).
   - Permissions: **Repository permissions** > **Issues** > **Access: Read and write**.
   - Copy the token for `GITHUB_TOKEN`.
3. **Environment**:
   - `GITHUB_OWNER`: Your GitHub username or organization name.
   - `GITHUB_REPO`: The name of the repository.

---

## 3. Local Environment Configuration

1. **Install Azure Functions Core Tools**:
   - Follow instructions [here](https://learn.microsoft.com/en-us/azure/azure-functions/functions-run-local).
2. **Python Setup**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```
3. **Local Settings**:
   - Copy `.env.example` to `.env`.
   - Fill in all the keys gathered in steps 1 and 2.
   - For local development, also update `local.settings.json` with the same values under `"Values"`.

---

## 4. Webhook & EventGrid Configuration (CRITICAL)

To handle real calls, Azure must notify your Function App when a call is received.

1. **Expose Local Function**:
   - Use **ngrok** to create a tunnel to your local port 7071: `ngrok http 7071`.
   - Your callback URL will be `https://<ngrok-id>.ngrok-free.app/api/acs/events`.
2. **Configure EventGrid**:
   - In the Azure Portal, go to your **ACS Resource**.
   - Click **Events** > **+ Event Subscription**.
   - **Name**: `CallCenterWebhook`.
   - **Event Types**: Select `Call Connected`, `Recognize Completed`, `Call Disconnected`, and `Play Completed`.
   - **Endpoint Type**: `Webhook`.
   - **Endpoint**: Paste your ngrok URL or your deployed Azure Function URL ending in `/api/acs/events`.
3. **Validation**: Azure will send a validation event to the endpoint. The `function_app.py` is already configured to handle this and return the `validationResponse`.

---

## 5. Testing Flow

### Scenario A: Simulation (No Infrastructure Needed)
1. Start the function: `func start`.
2. Send a POST request to `http://localhost:7071/api/dev/simulate` with a Greek JSON body.
3. Observe the response and check your GitHub repository for a new issue.

### Scenario B: Real Phone Call
1. Start the function and ensure ngrok is running (or deploy to Azure).
2. Configure the ACS Webhook (Step 4).
3. Call the phone number you acquired in ACS (Step 1.A.3).
4. You should hear the Greek greeting: *"Καλησπέρα σας! Είμαι η ψηφιακή εξυπηρέτηση..."*
5. Speak in Greek (e.g., *"Θέλω να ρωτήσω για τις επιστροφές"*) and wait for the AI response.

---

## 6. Troubleshooting
- **Linter Errors**: If you see `azure.functions` missing, ensure your Python interpreter in VS Code is set to the `.venv` where requirements were installed.
- **Greek Audio**: If the speech sounds robotic, verify `VOICE_NAME` in `src/speech.py` matches an available Neural voice in your region.
- **GitHub Failures**: Ensure the PAT has "Issues" write access and that the `GITHUB_OWNER` and `GITHUB_REPO` match exactly.
