# Bibha.ai Integration Guide

> Real integration with Bibha.ai AgentsHub based on official API documentation.

---

## API Overview

### Authentication
```
Authorization: Bearer bah-sk-your-api-key
```

### Main Endpoint
```
POST /api/v1/prediction/{chatflowId}
```

### Request Format
```json
{
  "question": "User message",
  "sessionId": "unique-session-id",
  "overrideConfig": {
    "temperature": 0.7
  }
}
```

### Response Format
```json
{
  "text": "Agent response",
  "chatId": "chat-abc123",
  "chatMessageId": "msg-xyz789",
  "sourceDocuments": []
}
```

---

## Integration Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  User Channels (WhatsApp, Web, Phone)                           │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│  Bibha.ai AgentsHub                                             │
│  - Multi-channel orchestration                                  │
│  - Conversation session management                              │
│  - Agent routing                                                │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTP Tool / Webhook
                          │ POST /api/v1/prediction/{chatflowId}
┌─────────────────────────▼───────────────────────────────────────┐
│  Easy Agent Builder Adapter                                     │
│  - Receives Bibha requests                                      │
│  - Processes via ADK                                            │
│  - Returns Bibha-compatible format                              │
└─────────────────────────┬───────────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────────┐
│  ADK Agent (Google/Gemini)                                      │
│  - LLM processing                                               │
│  - Custom tools                                                 │
│  - RAG (optional)                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Setup Guide

### Step 1: Get Bibha Credentials

In Bibha AgentsHub dashboard:
1. Go to **Utils → API Keys**
2. Click **"Create API Key"**
3. Copy the key (format: `bah-sk-...`)
4. Note your **chatflowId** (e.g., "sales-flow-001")

### Step 2: Configure Environment Variables

```bash
# .env
BIBHA_API_KEY=bah-sk-your-key-here
BIBHA_API_HOST=https://your-instance.bibha.ai
BIBHA_CHATFLOW_ID=your-chatflow-id
```

### Step 3: Deploy Adapter

```bash
# Deploy to Cloud Run
gcloud run deploy bibha-adapter \
  --source . \
  --set-env-vars BIBHA_API_KEY=bah-sk-xxx \
  --set-env-vars BIBHA_API_HOST=https://xxx.bibha.ai \
  --set-env-vars BIBHA_CHATFLOW_ID=xxx
```

### Step 4: Configure HTTP Tool in Bibha

1. Go to **Utils → Toolkit**
2. Click **"Add Tool"**
3. Configure:

**Name:** `ADK Agent Bridge`

**Method:** `POST`

**URL:** `https://your-adapter-url.run.app/api/v1/prediction/{{chatflowId}}`

**Headers:**
```json
{
  "Content-Type": "application/json"
}
```

**Body:**
```json
{
  "question": "{{user_message}}",
  "sessionId": "{{session_id}}",
  "chatflowId": "{{chatflow_id}}",
  "metadata": {
    "channel": "{{channel}}",
    "user_id": "{{user_id}}"
  }
}
```

### Step 5: Test

Send a message through Bibha's chat interface. It will:
1. Be received by Bibha
2. Forwarded to your adapter
3. Processed by ADK agent
4. Returned to the user

---

## Adapter Endpoints

### POST /api/v1/prediction/{chatflowId}
Bibha-compatible endpoint. Receives messages and returns responses.

### POST /webhook/bibha
Alternative webhook endpoint.

### GET /health
Health check for monitoring.

---

## Data Mapping

### Bibha → ADK
| Bibha Field | ADK Field | Description |
|-------------|-----------|-------------|
| `question` | `new_message` | User message |
| `sessionId` | `session_id` | Session identifier |
| `chatflowId` | `app_name` | Chatflow context |
| `metadata` | `state` | Additional data |

### ADK → Bibha
| ADK Field | Bibha Field | Description |
|-----------|-------------|-------------|
| `content` | `text` | Agent response |
| `session_id` | `sessionId` | Session continuity |
| `sourceDocuments` | `sourceDocuments` | RAG sources |

---

## Complete Conversation Flow

### Scenario: Customer asks about pricing via WhatsApp

```
1. Customer sends message on WhatsApp
   "Hi, what's the price for Enterprise plan?"

2. Bibha receives the message
   - Identifies: channel=whatsapp, phone=+55...
   - Creates/maintains session: sessionId="sess-abc-123"
   - Checks: which agent should respond?

3. Bibha calls our agent (via HTTP Tool)
   POST https://adapter.run.app/api/v1/prediction/sales
   {
     "question": "Hi, what's the price...",
     "sessionId": "sess-abc-123",
     "chatflowId": "sales",
     "metadata": {
       "channel": "whatsapp",
       "phone": "+551199999..."
     }
   }

4. Our Adapter receives and processes
   - Creates ADK session with ID "sess-abc-123"
   - Executes sales agent
   - Agent can:
     * Query CRM (custom tool)
     * Get current pricing
     * Apply business rules
   - Generates response

5. Our Adapter returns to Bibha
   {
     "text": "Hello! The Enterprise plan is $5,000/month...",
     "sessionId": "sess-abc-123",
     "chatId": "chat-sales-001"
   }

6. Bibha receives the response
   - Formats if necessary
   - Adds to conversation history
   - Sends back to customer's WhatsApp

7. Customer receives response on WhatsApp
   "Hello! The Enterprise plan is $5,000/month..."
```

---

## Customization

### Adding Metadata

Pass extra information from Bibha to ADK:

```json
{
  "question": "{{user_message}}",
  "sessionId": "{{session_id}}",
  "metadata": {
    "channel": "whatsapp",
    "user_phone": "{{phone}}",
    "campaign": "black-friday-2024"
  }
}
```

Access in ADK agent via `session.state`.

### Session Management

Bibha sends `sessionId` to maintain context. The adapter:
1. Uses the same `sessionId` in ADK
2. Persists state between messages
3. Enables continuous conversations

---

## Troubleshooting

### Error 401 - Unauthorized
```
Check: Is BIBHA_API_KEY configured correctly?
```

### Error 404 - Chatflow not found
```
Check: Does the chatflowId exist in Bibha?
```

### Timeout
```
Bibha has default timeout. Responses must be < 30s.
For long processing, use async webhooks.
```

### Session not persisting
```
Check if sessionId is being passed correctly
from Bibha to the adapter.
```

---

## Resources

- **Code:** `examples/10_bibha_integration_real.py`
- **Adapter:** `src/agent_builder/bibha_adapter_real.py`
- **Bibha Docs:** `BIBHA_AGENTSHUB_USER_GUIDE_COMPLETE.html`

---

## Integration Checklist

- [ ] Bibha API Key generated
- [ ] Chatflow ID identified
- [ ] Adapter deployed
- [ ] HTTP Tool configured in Bibha
- [ ] Message test working
- [ ] Session persistence validated
- [ ] Logs monitoring errors

---

**Ready to integrate!** 🚀
