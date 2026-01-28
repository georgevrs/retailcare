# RetailCare AI Call Center - Complete Project Explanation

## Overview

**RetailCare** is an end-to-end AI-powered call center demo application designed for a Greek retail shop. It demonstrates a complete voice-first customer service solution that can handle incoming phone calls, understand customer intent in Greek, answer questions from a knowledge base, and automatically create support tickets for complaints.

## Core Purpose

The system serves as a proof-of-concept for an intelligent call center that:
- **Automatically answers phone calls** using Azure Communication Services
- **Understands Greek speech** using Azure AI Speech (Speech-to-Text and Text-to-Speech)
- **Intelligently routes conversations** using Azure OpenAI (GPT-4) to distinguish between:
  - **Information requests** (e.g., "What are your store hours?")
  - **Complaints** (e.g., "My order #12345 is late")
- **Answers questions** from a local FAQ knowledge base
- **Creates support tickets** automatically in GitHub Issues when customers report problems

## Technology Stack

### Backend Framework
- **Azure Functions (Python)**: Serverless backend that handles HTTP webhooks and call events
- **Python 3.11+**: Main programming language

### Azure Services
1. **Azure Communication Services (ACS)**
   - Manages phone call lifecycle (incoming calls, call control, media streaming)
   - Handles call automation (answering, playing audio, recognizing speech)
   - Provides phone number management

2. **Azure AI Speech**
   - **Speech-to-Text (STT)**: Converts Greek spoken words to text (`el-GR` locale)
   - **Text-to-Speech (TTS)**: Converts AI responses back to Greek speech
   - Uses Neural voices for natural-sounding Greek audio

3. **Azure OpenAI**
   - **GPT-4o** model for conversation orchestration
   - Function calling/tool use for:
     - Searching FAQ knowledge base
     - Creating GitHub tickets
   - Intent classification (complaint vs. information request)

### External Integrations
- **GitHub Issues API**: Lightweight ticketing system for customer complaints
  - Automatically creates issues with labels (category, urgency, channel)
  - Includes caller phone number, order ID, product details

## Architecture & Data Flow

### Call Flow (Real Phone Call)

```
1. Customer calls phone number → Azure Communication Services receives call
   ↓
2. EventGrid webhook → POST to /api/acs/events
   ↓
3. Function App answers call → ACS Call Automation API
   ↓
4. Call Connected event → POST to /api/acs/callback
   ↓
5. System plays Greek greeting via TTS
   ↓
6. System starts continuous speech recognition (listening loop)
   ↓
7. Customer speaks → Speech-to-Text converts to Greek text
   ↓
8. RecognizeCompleted event → POST to /api/acs/callback
   ↓
9. Agent processes utterance:
   - Sends to Azure OpenAI with conversation history
   - AI determines intent (complaint vs. information)
   - If complaint: Calls create_ticket tool → GitHub API
   - If information: Calls search_faq tool → Local FAQ search
   ↓
10. AI generates Greek response text
   ↓
11. Response converted to speech via TTS
   ↓
12. Audio played to customer
   ↓
13. Loop back to step 6 (continuous conversation)
```

### Simulation Flow (Testing Without Phone)

```
1. POST to /api/dev/simulate with JSON body: {"text": "Greek text here"}
   ↓
2. Agent processes text directly (no STT/TTS)
   ↓
3. Returns JSON response with:
   - Intent classification
   - AI response text
   - Ticket ID (if created)
   - Conversation history length
```

## Project Structure

```
RetailCare/
├── function_app.py          # Azure Functions entry points (HTTP triggers)
├── host.json                 # Azure Functions host configuration
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variable template
├── README.md                 # Quick start guide
├── SETUP_GUIDE.md            # Detailed setup instructions
│
├── src/
│   ├── agent.py              # Core AI agent (OpenAI integration, tool calling)
│   ├── acs.py                # Azure Communication Services call control
│   ├── speech.py             # Speech configuration (voice name, locale)
│   ├── faq.py                # FAQ knowledge base search logic
│   ├── github_issues.py      # GitHub Issues API integration
│   ├── state.py              # Session management (conversation history, tickets)
│   └── models.py             # Data models (Intent, TicketDetails, AgentResponse)
│
├── data/
│   └── faq_el.json           # Greek FAQ knowledge base (questions/answers)
│
└── tests/                    # Test files for various components
```

