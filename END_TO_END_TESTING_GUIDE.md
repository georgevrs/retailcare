# End-to-End Testing Guide: Real Phone Call Testing

This guide walks you through testing the RetailCare AI call center with actual phone calls.

## Prerequisites Checklist

Before making a real phone call, ensure you have:

- [ ] Azure Communication Services resource created
- [ ] Phone number acquired in ACS
- [ ] Azure AI Speech resource created (region: `westeurope` recommended)
- [ ] Azure OpenAI resource with `gpt-4o` deployed
- [ ] GitHub repository and Personal Access Token
- [ ] Azure Function App deployed (or ngrok for local testing)
- [ ] All environment variables configured

## Step 1: Deploy Function App

### Option A: Deploy to Azure (Recommended for Production Testing)

1. **Create Function App in Azure Portal:**
   ```bash
   az functionapp create \
     --resource-group <your-resource-group> \
     --consumption-plan-location westeurope \
     --runtime python \
     --runtime-version 3.11 \
     --functions-version 4 \
     --name <your-function-app-name> \
     --storage-account <your-storage-account>
   ```

2. **Deploy the code:**
   ```bash
   func azure functionapp publish <your-function-app-name>
   ```

3. **Configure Application Settings:**
   - Go to Azure Portal → Function App → Configuration → Application settings
   - Add all environment variables from your `.env` file:
     - `ACS_CONNECTION_STRING`
     - `ACS_CALLBACK_URL` (should be `https://<your-app>.azurewebsites.net/api/acs/callback`)
     - `SPEECH_KEY`
     - `SPEECH_REGION`
     - `AZURE_OPENAI_ENDPOINT`
     - `AZURE_OPENAI_KEY`
     - `AZURE_OPENAI_DEPLOYMENT`
     - `GITHUB_OWNER`
     - `GITHUB_REPO`
     - `GITHUB_TOKEN`

### Option B: Local Testing with ngrok (For Development)

1. **Start Function App locally:**
   ```bash
   func start
   ```
   The app should start on `http://localhost:7071`

2. **Start ngrok tunnel:**
   ```bash
   ngrok http 7071
   ```
   Copy the HTTPS URL (e.g., `https://abc123.ngrok-free.app`)

3. **Update `.env` file:**
   ```bash
   ACS_CALLBACK_URL=https://abc123.ngrok-free.app/api/acs/callback
   ```

## Step 2: Configure Azure Communication Services Webhook

1. **Go to Azure Portal:**
   - Navigate to your **Azure Communication Services** resource

2. **Set up Event Subscription:**
   - Click on **Events** in the left menu
   - Click **+ Event Subscription**

3. **Configure Event Subscription:**
   - **Name**: `CallCenterWebhook`
   - **Event Schema**: Event Grid Schema
   - **System Topic**: Create new (or use existing)
   - **Filter to Event Types**: Select:
     - `Microsoft.Communication.IncomingCall`
     - `Microsoft.Communication.CallConnected`
     - `Microsoft.Communication.RecognizeCompleted`
     - `Microsoft.Communication.CallDisconnected`
     - `Microsoft.Communication.PlayCompleted`
   
4. **Endpoint Configuration:**
   - **Endpoint Type**: Webhook
   - **Endpoint URL**: 
     - Azure: `https://<your-app>.azurewebsites.net/api/acs/events`
     - Local: `https://<your-ngrok-url>.ngrok-free.app/api/acs/events`
   
5. **Click Create**
   - Azure will send a validation request
   - Your function should automatically respond with the validation code
   - Check Function App logs to confirm validation succeeded

## Step 3: Verify Configuration

### Test Health Endpoint

```bash
# Azure
curl https://<your-app>.azurewebsites.net/api/health

# Local
curl http://localhost:7071/api/health
```

Expected: `Healthy`

### Test Simulation Endpoint (Verify Agent Works)

```bash
curl -X POST http://localhost:7071/api/dev/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Θέλω επιστροφή χρημάτων για την παραγγελία #99102",
    "session_id": "test-123"
  }'
```

