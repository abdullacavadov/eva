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

### 4. Gmail Read / Management ✅

- Shared Google OAuth
- Gmail API adapter
- Email search
- Pagination
- Metadata extraction
- Plain-text body
- HTML → text
- Gmail folder/category queries
- Inbox, Primary, Sent, Drafts, Spam, Trash
- Promotions, Social, Updates, Purchases
- Starred, All Mail
- Structured Result Contract
- ResultStore / Context integration
- Result Resolver / Selection
- ToolExecutor
- Draft listing / retrieval
- Draft deletion
- Folder/category trash operations
- Confirmation boundary for destructive operations
- Confirmation snapshot preservation
- Permanent deletion scopes
- Spam / Trash handling
- Tests
- Real Gmail test

Safety rules:

- Destructive Gmail operations require explicit user confirmation.
- Confirmation uses the prepared message snapshot rather than silently re-running a potentially changed query.
- Permanent deletion is separated from reversible trash operations.

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
- Gmail Write ✅

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
```

---

# Next Work — Gmail Write

Gmail Read / Management artıq bağlanıb. Növbəti əsas iş Gmail Write inteqrasiyasıdır.

Scope:

- Draft hazırlamaq
- Recipient / subject / body validation
- Mövcud thread-ə reply hazırlamaq
- Yeni email hazırlamaq
- Structured draft nəticəsi
- Açıq confirmation boundary
- Confirmation-dan sonra send
- Error handling
- Unit/integration tests
- Real Gmail send testi

Qayda:

Draft → User confirmation → Send

Yeni çatda işə başlamaq üçün aşağıdakı prompt istifadə olunsun:

> EVA layihəsinə davam edirik.
>
> GitHub repository: https://github.com/abdullacavadov/eva
>
> VACİB:
> - GitHub `main` branch-i source of truth-dur.
> - Mövcud işlək kodu lazımsız refactor etmə.
> - Minimal diff prinsipinə əməl et.
> - Əvvəlcə repository-nin cari `main` vəziyyətini audit et.
> - Gmail Read / Management artıq tamamlanıb və dəyişdirilməməlidir, yalnız Gmail Write üçün tələb olunan boşluqlar araşdırılmalıdır.
> - Gmail Write üçün Draft → User confirmation → Send safety boundary məcburidir.
> - Structured Result Contract, ResultStore / Context, Result Resolver / Selection və ToolExecutor arxitekturasını mövcud pattern-lərə uyğun istifadə et.
> - Əvvəlcə mövcud email action/tool-ları və Google OAuth/Gmail adapterini audit et, sonra yalnız konkret fayllar və minimal dəyişiklik planı ver.
> - Hər dəyişiklikdən sonra bütün pytest suite-ni işə sal və regression nəticəsini yoxla.
> - Real Gmail send testini yalnız confirmation boundary və test suite keçdikdən sonra et.
>
> Başlanğıc tapşırığı: `main` branch-də Gmail Write üçün mövcud draft/create/send imkanlarını, tool definitions, actions, ToolExecutor inteqrasiyasını, Structured Result Contract istifadəsini və test coverage-i audit et. Sonra yalnız növbəti konkret işi müəyyənləşdir.
