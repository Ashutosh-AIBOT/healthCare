# XOMNI Full AI Agent Pipeline — Plan

## Overview
This plan defines the full end-to-end RAG pipeline for the Aarogya health platform, integrating multiple LLM providers (starting with NVIDIA NIM/Nemotron 3.5) with per-user API key management, fallback behaviors, and proper guardrails.

## 1. Provider API Key Management

### 1.1 `api_keys` Table (extension of existing)
- `id`, `user_id`, `provider` (nvidia|openai|gemini|groq|ollama), `api_key_hash`, `is_active`, `created_at`, `updated_at`
- Each user can have multiple provider keys active simultaneously
- Keys hashed at rest; never logged or exposed

### 1.2 Profile Settings UI
- Frontend: `/profile/api-keys` page (Tailwind + shadcn/ui)
- Lists all active providers per user
- "Add new provider" flow:
  1. User selects provider from dropdown (NVIDIA NIM, OpenAI, Gemini, Groq, Ollama)
  2. User enters API key (masked input)
  3. Frontend validates key by making a test call to provider's health endpoint
  4. On success: save hashed key, mark as active
  5. On failure: show error + direct link to provider's signup page
- "Remove" button to deactivate/revoke key

### 1.3 Fallback Behavior
- If no API key set for any provider → show UI prompt to add one
- If key invalid/expired → mark inactive, show "please re-add" link
- Default: use mock provider for demo/CI (existing behavior from PLAN.md § 18)

## 2. LLM Gateway Enhancement

### 2.1 `ai/llm/gateway.py` (create if not exists)
```python
from enum import Enum
class Provider(str, Enum):
    NVIDIA = "nvidia"
    OPENAI = "openai"
    GEMINI = "gemini"
    GROQ = "groq"
    OLLAMA = "ollama"
    MOCK = "mock"

class LLMGateway:
    def __init__(self, db_session, user_id: uuid.UUID):
        self.db = db_session
        self.user_id = user_id
        self._provider = None
    
    async def _get_active_provider(self) -> Provider:
        """Fetch active provider key from db, return Provider enum"""
        # Query api_keys table for user_id, is_active=true
        # Return Provider enum based on which key exists
        pass
    
    async def complete(self, prompt: str, **kwargs) -> dict:
        """Route to selected provider with fallback chain"""
        provider = await self._get_active_provider()
        
        # Fallback chain: nvidia → openai → gemini → groq → ollama → mock
        providers_chain = [Provider.NVIDIA, Provider.OPENAI, Provider.GEMINI, 
                          Provider.GROQ, Provider.OLLAMA, Provider.MOCK]
        
        last_error = None
        for p in providers_chain:
            try:
                result = await self._call_provider(p, prompt, **kwargs)
                # Record successful provider in analytics
                return result
            except Exception as e:
                last_error = e
                continue
        
        # All failed — return degraded response
        return {
            "text": "AI service temporarily unavailable. Please add a valid API key in your profile settings.",
            "provider": Provider.MOCK,
            "degraded": True
        }
    
    async def _call_provider(self, provider: Provider, prompt: str, **kwargs) -> dict:
        """Execute single provider call"""
        if provider == Provider.NVIDIA:
            return await self._call_nvidia(prompt, **kwargs)
        elif provider == Provider.OPENAI:
            return await self._call_openai(prompt, **kwargs)
        # ... etc
        elif provider == Provider.MOCK:
            return await self._call_mock(prompt, **kwargs)
    
    async def _call_nvidia(self, prompt: str, **kwargs) -> dict:
        """Call NVIDIA NIM API"""
        # NVIDIA NIM endpoint: POST https://ai.nvidia.com/v1/chat/completions
        # Model: nemotron-3.5-lightning or nvidia/nemotron-3.5-lightning-30b-a3b
        api_key = await self._get_key_hash(Provider.NVIDIA)
        headers = {"Authorization": f"Bearer {api_key}"}
        payload = {
            "model": "nvidia/nemotron-3.5-lightning-30b-a3b",
            "messages": [{"role": "user", "content": prompt}],
            **kwargs
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(
                "https://ai.nvidia.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            r.raise_for_status()
            return r.json()
```

### 2.2 Provider-Specific Models
- **NVIDIA NIM**: `nvidia/nemotron-3.5-lightning-30b-a3b` (confirmed correct name)
- **OpenAI**: `gpt-4o-mini`, `gpt-4o`
- **Google Gemini**: `gemini-1.5-flash`, `gemini-1.5-pro`
- **Groq**: `llama-3.1-8b-instant`, `mixtral-8x7b-32768`
- **Ollama**: local models (llama3, mixtral, etc.)

## 3. RAG Pipeline Enhancement

### 3.1 Existing Foundation (from `backend/app/ai/rag.py`)
- Keyword-overlap retrieval pre-filtered by `member_id`
- Cited answers with lab values and chunk citations
- Guardrail disclaimer appended