Expected: JSON response with intent, slots, and agent response

## Step 4: Make a Real Phone Call

### Get Your Phone Number

1. Go to Azure Portal → ACS Resource → **Phone Numbers**
2. Copy the phone number (format: `+30...` or `+1...`)

### Call Flow

1. **Call the number** from any phone
2. **Wait for greeting**: You should hear (in Greek):
   > "Καλησπέρα σας! Είμαι η ψηφιακή εξυπηρέτηση του καταστήματος RetailCare. Πώς μπορώ να σας βοηθήσω;"

3. **Speak your request** in Greek. Examples:

   **Test Case 1: Store Hours**
   - Say: "Ποιο είναι το ωράριο του καταστήματος;"
   - Expected: Agent responds with store hours in natural Greek

   **Test Case 2: Refund Request**
   - Say: "Θέλω επιστροφή χρημάτων"
   - Agent asks: "Ποιος είναι ο αριθμός παραγγελίας;"
   - Say: "#99102"
   - Agent asks: "Ποιος είναι ο λόγος επιστροφής;"
   - Say: "Ελαττωματικό"
   - Expected: Agent creates ticket and confirms with ticket number

   **Test Case 3: Order Cancellation**
   - Say: "Θέλω ακύρωση παραγγελίας"
   - Agent asks: "Ποιος είναι ο αριθμός παραγγελίας;"
   - Say: "#77881"
   - Agent asks: "Γιατί θέλεις να ακυρώσεις;"
   - Say: "Άργησε"
   - Expected: Agent creates ticket or suggests alternatives

   **Test Case 4: Bad Experience**
   - Say: "Είχα πολύ άσχημη εμπειρία, ήταν αγενείς"
   - Expected: Agent detects high severity, offers human callback, creates high-priority ticket

   **Test Case 5: Human Request**
   - Say: "Θέλω να μιλήσω με άνθρωπο"
   - Agent asks: "Θες να σε καλέσουμε πίσω;"
   - Say: "Ναι, 306912345678, πρωί"
   - Expected: Agent creates callback ticket

## Step 5: Monitor the Call

### View Function App Logs

**Azure Portal:**
1. Go to Function App → **Log stream** (or **Monitor**)
2. Watch for:
   - `--- INCOMING CALL DETECTED ---`
   - `--- CALL CONNECTED ---`
   - `--- SPEECH RECOGNIZED ---`
   - `User transcript: '...'`
   - `AI response: '...'`
   - `Created GitHub ticket #...`

**Local (Terminal):**
- Watch the `func start` terminal output
- Look for the same log messages

### Check GitHub Issues

1. Go to your GitHub repository
2. Check **Issues** tab
3. You should see new issues created with:
   - Title: `[Call Center] Category - Summary`
   - Labels: category, urgency, channel:phone
   - Body with caller phone, order ID, description

## Step 6: Expected Behavior by Scenario

### Scenario: Information Request (Store Hours)

**What you say:**
- "Ποιο είναι το ωράριο;"

**What happens:**
1. STT converts speech to text
2. Agent classifies as `STORE_HOURS`
3. Agent calls `get_store_hours`
4. TTS converts response to speech
5. You hear: "Σήμερα (Δευτέρα) είμαστε ανοιχτά **09:00–21:00**..."

**Logs show:**
```
Intent: STORE_HOURS
Action: get_store_hours
Response: "Σήμερα..."
```

### Scenario: Refund Request (Multi-Turn)

**Turn 1:**
- You: "Θέλω επιστροφή"
- Agent: "Ποιος είναι ο αριθμός παραγγελίας;"
- Logs: `Intent: REFUND_REQUEST`, `Missing slots: ['order_id']`, `Next question: ...`

**Turn 2:**
- You: "#99102"
- Agent: "Ποιος είναι ο λόγος επιστροφής;"
- Logs: `Slots: {'order_id': '#99102'}`, `Missing slots: ['reason']`

