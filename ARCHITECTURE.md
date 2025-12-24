# Architecture Overview

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
├─────────────────────────┬───────────────────────────────────────┤
│   CLI Version (main.py) │   Web Version (app.py)                │
│                         │                                       │
│   • System Microphone   │   • Browser Audio Recording           │
│   • pygame Speaker      │   • HTML5 Audio Player                │
│   • Terminal I/O        │   • Streamlit Components              │
│   • Local Only          │   • Session State Management          │
└─────────────────────────┴───────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CORE PROCESSING LAYER                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│   │ Voice Input  │───▶│  Query       │───▶│   Gemini     │   │
│   │ (Google STT) │    │  Processing  │    │   LLM        │   │
│   │  en-IN       │    │  + Context   │    │  Response    │   │
│   └──────────────┘    └──────────────┘    └──────────────┘   │
│                              │                     │           │
│                              ▼                     ▼           │
│                       ┌──────────────┐    ┌──────────────┐   │
│                       │  Database    │    │  TTS Output  │   │
│                       │  Queries     │    │  (gTTS)      │   │
│                       │  (SQLAlchemy)│    │  co.in       │   │
│                       └──────────────┘    └──────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       DATA LAYER                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌────────────────────┐        ┌────────────────────┐        │
│   │  TiDB Cloud        │        │  Static Data       │        │
│   │  (MySQL)           │        │  (Python Dict)     │        │
│   ├────────────────────┤        ├────────────────────┤        │
│   │ • users            │        │ • Recharge plans   │        │
│   │ • plans            │        │ • Customer care    │        │
│   │ • transactions     │        │ • Support info     │        │
│   │                    │        │ • Offers           │        │
│   └────────────────────┘        └────────────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Data Flow

### 1. User Authentication
```
User Input (10-digit phone)
    ↓
Database Query (users table)
    ↓
Session State Storage (current_phone)
    ↓
User Dashboard Display
```

### 2. Voice Query Processing (Web Version)
```
Browser Audio Recording
    ↓
Upload to Server (temp file)
    ↓
Google Speech Recognition (en-IN)
    ↓
Transcribed Text
    ↓
Query Intent Detection (keyword matching)
    ↓
Database Lookup (user_info, plans, transactions)
    ↓
Context Assembly (DB + Static Data)
    ↓
Gemini API (prompt + context)
    ↓
Hinglish Response Generation
    ↓
gTTS Audio Synthesis
    ↓
Browser Audio Playback
```

### 3. Text Query Processing
```
User Text Input
    ↓
Query Intent Detection
    ↓
[Same as steps 5-8 above]
```

## Component Breakdown

### Voice Recognition
- **Input Format**: WAV audio (browser) or raw microphone (CLI)
- **Recognition Engine**: Google Cloud Speech-to-Text (free tier)
- **Language**: `en-IN` (Indian English, handles Hinglish)
- **Timeout**: 10 seconds per query
- **Error Handling**: Fallback to text input on failure

### LLM Integration
- **Model**: Gemini 1.5 Flash (fast, cost-effective)
- **Prompt Structure**:
  ```
  Role: Professional telecom agent
  Language: Formal Hinglish
  Context: User query + Relevant data
  Constraints: 2-3 sentences, data-grounded
  ```
- **Rate Limit**: 15 RPM (free tier)
- **Fallback**: Pre-defined error messages

### Database Schema
```sql
plans (plan_id, plan_name, price, data_gb, validity_days)
   ↓ FK
users (user_id, phone, name, plan_id, balance_mb)
   ↓ FK
transactions (txn_id, user_id, amount, txn_date, status)
```

### Session Management (Web Only)
```python
st.session_state = {
    'authenticated': bool,
    'phone': str,
    'user_name': str,
    'conversation_history': [
        {query, response, timestamp}
    ]
}
```

## Security Architecture

### Authentication
```
Phone Number Input
    ↓
Database Verification (users.phone)
    ↓
Session Token (Streamlit session_state)
    ↓
Access Granted
```

### Data Protection
- **Environment Variables**: `.env` for secrets (gitignored)
- **SSL/TLS**: Required for TiDB connection
- **Certificate Validation**: `check_hostname: True`
- **No Password Storage**: Phone-only verification
- **API Keys**: Never hardcoded, loaded from environment

### Cloud Deployment Secrets
```
Streamlit Cloud: Secrets management (TOML format)
Hugging Face: Repository secrets
Railway/Render: Environment variables UI
```

## Performance Optimization

### Database
- **Connection Pooling**: SQLAlchemy with `pool_pre_ping=True`
- **Query Optimization**: Indexed lookups on `phone` (UNIQUE key)
- **Join Efficiency**: Foreign key constraints for fast joins

### Caching (Future Enhancement)
- Cache user data for session duration
- Cache static telecom data globally
- Implement Redis for multi-user deployments

### Audio Processing
- **TTS Generation**: On-demand per response
- **Temporary Files**: Auto-cleanup after playback
- **Streaming**: Not implemented (sync playback only)

## Scaling Considerations

### Current Architecture (Single User)
- **Concurrent Users**: 1 (CLI) or Session-based (Web)
- **State Management**: In-memory session state
- **Database Connections**: Per-request, pooled

### Production Scaling (Future)
- **Concurrent Users**: Requires database connection pool tuning
- **State Management**: Redis for session persistence
- **Audio Processing**: Queue system for async TTS
- **CDN**: Serve static assets separately
- **Load Balancing**: Multiple Streamlit instances

## Technology Choices Rationale

| Choice | Reason |
|--------|--------|
| **Streamlit** | Pure Python, no JS needed, built-in audio widgets |
| **TiDB Cloud** | MySQL-compatible, free 5GB, serverless scaling |
| **Gemini Flash** | Fast (low latency), free tier, good Hinglish support |
| **gTTS** | Free, no API key, Indian accent (`tld='co.in'`) |
| **Google STT** | Free 60 min/month, good Hinglish recognition |
| **SQLAlchemy** | ORM abstraction, easy TiDB migration |

## Deployment Architecture

### Streamlit Cloud
```
GitHub Repo (main branch)
    ↓ Auto-deploy on push
Streamlit Cloud Server
    ↓ HTTPS auto-provisioned
https://yourapp.streamlit.app
```

### Environment Variables Flow
```
Local: .env file
    ↓ (gitignored)
Cloud: Platform secrets management
    ↓ Injected at runtime
Application: os.getenv()
```

## Monitoring & Observability (Future)

### Metrics to Track
- Voice recognition accuracy
- Average response time
- Database query performance
- Gemini API usage/costs
- User session duration
- Most common queries

### Error Tracking
- Audio transcription failures
- Database connection issues
- API rate limit hits
- Browser compatibility issues

### Logging
- User queries (anonymized)
- Response generation time
- Database query execution time
- API call latency
