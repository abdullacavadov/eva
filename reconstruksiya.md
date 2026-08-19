# EVA Development Roadmap

## Phase 1 — Core Assistant Integrations

### 1. Memory ✅

- Memory CRUD
- Fuzzy matching
- Ambiguous delete protection
- Prompt formatting
- Memory → system instruction
- ToolExecutor integration
- Regression tests

Status: tamamlandı.

---

### 2. Google Calendar ✅

- OAuth
- Calendar read
- Event creation
- Event deletion
- Real API integration
- Structured Result Contract
- ResultStore / Context integration
- Result Resolver / Selection
- ToolExecutor
- Tests
- Real-device/manual test

Status: tamamlandı.

---

### 3. Google Tasks / Reminders ✅

- Tasks OAuth scope
- Task list
- Task creation
- Reminder querying
- Pagination
- Filtering
- priority
- all_day
- Structured Result Contract
- ResultStore / Context integration
- Result Resolver / Selection
- ToolExecutor
- Tests
- Real API test

Status: tamamlandı.

---

### 4. Gmail Read ✅

- Shared Google OAuth
- gmail.readonly
- Gmail API adapter
- Email search
- Pagination
- Metadata extraction
- Plain-text body
- HTML → text
- Structured Result Contract
- ResultStore / Context integration
- Result Resolver / Selection
- ToolExecutor
- Tests
- Real Gmail test

Status: tamamlandı.

---

### 5. Gmail Write ⏳

- Email composition
- Recipient validation
- Subject/body preparation
- Reply to existing thread
- New email creation
- Structured draft result
- Explicit user confirmation
- Send
- Error handling
- Tests
- Real Gmail send test

Safety rule:

Draft → User confirmation → Send

EVA istifadəçinin açıq təsdiqi olmadan email göndərməməlidir.

Status: növbəti inteqrasiya.

---

### 6. WhatsApp ⏳

- Contact management
- Incoming message retrieval
- Message reading
- Message analysis
- Conversation context
- Reply preparation
- New message preparation
- Structured Result Contract
- ResultStore / Context integration
- Result Resolver / Selection
- ToolExecutor
- Safety / confirmation
- Message sending
- Error handling
- Tests
- Real-device test

Safety rule:

Draft → User confirmation → Send

EVA istifadəçinin açıq təsdiqi olmadan WhatsApp mesajı göndərməməlidir.

Status: Gmail Write-dan sonra növbəti əsas inteqrasiya.

---

### Phase 1 Completion Criteria

Phase 1 aşağıdakılar tamamlandıqda bağlanacaq:

- Memory ✅
- Google Calendar ✅
- Google Tasks / Reminders ✅
- Gmail Read ✅
- Gmail Write
- WhatsApp
- Regression test suite
- Final architecture/code audit

UI bu mərhələnin scope-unda deyil.

---

# Cross-cutting architectural rule — Data-first / Presentation-later

EVA istifadəçidən hər hansı məlumatı istədikdə məlumatı yalnız TTS üçün əldə etməməlidir.

Məlumat əvvəlcə strukturlaşdırılmış və gələcək UI təqdimatına hazır vəziyyətdə hazırlanmalıdır.

Əsas prinsip:

Data retrieval
    ↓
Structured result
    ↓
Context / ResultStore
    ↓
Presentation

Hazır structured nəticə:

- TTS tərəfindən səsləndirilə bilər
- gələcək UI tərəfindən göstərilə bilər
- follow-up command-lar üçün istifadə edilə bilər

Məsələn:

"X kontaktını mənə göstər"
    ↓
Contact məlumatını əldə et
    ↓
Structured contact result
    ↓
ResultStore
    ├─ Voice → məlumatı səsləndir
    └─ Future UI → kontaktı futuristic modalda göstər

və:

"20 avqustdakı eventləri göstər"
    ↓
Calendar eventləri əldə et
    ↓
Structured event list
    ↓
ResultStore
    ↓
"Dentist-i aç"
    ↓
Əvvəlki nəticədən konkret event seç
    ↓
Selected result
    ├─ Voice
    └─ Future UI

Lazımsız ikinci API çağırışı yalnız tələb olunan məlumat əvvəlki structured nəticədə mövcud deyilsə edilməlidir.

### Unified Structured Result Contract

```json
{
  "type": "calendar_event | contact | email | task",
  "status": "success | empty | partial | error",
  "query": {},
  "data": [],
  "count": 0,
  "selected": null,
  "meta": {}
}