**Turn 3:**
- You: "Ελαττωματικό"
- Agent: Policy check → "Για να προχωρήσουμε, χρειαζόμαστε: Φωτογραφία..."
- Logs: `Policy eligible: True`, `Required: ['photo']`

**Turn 4:**
- You: "Έχω φωτογραφία"
- Agent: "Κατέγραψα ότι η παραγγελία #99102 ζητά επιστροφή χρημάτων... Άνοιξα αίτημα με αριθμό #105..."
- Logs: `Created ticket #105`, `Confirmation summary: ...`

**GitHub Issue Created:**
- Title: `[Call Center] Refund - Επιστροφή για ελαττωματικό`
- Labels: `refund`, `urgency:medium`, `channel:phone`
- Body includes: caller phone, order ID, reason, policy requirements

### Scenario: Bad Experience (High Severity)

**What you say:**
- "Είχα πολύ άσχημη εμπειρία, ήταν αγενείς"

**What happens:**
1. Agent detects high severity keywords ("αγεν")
2. Sets `severity: "high"`, `needs_human: true`
3. Agent asks: "Θες να σε καλέσει άνθρωπος από την ομάδα μας;"
4. If you say "Ναι": Creates ticket with `priority:high` label

**GitHub Issue:**
- Labels include: `priority:high`
- Urgency: `high`
- Body mentions: "High severity - requires human intervention"

## Step 7: Troubleshooting

### Issue: No greeting plays / Call doesn't answer

**Check:**
1. EventGrid webhook configured correctly?
2. Function App logs show "INCOMING CALL DETECTED"?
3. `ACS_CALLBACK_URL` is correct?
4. Function App is running and accessible?

**Fix:**
- Verify webhook endpoint is reachable: `curl https://<your-url>/api/health`
- Check EventGrid subscription status in Azure Portal
- Review Function App logs for errors

### Issue: Speech not recognized

**Check:**
1. `SPEECH_KEY` and `SPEECH_REGION` configured?
2. Speech resource in correct region?
3. Speaking clearly in Greek?

**Fix:**
- Test Speech service separately
- Check logs for "RecognizeFailed" events
- Verify `STT_LOCALE` is `el-GR`

### Issue: Agent doesn't respond / Wrong responses

**Check:**
1. `AZURE_OPENAI_ENDPOINT` and `AZURE_OPENAI_KEY` correct?
2. Model `gpt-4o` deployed?
3. Function App logs show OpenAI API calls?

**Fix:**
- Test OpenAI connection: Check logs for "Initializing Azure OpenAI"
- Verify deployment name matches `AZURE_OPENAI_DEPLOYMENT`
- Check for rate limits or quota issues

### Issue: Tickets not created

**Check:**
1. `GITHUB_OWNER`, `GITHUB_REPO`, `GITHUB_TOKEN` correct?
2. Token has `issues:write` permission?
3. Function App logs show "Created GitHub ticket"?

**Fix:**
- Test GitHub API separately
- Verify token permissions
- Check repository name spelling

### Issue: Call disconnects immediately

**Check:**
1. ngrok tunnel still active? (if local)
2. Function App timeout settings
3. Network connectivity

**Fix:**
- Keep ngrok running during test
- Check Function App timeout (default 5 minutes)
- Verify no firewall blocking

## Step 8: Advanced Testing Scenarios

### Test Multi-Turn Conversation

1. Call and say: "Θέλω επιστροφή"
2. Wait for question, then say: "#99102"
3. Wait for next question, then say: "Ελαττωματικό"
4. Continue until ticket is created
5. Verify all turns are in conversation history

### Test Policy Enforcement

1. Call and say: "Θέλω επιστροφή για παραγγελία #99102, άλλαξα γνώμη, 20 ημέρες"
2. Expected: Agent explains 14-day limit, still creates ticket for review

### Test Escalation

1. Call and say: "Είχα πολύ άσχημη εμπειρία, αυτό είναι απάτη"
2. Expected: High priority ticket, no coupon offer, human handoff

