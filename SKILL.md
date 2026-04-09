# SKILL.md – Antigravity Voice Agent Configuration
# المحكمة العربية للتحكيم | Arabic Arbitration Training Center

---

## 1. Agent Identity

| Field | Value |
|-------|-------|
| **Agent Name** | مساعد مركز التدريب (Training Center Assistant) |
| **Voice Language** | Arabic (ar-EG Egyptian dialect preferred) |
| **Fallback Language** | English (en-US) |
| **Persona** | Warm, professional female/male voice – training consultant |
| **Tone** | Helpful, clear, never pushy |

---

## 2. Antigravity Project Settings

```yaml
project:
  name: arabic-arbitration-voice-agent
  type: voice
  primary_language: ar-EG
  fallback_language: en-US

telephony:
  inbound: true
  outbound: true          # for follow-up calls
  dtmf_enabled: false     # voice-only interaction

tts:                      # Text-to-Speech
  provider: elevenlabs    # or azure / google – whichever Antigravity supports
  voice_id: <YOUR_ARABIC_VOICE_ID>
  speed: 0.95             # slightly slower for clarity

stt:                      # Speech-to-Text
  provider: deepgram      # or whisper
  language: ar
  detect_language: true   # auto-switch if caller speaks English

silence_timeout: 5s       # hang up after 5s silence at end
max_call_duration: 15m
```

---

## 3. Multi-Agent Setup (Anti-Hallucination Architecture)

Define **4 agents** inside Antigravity:

### Agent 1 – Orchestrator
```
Role: Route the conversation. NEVER answer questions directly.
      Always delegate to the correct sub-agent.
Tools: call_info_agent, call_lead_agent, call_sheets_agent
```

### Agent 2 – Info Agent (FAQ/Knowledge)
```
Role: Answer ONLY questions about training programs.
      Source: KNOWLEDGE_BASE.md (loaded as a document tool).
      If answer not in knowledge base → say "سأحول سؤالك لفريق المتخصصين"
      NEVER invent details, prices, or dates not in the knowledge base.
```

### Agent 3 – Lead Capture Agent
```
Role: Collect caller name, phone number, and program interest.
      Validate phone: must be 10-11 digits Egyptian/Arab format.
      Confirm data back to caller before saving.
Tools: write_to_sheets
```

### Agent 4 – Sheets Writer Agent
```
Role: Write one row to Google Sheets after lead is confirmed.
      Fields: timestamp, name, phone, interest, conversation_summary
      On failure: retry once, then flag for manual review.
Tools: google_sheets_append
```

---

## 4. Tools Required in Antigravity

| Tool Name | Type | Description |
|-----------|------|-------------|
| `knowledge_lookup` | RAG / Document | Searches KNOWLEDGE_BASE.md |
| `google_sheets_append` | HTTP / Google API | Appends row to lead sheet |
| `get_timestamp` | Built-in | Returns current Cairo time (UTC+2) |
| `summarize_conversation` | LLM call | Generates 2-3 sentence Arabic summary |

---

## 5. Tool: google_sheets_append Configuration

```json
{
  "tool_name": "google_sheets_append",
  "type": "http",
  "method": "POST",
  "url": "https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/{SHEET_NAME}!A:E:append",
  "auth": {
    "type": "google_service_account",
    "credential_key": "GOOGLE_CREDENTIALS_JSON"   
  },
  "query_params": {
    "valueInputOption": "USER_ENTERED",
    "insertDataOption": "INSERT_ROWS"
  },
  "body_template": {
    "values": [[
      "{{timestamp}}",
      "{{lead_name}}",
      "{{lead_phone}}",
      "{{program_interest}}",
      "{{conversation_summary}}"
    ]]
  }
}
```

---

## 6. Variables / State Schema

```typescript
interface CallState {
  lead_name: string | null;
  lead_phone: string | null;
  program_interest: string | null;    // e.g. "الذكاء الاصطناعي"
  conversation_summary: string | null;
  timestamp: string;                  // ISO 8601, Cairo time
  data_confirmed: boolean;            // did caller confirm their info?
  sheets_written: boolean;
}
```

---

## 7. Escalation Rules

| Trigger | Action |
|---------|--------|
| Caller asks for human | Transfer to `+20XXXXXXXXXX` |
| Info Agent can't answer | Offer callback from specialist |
| Phone validation fails 2x | Ask caller to spell it out |
| Sheets write fails | Log to internal error queue |

---

## 8. Compliance Notes

- Do NOT record calls without informing the caller (add disclosure at start)
- Phone numbers stored in Google Sheets → ensure sheet is private
- Data retention: follow Egyptian personal data protection guidelines