## Key Components Explained

### 1. `function_app.py` - HTTP Endpoints

Three main HTTP endpoints:

- **`/api/acs/events`**: Receives EventGrid webhooks from Azure Communication Services
  - Handles `IncomingCall` events
  - Validates EventGrid subscriptions
  - Automatically answers incoming calls

- **`/api/acs/callback`**: Receives Call Automation callbacks
  - Handles `CallConnected`, `RecognizeCompleted`, `CallDisconnected` events
  - Orchestrates the conversation loop (play → recognize → process → repeat)

- **`/api/dev/simulate`**: Development/testing endpoint
  - Simulates a call without requiring a phone line
  - Accepts plain text input, returns AI response

### 2. `src/agent.py` - AI Agent Logic

The `CallCenterAgent` class:
- Initializes Azure OpenAI client
- Maintains conversation context via session history
- Uses function calling with two tools:
  - `search_faq(query)`: Searches local FAQ for information
  - `create_ticket(title, description, category, urgency, ...)`: Creates GitHub issue
- System prompt in Greek instructs the AI to:
  - Speak only in Greek
  - Distinguish complaints from information requests
  - Be decisive (create tickets immediately when problem is clear)
  - Ask one question at a time if details are missing

### 3. `src/acs.py` - Call Control

The `ACSCallHandler` class:
- Manages Azure Communication Services client
- `answer_call()`: Answers incoming calls
- `play_and_recognize()`: Plays TTS audio and starts continuous speech recognition
- Handles participant identification (phone numbers vs. communication users)

### 4. `src/state.py` - Session Management

- **`CallSession`**: Stores conversation state per call
  - `call_connection_id`: Unique identifier for the call
  - `phone_number`: Caller's phone number
  - `conversation_history`: List of messages (user/assistant turns)
  - `ticket_id` & `ticket_url`: If a ticket was created
  - `greeting_triggered`: Prevents duplicate greetings

- **`SessionStore`**: Persists sessions to disk (temp directory)
  - Sessions saved as JSON files
  - Allows conversation history to persist across multiple turns

### 5. `src/github_issues.py` - Ticketing Integration

- Creates GitHub Issues via REST API
- Formats tickets with:
  - Title: `[Call Center] Category - Summary`
  - Body: Caller phone, category, urgency, order ID, product, description
  - Labels: Category, urgency level, `channel:phone`

### 6. `src/faq.py` - Knowledge Base

- Loads FAQ from `data/faq_el.json`
- Simple keyword/search matching for Greek questions
- Returns best matching answer

## Configuration

### Environment Variables (`.env` file)

```bash
# Azure Communication Services
ACS_CONNECTION_STRING=endpoint=https://...;accesskey=...
ACS_CALLBACK_URL=https://your-app.azurewebsites.net/api/acs/events

# Azure AI Speech
SPEECH_KEY=your_speech_key
SPEECH_REGION=westeurope

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_KEY=your_key
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# GitHub
GITHUB_OWNER=your_username
GITHUB_REPO=your_repo_name
GITHUB_TOKEN=your_fine_grained_pat
```

### Azure Resources Required

1. **Azure Communication Services Resource**
   - Provides phone number
   - Generates connection string
   - Sends EventGrid events for incoming calls

2. **Azure AI Speech Resource**
   - Region: `westeurope` recommended (for Greek Neural voices)
   - Provides STT/TTS capabilities

3. **Azure OpenAI Resource**
   - Deploy `gpt-4o` model
   - Provides conversation intelligence

4. **Azure Function App**
   - Hosts the Python functions
   - Receives webhooks from ACS
   - Must be publicly accessible (or use ngrok for local dev)

## Setup Process

### 1. Local Development Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Azure/GitHub credentials