### Test Store Hours with "Today"

1. Call and say: "Τι ώρες είστε ανοιχτά σήμερα;"
2. Expected: Response includes "Σήμερα (day name) είμαστε ανοιχτά..."

## Step 9: Verification Checklist

After each call, verify:

- [ ] Greeting played correctly
- [ ] Speech recognized (check logs for transcript)
- [ ] Intent classified correctly
- [ ] Slots extracted properly
- [ ] Agent responded appropriately
- [ ] Multi-turn conversation maintained context
- [ ] Ticket created (if applicable) with correct information
- [ ] Confirmation message played
- [ ] GitHub issue has all required fields
- [ ] Call ended gracefully

## Step 10: Log Analysis

### Key Log Messages to Look For

```
✅ Good Flow:
--- INCOMING CALL DETECTED ---
✅ Answer request sent. Connection ID: ...
--- CALL CONNECTED ---
🎤 STARTING MEDIA LOOP
--- SPEECH RECOGNIZED ---
User transcript: '...'
Intent: REFUND_REQUEST
Slots: {'order_id': '#99102'}
Created GitHub ticket #105
AI response: 'Κατέγραψα ότι...'
--- CALL DISCONNECTED ---

❌ Error Indicators:
❌ Failed to answer call
❌ Cannot start recognition: user_id is unknown
❌ Error in agent processing
❌ Failed to create GitHub ticket
```

## Quick Test Script

Save this as `test_phone_call.sh`:

```bash
#!/bin/bash

echo "📞 Testing RetailCare Phone System"
echo "=================================="
echo ""
echo "1. Verify Function App is running:"
curl -s https://<your-app>.azurewebsites.net/api/health
echo ""
echo ""
echo "2. Test simulation endpoint:"
curl -X POST https://<your-app>.azurewebsites.net/api/dev/simulate \
  -H "Content-Type: application/json" \
  -d '{"text": "Θέλω επιστροφή", "session_id": "test-phone-1"}' | jq .
echo ""
echo ""
echo "3. Check GitHub Issues:"
echo "   Go to: https://github.com/<owner>/<repo>/issues"
echo ""
echo "4. Make a phone call to: <your-phone-number>"
echo "   Say: 'Θέλω επιστροφή χρημάτων'"
echo ""
echo "5. Monitor logs in Azure Portal → Function App → Log stream"
```

## Expected Call Duration

- **Simple query (store hours)**: 30-60 seconds
- **Ticket creation (single turn)**: 1-2 minutes
- **Multi-turn conversation**: 2-5 minutes
- **Complex flow (refund with policy)**: 3-7 minutes

## Success Criteria

A successful test call should:

1. ✅ Answer automatically within 2-3 seconds
2. ✅ Play greeting in clear Greek
3. ✅ Recognize your speech accurately
4. ✅ Respond contextually and naturally
5. ✅ Ask follow-up questions when needed (one at a time)
6. ✅ Create tickets with complete information
7. ✅ Provide confirmation with ticket number
8. ✅ Handle errors gracefully
9. ✅ Maintain conversation context across turns
10. ✅ End call cleanly

## Next Steps After Testing

1. **Review GitHub Issues**: Verify all tickets have correct information
2. **Check Logs**: Identify any errors or edge cases
3. **Test Edge Cases**: Try unclear speech, interruptions, etc.
4. **Performance**: Measure response times
5. **User Experience**: Note any awkward pauses or unclear responses

---

## Quick Reference: Phone Number Format

When calling, use the full international format:
- **Greece**: `+30XXXXXXXXX`
- **US**: `+1XXXXXXXXXX`
- **UK**: `+44XXXXXXXXXX`

The number format depends on where you acquired the phone number in Azure Communication Services.

---

## Support

If you encounter issues:
1. Check Function App logs first
2. Verify all environment variables
3. Test each component separately (Speech, OpenAI, GitHub)
4. Review the troubleshooting section above

Good luck with your testing! 🎉
