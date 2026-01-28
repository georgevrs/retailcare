# Quick Start: Testing with Real Phone Calls

## Fastest Path to Test

### 1. Deploy Function App (5 minutes)

```bash
# If not already deployed
func azure functionapp publish <your-function-app-name>
```

### 2. Configure Webhook (2 minutes)

1. Azure Portal → ACS Resource → **Events** → **+ Event Subscription**
2. Endpoint: `https://<your-app>.azurewebsites.net/api/acs/events`
3. Events: Select `IncomingCall`, `CallConnected`, `RecognizeCompleted`, `CallDisconnected`
4. Create

### 3. Get Phone Number (1 minute)

1. Azure Portal → ACS Resource → **Phone Numbers**
2. Copy the number (e.g., `+306912345678`)

### 4. Make Test Call (2 minutes)

**Call the number and say:**

```
"Θέλω επιστροφή χρημάτων για την παραγγελία #99102"
```

**Expected flow:**
1. Greeting plays
2. Agent asks for reason
3. You say: "Ελαττωματικό"
4. Agent asks for photo
5. You say: "Έχω"
6. Agent creates ticket and confirms

### 5. Verify (1 minute)

- Check GitHub Issues → New ticket created
- Check Function App logs → See conversation flow
- Verify ticket has: order ID, reason, caller phone

## Test Scenarios (Copy-Paste Ready)

### Scenario 1: Simple Information
**Say:** "Ποιο είναι το ωράριο;"
**Expected:** Store hours response

### Scenario 2: Refund Request
**Say:** "Θέλω επιστροφή"
**Then:** "#99102"
**Then:** "Ελαττωματικό"
**Then:** "Επιστροφή χρημάτων"
**Expected:** Ticket #XXX created

### Scenario 3: Cancellation
**Say:** "Θέλω ακύρωση παραγγελίας #77881"
**Then:** "Άργησε"
**Expected:** Ticket or alternative offer

### Scenario 4: Bad Experience
**Say:** "Είχα πολύ άσχημη εμπειρία, ήταν αγενείς"
**Then:** "Ναι" (to human callback)
**Expected:** High-priority ticket, callback scheduled

### Scenario 5: Human Request
**Say:** "Θέλω να μιλήσω με άνθρωπο"
**Then:** "306912345678, πρωί"
**Expected:** Callback ticket created

## Monitoring During Call

**Open in browser:**
- Azure Portal → Function App → **Log stream**
- GitHub → Your Repo → **Issues** (refresh to see new tickets)

**Watch for:**
- `--- INCOMING CALL DETECTED ---`
- `User transcript: '...'`
- `Created GitHub ticket #...`
- `AI response: '...'`

## Common Issues & Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| No greeting | Check webhook endpoint URL |
| Speech not recognized | Verify `SPEECH_KEY` and `SPEECH_REGION` |
| Wrong responses | Check `AZURE_OPENAI_KEY` and deployment name |
| No ticket created | Verify `GITHUB_TOKEN` has `issues:write` permission |
| Call drops | Check ngrok (if local) or Function App timeout |

## Success Indicators

✅ Greeting plays automatically  
✅ Your speech is transcribed correctly  
✅ Agent asks relevant follow-up questions  
✅ Ticket created with correct information  
✅ Confirmation message includes ticket number  
✅ GitHub issue has all details  

---

**Total time to first test call: ~10 minutes**