# Run locally
func start
```

### 2. Testing Without Phone (Simulation)

```bash
# Test complaint handling
curl -X POST http://localhost:7071/api/dev/simulate \
  -H "Content-Type: application/json" \
  -d '{"text": "Θέλω να αναφέρω ένα πρόβλημα. Η παραγγελία μου #12345 δεν έχει έρθει ακόμα."}'

# Test information request
curl -X POST http://localhost:7071/api/dev/simulate \
  -H "Content-Type: application/json" \
  -d '{"text": "Ποιο είναι το ωράριο του καταστήματος το Σάββατο;"}'
```

### 3. Real Phone Call Setup

1. **Deploy Function App to Azure** (or use ngrok for local testing)
2. **Configure EventGrid Webhook**:
   - In Azure Portal → ACS Resource → Events
   - Create Event Subscription
   - Endpoint: `https://your-app.azurewebsites.net/api/acs/events`
   - Events: `Call Connected`, `Recognize Completed`, `Call Disconnected`
3. **Call the phone number** acquired in ACS
4. **System automatically**:
   - Answers the call
   - Plays Greek greeting
   - Listens for customer input
   - Processes and responds

## Key Features

### 1. Intent Recognition
The AI automatically classifies customer input:
- **COMPLAINT_TICKET**: Customer reports a problem → Creates GitHub issue
- **INFORMATION**: Customer asks a question → Searches FAQ
- **GREETING/GOODBYE**: Social interactions

### 2. Automatic Ticket Creation
When a complaint is detected:
- AI extracts: title, description, category, urgency, order ID, product
- Creates GitHub Issue with formatted body
- Confirms ticket number to customer in Greek

### 3. FAQ Knowledge Base
- Local JSON file with Greek Q&A pairs
- AI searches FAQ when information is requested
- Falls back to "will forward to representative" if no match

### 4. Continuous Conversation
- Maintains conversation history across turns
- Context-aware responses
- Can handle multi-turn conversations (e.g., collecting missing details)

### 5. Greek Language Support
- Full Greek STT/TTS (`el-GR` locale)
- Neural voice for natural speech
- All AI prompts and responses in Greek

## Dependencies

From `requirements.txt`:
- `azure-functions`: Azure Functions runtime
- `azure-communication-callautomation`: ACS call control SDK
- `openai`: Azure OpenAI SDK
- `azure-cognitiveservices-speech`: Speech services SDK
- `pydantic`: Data validation
- `httpx`: Async HTTP client (for GitHub API)
- `python-dotenv`: Environment variable loading

## Deployment

1. **Deploy to Azure Function App**:
   - Use VS Code Azure Functions extension, or
   - Use Azure CLI: `func azure functionapp publish <app-name>`

2. **Configure Application Settings**:
   - Add all environment variables from `.env` to Function App settings

3. **Set up EventGrid Webhook** (as described in Setup Process)

## Use Cases

1. **Customer Service Automation**: Handle common questions and complaints without human agents
2. **24/7 Support**: Always-available voice interface
3. **Ticket Routing**: Automatically create and categorize support tickets
4. **Multilingual Support**: Can be adapted to other languages by changing locale and FAQ

## Limitations & Considerations

- **Session Storage**: Uses local temp directory (not suitable for production scale)
- **FAQ Search**: Simple keyword matching (could be enhanced with semantic search)
- **Error Handling**: Basic retry logic for speech recognition failures
- **Scalability**: Azure Functions auto-scale, but session storage needs improvement for production

## Future Enhancements

- Replace file-based session storage with Azure Cosmos DB or Redis
- Add semantic search for FAQ (Azure AI Search)
- Support multiple languages
- Add analytics and call recording
- Integrate with CRM systems instead of GitHub
- Add sentiment analysis
- Support for call transfers to human agents

---

## Summary

RetailCare is a **production-ready demo** of an AI call center that combines:
- **Azure Communication Services** for telephony
- **Azure AI Speech** for Greek voice interaction
- **Azure OpenAI** for intelligent conversation
- **GitHub Issues** for ticketing

It demonstrates how modern AI can automate customer service calls with natural language understanding, automatic ticket creation, and knowledge base integration—all in Greek.
