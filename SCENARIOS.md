# RetailCare AI Call Center - Test Scenarios

This document outlines all scenarios that should work correctly in the RetailCare AI call center system.

## Table of Contents

1. [Basic Information Queries](#basic-information-queries)
2. [Store Hours Queries](#store-hours-queries)
3. [Order Cancellation Flow](#order-cancellation-flow)
4. [Order Change Flow](#order-change-flow)
5. [Refund Request Flow](#refund-request-flow)
6. [Bad Experience Flow](#bad-experience-flow)
7. [Human Request Flow](#human-request-flow)
8. [Complaint Ticket Flow](#complaint-ticket-flow)
9. [Multi-Turn Dialogue Scenarios](#multi-turn-dialogue-scenarios)
10. [Policy Check Scenarios](#policy-check-scenarios)
11. [Ticket Confirmation Scenarios](#ticket-confirmation-scenarios)
12. [Simulation Mode Scenarios](#simulation-mode-scenarios)
13. [Automation/Remediation Scenarios](#automationremediation-scenarios)

---

## Basic Information Queries

### Scenario 1.1: FAQ Search - Store Hours Question
**User:** "Ποιο είναι το ωράριο του καταστήματος;"

**Expected Behavior:**
- Intent: `INFORMATION` or `STORE_HOURS`
- Action: Search FAQ or get store hours
- Response: Contains store hours information in natural Greek

### Scenario 1.2: FAQ Search - Return Policy
**User:** "Ποια είναι η πολιτική επιστροφών;"

**Expected Behavior:**
- Intent: `INFORMATION`
- Action: Search FAQ
- Response: Returns FAQ answer about return policy

### Scenario 1.3: FAQ Search - Delivery Time
**User:** "Πόσος χρόνος χρειάζεται για την παράδοση;"

**Expected Behavior:**
- Intent: `INFORMATION`
- Action: Search FAQ
- Response: Returns delivery time information

### Scenario 1.4: FAQ Search - No Match
**User:** "Ποια είναι η φορολογική πολιτική σας;"

**Expected Behavior:**
- Intent: `INFORMATION`
- Action: Search FAQ (no match found)
- Response: "Λυπάμαι, δεν βρήκα συγκεκριμένη πληροφορία για αυτό. Θα το σημειώσω για να σας καλέσει ένας εκπρόσωπος."

---

## Store Hours Queries

### Scenario 2.1: General Store Hours Query
**User:** "Ποιο είναι το ωράριο του καταστήματος;"

**Expected Behavior:**
- Intent: `STORE_HOURS`
- Action: `get_store_hours`
- Response: Natural Greek text like "Σήμερα (Δευτέρα) είμαστε ανοιχτά **09:00–21:00**. Το ωράριο μας είναι: Δευτέρα–Παρασκευή **09:00-21:00**, Σάββατο **10:00-18:00**, Κυριακή **Κλειστά**."

### Scenario 2.2: Specific Day Query - Saturday
**User:** "Τι ώρες είστε ανοιχτά το Σάββατο;"

**Expected Behavior:**
- Intent: `STORE_HOURS`
- Action: `get_store_hours` (with day="saturday")
- Response: Contains "Σάββατο **10:00-18:00**"

### Scenario 2.3: Tomorrow Query
**User:** "Τι ώρες είστε ανοιχτά αύριο;"

**Expected Behavior:**
- Intent: `STORE_HOURS`
- Action: `get_store_hours` (with tomorrow's day)
- Response: Shows tomorrow's hours with day name

---

## Order Cancellation Flow

### Scenario 3.1: Simple Cancellation - Before Shipment
**Turn 1:**
- **User:** "Θέλω ακύρωση παραγγελίας"
- **Expected:** Intent `ORDER_CANCEL`, asks for order_id

**Turn 2:**
- **User:** "#77881"
- **Expected:** Asks for reason

**Turn 3:**
- **User:** "Άργησε"
- **Expected:** Creates ticket with cancellation request, shows confirmation summary

### Scenario 3.2: Cancellation - After Shipment (Alternative Offer)
**Turn 1:**
- **User:** "Θέλω να ακυρώσω την παραγγελία #77881"
- **Expected:** Intent `ORDER_CANCEL`, extracts order_id

**Turn 2:**
- **User:** "Άργησε"
- **Expected:** Checks policy, if shipped → suggests alternatives

**Turn 3:**
- **User:** "Κουπόνι"
- **Expected:** Creates ticket with alternative: store credit/coupon

### Scenario 3.3: Cancellation - Alternative Offers Offered
**User Input:** Order cancellation request with shipment status = "shipped"

**Expected Behavior:**
- Policy check determines not eligible for cancellation
- Agent asks: "Αν η παραγγελία έχει ήδη αποσταλεί, μπορώ να σου προτείνω εναλλακτικά: **αλλαγή σε άλλο προϊόν**, **πίστωση κουπονιού**, ή **επιστροφή μετά την παράδοση**. Ποιο προτιμάς;"
- User selects alternative → ticket created with alternative noted

---

## Order Change Flow

### Scenario 4.1: Address Change
**Turn 1:**
- **User:** "Θέλω να αλλάξω διεύθυνση στην παραγγελία μου"
- **Expected:** Intent `ORDER_CHANGE`, asks for order_id

**Turn 2:**
- **User:** "#12345"
- **Expected:** Asks what to change

**Turn 3:**
- **User:** "Διεύθυνση"
- **Expected:** Asks for new address

**Turn 4:**
- **User:** "Λεωφόρος Πατησίων 50, Αθήνα"
- **Expected:** Creates ticket with change request

### Scenario 4.2: Item Change
**Turn 1:**
- **User:** "Θέλω να αλλάξω προϊόν στην παραγγελία #12345"
- **Expected:** Intent `ORDER_CHANGE`, extracts order_id and change_type

**Turn 2:**
- **User:** "Αντί για το X θέλω το Y"
- **Expected:** Creates ticket with item change details

### Scenario 4.3: Quantity Change
**Turn 1:**
- **User:** "Μπορώ να αλλάξω την ποσότητα στην παραγγελία #12345;"
- **Expected:** Intent `ORDER_CHANGE`

**Turn 2:**
- **User:** "Ναι, θέλω 3 αντί για 2"
- **Expected:** Creates ticket with quantity change

---

## Refund Request Flow

### Scenario 5.1: Refund - Changed Mind (Eligible)
**Turn 1:**
- **User:** "Θέλω επιστροφή χρημάτων"
- **Expected:** Intent `REFUND_REQUEST`, asks for order_id

**Turn 2:**
- **User:** "#99102"
- **Expected:** Asks for reason

**Turn 3:**
- **User:** "Άλλαξα γνώμη"
- **Expected:** Policy check (14 days, unopened) → asks for days_since_delivery and condition

**Turn 4:**
- **User:** "5 ημέρες, ανοιχτό"
- **Expected:** Policy eligible → asks preferred resolution

**Turn 5:**
- **User:** "Επιστροφή χρημάτων"
- **Expected:** Creates ticket with refund request, shows confirmation

### Scenario 5.2: Refund - Damaged Product (Requires Photo)
**Turn 1:**
- **User:** "Το προϊόν που πήρα είναι ελαττωματικό, θέλω επιστροφή"
- **Expected:** Intent `REFUND_REQUEST`, extracts reason="damaged"

**Turn 2:**
- **User:** "#99102"
- **Expected:** Policy check → requires photo evidence

**Turn 3:**
- **User:** "Έχω φωτογραφία"
- **Expected:** Creates ticket with note about photo requirement

### Scenario 5.3: Refund - Not Eligible (Too Many Days)
**Turn 1:**
- **User:** "Θέλω επιστροφή για παραγγελία #99102, άλλαξα γνώμη"
- **Expected:** Intent `REFUND_REQUEST`

**Turn 2:**
- **User:** "20 ημέρες"
- **Expected:** Policy check → not eligible (14 day limit) → explains limitation, still creates ticket for review

### Scenario 5.4: Refund - Replacement Preferred
**Turn 1:**
- **User:** "Το προϊόν #99102 είναι ελαττωματικό"
- **Expected:** Intent `REFUND_REQUEST`

**Turn 2:**
- **User:** "Θα προτιμούσα αντικατάσταση"
- **Expected:** Creates ticket with preferred_resolution="replacement"

---

## Bad Experience Flow

### Scenario 6.1: Bad Experience - High Severity (Human Handoff)
**Turn 1:**
- **User:** "Είχα πολύ άσχημη εμπειρία, ήταν αγενείς"
- **Expected:** Intent `BAD_EXPERIENCE`, detects high severity keywords ("αγενής"), sets severity="high"

**Turn 2:**
- **User:** "Ναι" (to human callback offer)
- **Expected:** Creates ticket with `priority:high` label, offers human callback

### Scenario 6.2: Bad Experience - Medium Severity
**Turn 1:**
- **User:** "Δεν μου άρεσε η εξυπηρέτηση"
- **Expected:** Intent `BAD_EXPERIENCE`, severity="medium"

**Turn 2:**
- **User:** Provides more details
- **Expected:** Creates ticket with medium urgency, may offer coupon

### Scenario 6.3: Bad Experience - Legal/Fraud Claim (No Coupon)
**Turn 1:**
- **User:** "Αυτό είναι απάτη, θα καλέσω δικηγόρο"
- **Expected:** Intent `BAD_EXPERIENCE`, severity="high", offer_coupon=false

**Turn 2:**
- **User:** Provides details
- **Expected:** Creates high-priority ticket, offers human handoff only (no coupon)

---

## Human Request Flow

### Scenario 7.1: Human Request - With Callback
**Turn 1:**
- **User:** "Θέλω να μιλήσω με άνθρωπο"
- **Expected:** Intent `HUMAN_REQUEST`, asks for callback number

**Turn 2:**
- **User:** "306912345678, πρωί"
- **Expected:** Extracts callback_number and preferred_time, creates ticket for tracking, provides contact info

### Scenario 7.2: Human Request - Just Contact Info
**Turn 1:**
- **User:** "Θέλω άνθρωπο"
- **Expected:** Intent `HUMAN_REQUEST`

**Turn 2:**
- **User:** "Όχι, δεν θέλω callback"
- **Expected:** Provides store phone/email, offers to create ticket

### Scenario 7.3: Human Request - Direct Contact Info Request
**User:** "Πώς μπορώ να επικοινωνήσω με το φυσικό κατάστημα;"

**Expected Behavior:**
- Intent: `HUMAN_REQUEST` or `INFORMATION`
- Response: Provides phone, email, and location from store_info

---

## Complaint Ticket Flow

### Scenario 8.1: Simple Complaint
**Turn 1:**
- **User:** "Έχω πρόβλημα με την παραγγελία μου"
- **Expected:** Intent `COMPLAINT_TICKET`, asks for description

**Turn 2:**
- **User:** "Η παραγγελία #12345 έχει καθυστέρηση 5 ημέρες"
- **Expected:** Creates ticket with delivery category, shows confirmation

### Scenario 8.2: Complaint - With All Details
**User:** "Η παραγγελία #12345 για το προϊόν X έχει καθυστέρηση 5 ημέρες και θέλω ενημέρωση"

**Expected Behavior:**
- Intent: `COMPLAINT_TICKET`
- Extracts: order_id, product, description, urgency
- Creates ticket immediately (no questions needed)
- Shows detailed confirmation summary

---

## Multi-Turn Dialogue Scenarios

### Scenario 9.1: Slot Collection - Missing Multiple Fields
**Turn 1:**
- **User:** "Θέλω επιστροφή"
- **Expected:** Asks for order_id (one question at a time)

**Turn 2:**
- **User:** "#99102"
- **Expected:** Asks for reason

**Turn 3:**
- **User:** "Ελαττωματικό"
- **Expected:** Asks for days_since_delivery (policy requirement)

**Turn 4:**
- **User:** "3 ημέρες"
- **Expected:** Asks for preferred_resolution

**Turn 5:**
- **User:** "Επιστροφή χρημάτων"
- **Expected:** All slots collected → creates ticket

### Scenario 9.2: Context Preservation Across Turns
**Turn 1:**
- **User:** "Θέλω ακύρωση παραγγελίας #77881"
- **Expected:** Stores order_id in slots

**Turn 2:**
- **User:** "Άργησε"
- **Expected:** Remembers order_id from previous turn, adds reason

**Turn 3:**
- **User:** "Ναι, θέλω κουπόνι"
- **Expected:** Remembers all previous context, creates ticket

---

## Policy Check Scenarios

### Scenario 10.1: Refund Policy - Changed Mind (14 Days)
**Input:** reason="changed_mind", days_since_delivery=5, condition="unopened"

**Expected:**
- Policy: Eligible (within 14 days, unopened)
- Response: "Το αίτημά σας πληροί τις προϋποθέσεις. Θα προχωρήσουμε με την επιστροφή."

### Scenario 10.2: Refund Policy - Changed Mind (Too Late)
**Input:** reason="changed_mind", days_since_delivery=20, condition="unopened"

**Expected:**
- Policy: Not eligible (exceeds 14 days)
- Response: "Η επιστροφή πρέπει να γίνει εντός 14 ημερών από την παράδοση."
- Still creates ticket for manual review

### Scenario 10.3: Refund Policy - Damaged (Requires Photo)
**Input:** reason="damaged", days_since_delivery=2

**Expected:**
- Policy: Eligible but requires photo
- Response: "Για να προχωρήσουμε, χρειαζόμαστε: Φωτογραφία του προϊόντος."

### Scenario 10.4: Cancellation Policy - Before Shipment
**Input:** order_id="#77881", shipment_status="pending"

**Expected:**
- Policy: Eligible for cancellation
- Response: "Η ακύρωση μπορεί να γίνει. Θα προχωρήσουμε αμέσως."

### Scenario 10.5: Cancellation Policy - After Shipment
**Input:** order_id="#77881", shipment_status="shipped"

**Expected:**
- Policy: Not eligible for cancellation
- Response: "Η παραγγελία έχει ήδη αποσταλεί. Μπορείτε να την επιστρέψετε μετά την παράδοση."
- Offers alternatives: exchange, store credit, return after delivery

---

## Ticket Confirmation Scenarios

### Scenario 11.1: Detailed Confirmation - Cancellation
**After ticket creation for cancellation:**

**Expected Response:**
```
Κατέγραψα ότι η παραγγελία #77881 έχει αίτημα ακύρωσης (λόγος: Άργησε).
Άνοιξα αίτημα με αριθμό #104.
Θα λάβεις ενημέρωση μόλις το δει η ομάδα μας.
```

### Scenario 11.2: Confirmation with Missing Info
**After ticket creation with missing optional fields:**

**Expected Response:**
```
Κατέγραψα ότι η παραγγελία #12345 έχει καθυστέρηση και ζητάς ενημέρωση/επίσπευση.
Άνοιξα αίτημα με αριθμό RC-104.
Θα λάβεις ενημέρωση μόλις το δει η ομάδα μας.
Για να προχωρήσουμε πιο γρήγορα, μπορείς να μου πεις: το ονοματεπώνυμο στην παραγγελία;
```

### Scenario 11.3: Confirmation - Refund Request
**After ticket creation for refund:**

**Expected Response:**
```
Κατέγραψα ότι η παραγγελία #99102 ζητά επιστροφή χρημάτων (λόγος: Ελαττωματικό).
Άνοιξα αίτημα με αριθμό #105.
Θα λάβεις ενημέρωση μόλις το δει η ομάδα μας.
```

---

## Simulation Mode Scenarios

### Scenario 12.1: Simulation - Basic Request
**POST /api/dev/simulate**
```json
{
  "text": "Θέλω επιστροφή χρημάτων για την παραγγελία #99102",
  "session_id": "test-123",
  "mode": "live"
}
```

**Expected Response:**
```json
{
  "session_id": "test-123",
  "user_input": "Θέλω επιστροφή χρημάτων για την παραγγελία #99102",
  "agent_intent": "REFUND_REQUEST",
  "agent_response": "...",
  "slots": {
    "order_id": "#99102",
    "reason": "επιστροφή"
  },
  "next_question": "Ποιος είναι ο λόγος επιστροφής;",
  "flow_state": {
    "active_intent": "REFUND_REQUEST",
    "missing_slots": ["reason"],
    "last_action": "asked_question"
  }
}
```

### Scenario 12.2: Simulation - Dry Run Mode
**POST /api/dev/simulate**
```json
{
  "text": "Θέλω ακύρωση παραγγελίας #77881",
  "session_id": "test-456",
  "mode": "dry_run"
}
```

**Expected Response:**
- Includes `ticket_preview` with `would_create: true`
- Shows what ticket would be created without actually creating it
- Returns all slots and flow state

### Scenario 12.3: Simulation - Multi-Turn Session
**Turn 1:**
```json
{
  "text": "Θέλω επιστροφή",
  "session_id": "multi-turn-1"
}
```

**Turn 2 (same session_id):**
```json
{
  "text": "#99102",
  "session_id": "multi-turn-1"
}
```

**Expected:**
- Turn 2 remembers context from Turn 1
- Slots accumulate across turns
- Flow state persists

---

## Automation/Remediation Scenarios

### Scenario 13.1: Automation - Fill Table (Dry Run)
**GitHub Issue:**
- Labels: `automation:run`, `approved`, `playbook:fill_table`
- Body: "Table X is empty; please refill from Source Y."

**POST /api/automation/run**
```json
{
  "issue_number": 123,
  "issue_data": {
    "number": 123,
    "labels": ["automation:run", "approved", "playbook:fill_table"],
    "body": "Table X is empty; please refill from Source Y."
  },
  "dry_run": true
}
```

**Expected:**
- Status: `dry_run`
- Comment posted to issue: "🔍 **DRY RUN** - Would execute fill_table"
- No actual execution

### Scenario 13.2: Automation - Fill Table (Live Execution)
**GitHub Issue:**
- Labels: `automation:run`, `approved`, `playbook:fill_table`
- Body: "Table orders is empty; please refill from Source backup_db."

**POST /api/automation/run**
```json
{
  "issue_number": 124,
  "issue_data": {
    "number": 124,
    "labels": ["automation:run", "approved", "playbook:fill_table"],
    "body": "Table orders is empty; please refill from Source backup_db."
  },
  "dry_run": false
}
```

**Expected:**
- Status: `success`
- Executes fill_table playbook
- Comment posted: "✅ **EXECUTED** - Filled table orders with 12345 rows"
- Returns execution result

### Scenario 13.3: Automation - Missing Approval Label
**GitHub Issue:**
- Labels: `automation:run`, `playbook:fill_table` (missing `approved`)

**Expected:**
- Status: `skipped`
- Message: "Missing required labels: approved"
- No execution, no comment

### Scenario 13.4: Automation - Unknown Playbook
**GitHub Issue:**
- Labels: `automation:run`, `approved`, `playbook:unknown_action`

**Expected:**
- Status: `failed`
- Message: "Unknown playbook: unknown_action"
- No execution

### Scenario 13.5: Automation - Re-run Job
**GitHub Issue:**
- Labels: `automation:run`, `approved`, `playbook:rerun_job`
- Body: "Please re-run the daily_ingestion job with parameters: {start_date: '2026-01-01'}"

**Expected:**
- Extracts job_name="daily_ingestion"
- Extracts parameters from body
- Executes rerun_job playbook
- Posts comment with execution result

### Scenario 13.6: Automation - Sync FAQ
**GitHub Issue:**
- Labels: `automation:run`, `approved`, `playbook:sync_faq`
- Body: "Sync FAQ from url: https://example.com/faq.json"

**Expected:**
- Extracts source_url
- Executes sync_faq playbook
- Posts comment: "Synced 12 FAQ items from https://example.com/faq.json"

---

## Edge Cases and Error Scenarios

### Scenario 14.1: Empty Input
**User:** "" (empty string)

**Expected:**
- Intent: `UNKNOWN`
- Response: Asks user to repeat or provides helpful message

### Scenario 14.2: Unclear Intent
**User:** "Γεια σας, τι κάνετε;"

**Expected:**
- Intent: `GREETING` or `INFORMATION`
- Response: Friendly greeting and offer to help

### Scenario 14.3: Multiple Intents in One Message
**User:** "Θέλω ακύρωση και επίσης επιστροφή χρημάτων"

**Expected:**
- Classifies primary intent (likely ORDER_CANCEL)
- May ask for clarification or handle first intent, then ask about second

### Scenario 14.4: Ticket Creation Failure
**Scenario:** GitHub API returns error

**Expected:**
- Error message: "Υπήρξε ένα πρόβλημα κατά την καταχώρηση του αιτήματος. Παρακαλώ περιμένετε να σας συνδέσω με έναν εκπρόσωπο."
- Logs error for debugging
- Does not crash the conversation

### Scenario 14.5: Policy Check Failure
**Scenario:** Policy engine encounters invalid data

**Expected:**
- Falls back to creating ticket anyway
- Logs warning
- Continues conversation

---

## Integration Test Scenarios

### Scenario 15.1: Full Call Flow - Refund Request
1. Call comes in → ACS event received
2. Call answered → Greeting played
3. User speaks: "Θέλω επιστροφή"
4. STT converts to text
5. Agent processes → Asks for order_id
6. User: "#99102"
7. Agent processes → Asks for reason
8. User: "Ελαττωματικό"
9. Agent processes → Policy check → Asks for photo
10. User: "Έχω φωτογραφία"
11. Agent processes → Creates ticket
12. TTS converts confirmation to speech
13. Confirmation played to user
14. Call continues or ends

### Scenario 15.2: Session Persistence
**Multiple turns in same call:**
- Turn 1: User provides order_id
- Turn 2: User provides reason
- Turn 3: User provides additional info

**Expected:**
- All information preserved in session
- Flow state maintained
- Conversation history complete
- Ticket includes all collected information

---

## Golden Test Scenarios

These scenarios are stored in `tests/golden_conversations/` and should be used for regression testing:

1. **cancellation_flow.json** - Order cancellation with alternative offers
2. **refund_flow.json** - Refund request with policy checks
3. **bad_experience_flow.json** - Bad experience with escalation
4. **human_request_flow.json** - Human handoff with callback
5. **store_hours_flow.json** - Store hours queries

Each golden test contains:
- Multiple conversation turns
- Expected intent for each turn
- Expected action (ask_question, create_ticket, etc.)
- Expected slots collected
- Expected response content

---

## Success Criteria

For each scenario to be considered "working":

1. **Intent Classification:** Correct intent detected
2. **Slot Extraction:** Required slots extracted accurately
3. **Next Action:** Correct action taken (ask question, create ticket, etc.)
4. **Response Quality:** Response is in natural Greek, helpful, and contextually appropriate
5. **Ticket Creation:** When applicable, ticket created with correct information
6. **Confirmation:** User receives clear confirmation of what was registered
7. **Flow State:** Conversation state properly maintained across turns
8. **Error Handling:** Graceful handling of errors without crashing

---

## Notes

- All responses should be in **Greek (el-GR)**
- One question should be asked at a time (not overwhelming)
- Policy checks should be transparent to the user
- Ticket confirmations should be detailed and reassuring
- Automation requires both `automation:run` and `approved` labels for safety
- Dry-run mode is default for automation to prevent accidental execution
