# GOOGLE_SHEETS_INTEGRATION.md
# Google Sheets Lead Logger – Setup Guide

---

## 📋 Sheet Structure

Create a Google Sheet with these exact column headers in Row 1:

| A | B | C | D | E |
|---|---|---|---|---|
| Timestamp | الاسم (Name) | الهاتف (Phone) | البرنامج (Program) | ملخص المكالمة (Summary) |

**Sheet name:** `Leads` (or any name – update in config)

---

## 🔑 Step 1: Google Service Account Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. Enable **Google Sheets API**:
   - APIs & Services → Enable APIs → Search "Google Sheets API" → Enable
4. Create a **Service Account**:
   - APIs & Services → Credentials → Create Credentials → Service Account
   - Name: `voice-agent-sheets`
   - Role: `Editor`
5. Download the JSON key:
   - Click the service account → Keys → Add Key → JSON → Download
   - This is your `google_credentials.json`

---

## 🔑 Step 2: Share the Sheet with the Service Account

1. Open your Google Sheet
2. Click **Share**
3. Paste the service account email (looks like: `voice-agent-sheets@your-project.iam.gserviceaccount.com`)
4. Give it **Editor** access
5. Uncheck "Notify people"
6. Click **Done**

---

## 🔑 Step 3: Get Your Spreadsheet ID

From your sheet URL:
```
https://docs.google.com/spreadsheets/d/SPREADSHEET_ID_IS_HERE/edit
```
Copy the ID between `/d/` and `/edit`.

---

## 🔑 Step 4: Configure in Antigravity

In Antigravity, go to **Secrets / Environment Variables** and add:

```
GOOGLE_CREDENTIALS_JSON = <paste entire contents of your JSON key file>
SPREADSHEET_ID = <your spreadsheet ID>
SHEET_NAME = Leads
```

---

## 🔑 Step 5: Tool Configuration in Antigravity

Use this as the HTTP tool config for `google_sheets_append`:

```json
{
  "name": "google_sheets_append",
  "description": "Append a new lead row to Google Sheets",
  "type": "http",
  "auth": {
    "type": "google_service_account",
    "scopes": ["https://www.googleapis.com/auth/spreadsheets"],
    "credentials_env_var": "GOOGLE_CREDENTIALS_JSON"
  },
  "request": {
    "method": "POST",
    "url": "https://sheets.googleapis.com/v4/spreadsheets/{{env.SPREADSHEET_ID}}/values/{{env.SHEET_NAME}}!A:E:append",
    "query_params": {
      "valueInputOption": "USER_ENTERED",
      "insertDataOption": "INSERT_ROWS"
    },
    "headers": {
      "Content-Type": "application/json"
    },
    "body": {
      "values": [[
        "{{call.timestamp}}",
        "{{call.lead_name}}",
        "{{call.lead_phone}}",
        "{{call.program_interest}}",
        "{{call.conversation_summary}}"
      ]]
    }
  }
}
```

---

## 🔑 Step 6: Summary Generation Prompt

Instruct the Sheets Writer Agent to generate the summary using this prompt before writing:

```
Based on this conversation transcript, write a 2-3 sentence summary in Arabic.
Include: what the caller asked about, what information was given, and the outcome.
Be factual and concise. Do not add information not present in the transcript.

Transcript:
{{call.transcript}}
```

---

## ✅ Test the Integration

After setup, trigger a test call with fake data:
- Name: تجربة تجربة
- Phone: 01000000000
- Program: الذكاء الاصطناعي

Verify a new row appears in the sheet within 5 seconds of call end.

---

## 🛡️ Data Security

- Keep your `google_credentials.json` secret – never commit to GitHub
- Restrict sheet access to only the service account + your team
- Consider adding a **Protected Range** on the header row
- Enable Google Sheets **Audit Log** for compliance tracking

---

## 📊 Recommended Sheet Formatting

Apply these to make the sheet easier to read:

| Column | Format |
|--------|--------|
| A (Timestamp) | Date-time format: `DD/MM/YYYY HH:MM` |
| B (Name) | Text, right-to-left |
| C (Phone) | Plain text (not number – avoid losing leading zero) |
| D (Program) | Dropdown validation (optional) |
| E (Summary) | Text, wrap text on |

Freeze Row 1 (headers): View → Freeze → 1 row