### 3.2 Enhanced RAG with Provider Routing
```python
async def retrieve_and_answer(
    db: AsyncSession,
    *,
    member_id: uuid.UUID,
    question: str,
    document_id: uuid.UUID | None = None,
) -> RagAnswer:
    """Enhanced RAG that uses the LLM gateway for generation"""
    
    # 1. Retrieve chunks (existing logic, pre-filtered by member_id)
    chunks = await retrieve_chunks(
        db, member_id=member_id, question=question
    )
    
    # 2. Extract relevant lab values
    lv_q = select(LabReportValue).where(LabReportValue.member_id == member_id)
    if document_id:
        lv_q = lv_q.where(LabReportValue.document_id == document_id)
    values = list((await db.execute(lv_q)).scalars().all())
    
    # 3. Build cited answer using LLM gateway instead of pure keyword matching
    # The LLM will generate the explanation from the retrieved context
    rag_answer = await build_cited_answer(db, member_id=member_id, question=question)
    
    # 4. Post-process: ensure disclaimer is present, redact PII
    # ... guardrail checks
    
    return rag_answer
```

### 3.3 Semantic Cache (existing `ai/llm/cache.py`)
- Cache keys include provider name + model, so different providers get separate caches
- Cost tracking per provider

## 4. Checkup Advisor Agent (LangGraph)

### 4.1 Enhanced with Provider Routing
The Checkup Advisor (LangGraph agent from PLAN.md § 7.4) should route LLM calls through the gateway.

```python
checkup_advisor_graph = StateGraph(state_schema=AdvisorState)

checkup_advisor_graph.add_edge("start", "analyze_profile")
checkup_advisor_graph.add_edge("analyze_profile", "generate_gaps")
checkup_advisor_graph.add_edge("generate_gaps", "llm_call")  # Uses gateway
checkup_advisor_graph.add_edge("llm_call", "guardrail_check")
checkup_advisor_graph.add_edge("guardrail_check", "map_to_lab")
checkup_advisor_graph.add_edge("map_to_lab", "package_recommendation")
checkup_advisor_graph.add_edge("package_recommendation", "end")
```

### 4.2 Guardrail Integration
- No diagnosis, no dosage, no prognosis
- Emergency detection with helpline numbers
- Disclaimer appended verbatim from `docs/copy-guide.md`

## 5. Frontend: Profile API Keys Page

### 5.1 Page Structure (`frontend/app/profile/api-keys/`)
- Tailwind-based card grid for each provider
- Add provider form with dropdown + input
- Real-time validation feedback

### 5.2 API Routes
- `GET /api/v1/profile/api-keys` — list user's active providers
- `POST /api/v1/profile/api-keys` — add new provider key
- `DELETE /api/v1/profile/api-keys/{provider_id}` — remove key

### 5.3 Error States
- "No API key configured → Add one to enable AI features"
- Link to provider signup pages (NVIDIA NIM: https://ai.nvidia.com/)

## 6. Cost & Quota Guardrails

### 6.1 Per-Plan Cost Ceilings (PLAN.md § 57)
- Free: 3 AI queries/day
- Plus: 50 AI queries/day  
- Family Pro: Unlimited (within reason)

### 6.2 Cost Model Tracking
- Every AI call records: tokens, cost, latency, provider, model
- Monthly budget guard with alerting
- Per-tenant ceilings enforced at gateway level

### 6.3 Degraded Mode
- When budget exceeded → switch to mock/cheaper provider
- User-visible: "AI running in reduced mode — some features disabled"
- Logged with cost, latency, prompt version, guardrail verdict

## 7. Walking Skeleton (M6 Exit Criterion)

### 7.1 End-to-End Flow
```
register → login → upload PDF lab report → 
worker ingests → OCR + extraction → chunks embedded → 
add NVIDIA API key in profile → 
ask question → RAG retrieval → NVIDIA/Nemotron answer → 
cited answer streams back → disclaimer shown
```

### 7.2 Success Criteria
- Docker compose boots green from clean state
- User can upload a lab report and get structured values
- User can ask questions about the report
- User can add NVIDIA NIM API key in profile
- Questions get answered using NVIDIA model (or fallback)
- All guardrails enforced (no diagnosis, disclaimer present)
- Cost tracked per tenant

## 8. Migration & Deployment

### 8.1 Environment Variables (`.env.example` update)
```
# LLM Provider Selection
LLM_PROVIDER=nvidia  # or openai|gemini|groq|ollama|mock

# NVIDIA NIM
NVIDIA_API_KEY=your_nvidia_nim_key_here

# Fallback chain (optional)
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
GROQ_API_KEY=...

# Cost guardrails
AI_COST_CEILING_PER_MONTH=10.00  # USD
```

### 8.2 Docker Compose
- No code changes needed; gateway reads from env
- Mock provider default keeps CI working without keys

### 8.3 CI/CD
- Nightly AI eval suite tests all providers
- Provider key rotation documented
- Secrets never committed (env vars only)

## 9. Testing Requirements

### 9.1 Unit Tests
- Gateway routing logic for each provider
- Key management CRUD operations
- Fallback chain behavior

### 9.2 Integration Tests
- Full RAG pipeline with NVIDIA key
- Fallback when no key set
- Cost tracking and ceiling enforcement

### 9.3 Guardrail Tests
- No diagnosis output
- Disclaimer present on all AI output
- Emergency detection works

### 9.4 Negative Tests
- Another tenant's data inaccessible (RLS)
- Invalid API key handled gracefully
- Degraded mode UI shown properly