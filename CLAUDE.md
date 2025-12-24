# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An AI-powered Hinglish-speaking voice assistant for telecom customer support. The system handles customer queries about data balance, recharge plans, billing, and network issues through natural voice conversations in a mix of Hindi and English (Hinglish).

**Core Concept**: Replace complex IVR menus with conversational AI that speaks naturally to Indian telecom customers in their preferred language mix.

## Architecture

### Three-Layer System

1. **Database Layer (db.py)**
   - TiDB Cloud MySQL connection using SQLAlchemy
   - SSL/TLS encrypted connection with certificate validation
   - Connection pooling with pre-ping health checks
   - Database schema: `plans` → `users` → `transactions` (foreign key relationships)

2. **Data Ingestion (ingest.py)**
   - One-time database initialization script
   - Creates schema: plans, users, transactions tables
   - Seeds sample telecom data (5 users, 5 plans, 5 transactions)
   - Uses foreign key constraints to maintain referential integrity

3. **AI Agent (main.py)**
   - Voice I/O: Google Speech Recognition (English-IN) + gTTS (Text-to-Speech)
   - LLM: Google Gemini 1.5 Flash for response generation
   - Dual authentication: Voice greeting → CLI phone number input → Voice queries
   - Context-aware query processing with database lookups

### Key Design Patterns

**Phone Number Verification Flow**:
- Greets user with voice prompt
- Requires 10-digit phone number via CLI input (not voice for accuracy)
- Validates against database before allowing voice queries
- Stores verified phone in `self.current_phone` session state

**Query Processing Pipeline**:
1. Voice input → Google Speech Recognition (en-IN)
2. Keyword extraction from user query (balance, plan, recharge, etc.)
3. Database lookup using verified phone number
4. Combine DB results + hardcoded telecom data
5. Pass to Gemini with structured prompt for Hinglish response
6. Text-to-Speech output (gTTS with co.in accent)

**Data Sources**:
- **Dynamic (from DB)**: User balance, active plan, transaction history
- **Static (hardcoded dict)**: Recharge plan catalog, customer care numbers, support info, promotional offers

## Development Commands

### Initial Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment variables (.env required)
# GEMINI_API_KEY - Google AI API key
# TIDB_HOST, TIDB_PORT, TIDB_USER, TIDB_PASSWORD, TIDB_DB_NAME - TiDB Cloud credentials
# CA_PATH - Path to SSL certificate (isrgrootx1.pem)

# Test database connection
python db.py
# Expected output: "Connected to TiDB Cloud, server time: [timestamp]"

# Initialize database (run once)
python ingest.py
# Expected output: "Simple telecom database created!"
```

### Running the Application

#### Web Interface (Recommended):
```bash
streamlit run app.py
# Opens browser at http://localhost:8501
# Features: Voice recording, text input, conversation history, user dashboard
```

#### CLI Version:
```bash
python main.py
# Interaction flow:
# 1. Listen to voice greeting
# 2. Type 10-digit mobile number when prompted
# 3. Use voice commands for queries
# 4. Say "bye" or "goodbye" to exit
```

### Testing Accounts
Pre-seeded phone numbers in ingest.py:
- 9876543210 (Rajesh Kumar - Jio Basic)
- 9123456789 (Priya Sharma - Airtel Smart)
- 9988776655 (Amit Singh - Vi Power)
- 9555444333 (Sneha Gupta - BSNL Value)
- 9111222333 (Vikash Yadav - Jio Premium)

## Database Schema

```
plans
├── plan_id (PK)
├── plan_name
├── price (DECIMAL)
├── data_gb (DECIMAL)
└── validity_days

users
├── user_id (PK)
├── phone (UNIQUE)
├── name
├── plan_id (FK → plans)
└── balance_mb (remaining data in MB)

transactions
├── txn_id (PK)
├── user_id (FK → users)
├── amount
├── txn_date (TIMESTAMP)
└── status
```

## Important Implementation Details

### Voice Recognition Setup
- Uses `sr.Microphone()` with ambient noise adjustment
- 10-second timeout for user speech
- Language: `en-IN` (Indian English for better Hinglish recognition)
- Graceful handling of timeout/unknown audio errors

### TTS Configuration
- Creates temporary MP3 files (cleaned up after playback)
- Uses `tld='co.in'` for Indian accent
- Pygame mixer for audio playback with busy-wait loop
- Process-safe filenames using `os.getpid()`

### Gemini Prompt Engineering
The AI response generator uses structured prompts with:
- **Role**: Professional telecom customer service agent
- **Language**: Formal Hinglish with respectful terms (aap, ji, sir/madam)
- **Constraints**: Use ONLY provided data, 2-3 sentence responses
- **Tone**: Helpful and courteous, not casual

### Query Intent Detection
Uses keyword matching in `find_relevant_data()`:
- Balance queries: "balance", "data", "remaining", "kitna", "how much"
- Plan info: "plan", "current", "my plan", "active plan"
- Recharge: "recharge", "new plan", "budget", "cheap", "affordable"
- Support: "help", "problem", "customer care", "complaint"
- Network: "network", "slow", "not working", "connection"
- Offers: "offer", "discount", "deal", "cashback"

Budget extraction from user input (200/500/1000) for plan recommendations.

## Application Versions

### Web Interface (app.py) - Recommended for Production
- **Framework**: Streamlit for web UI
- **Voice Input**: Browser-based audio recording (`st.audio_input()`)
- **Voice Output**: Browser audio player (auto-play supported)
- **Authentication**: Web form with session state
- **Features**: Conversation history, user dashboard, dual input modes (voice/text)
- **Deployment**: Streamlit Cloud, Hugging Face Spaces, Railway, Render
- **Advantages**: No system microphone needed, works on any device with browser

### CLI Version (main.py) - Local Development
- **Framework**: Pure Python CLI
- **Voice Input**: System microphone via SpeechRecognition
- **Voice Output**: pygame mixer for speaker playback
- **Authentication**: Terminal phone input
- **Features**: Lightweight, fast, no browser needed
- **Deployment**: Local execution only
- **Advantages**: Direct hardware access, simpler architecture

## Dependencies

- **speechrecognition**: Voice input (Google Web Speech API)
- **gTTS**: Text-to-speech output
- **pygame**: Audio playback (CLI version only)
- **python-dotenv**: Environment variable management
- **google-generativeai**: Gemini LLM integration
- **sqlalchemy**: Database ORM with TiDB Cloud
- **pymysql**: MySQL driver for TiDB
- **streamlit**: Web framework (web version only)
- **pydub**: Audio processing utilities

## Security Notes

- SSL/TLS required for TiDB connection (`check_hostname: True`)
- API keys loaded from .env (never commit .env to git)
- Phone number validation (10-digit numeric check)
- Database connection uses pymysql with UTF-8 encoding
- No password storage or user authentication beyond phone verification

## Deployment

### Recommended Platform: Streamlit Cloud (Free)
1. Push code to GitHub
2. Deploy at https://share.streamlit.io
3. Add secrets in TOML format (see DEPLOYMENT.md)
4. App goes live at `https://yourapp.streamlit.app`

### NOT Compatible: Vercel
Vercel is Node.js/Next.js/static only - does NOT support Python voice apps with audio processing.

### Alternatives:
- **Hugging Face Spaces**: Free, select Streamlit SDK
- **Railway**: Free tier, auto-detects Python
- **Render**: Free tier, manual start command configuration

## Limitations & Edge Cases

### CLI Version (main.py):
- Phone verification is CLI-based (not voice) to avoid recognition errors
- Audio playback blocks execution (synchronous)
- Temporary MP3 files may persist if program crashes during playback
- No support for multiple concurrent users (single session)
- Requires system microphone and speakers

### Web Version (app.py):
- Requires browser microphone permissions
- Audio recording needs HTTPS in production (handled by cloud platforms)
- Session state cleared on browser refresh
- No persistent user sessions across devices

### Both Versions:
- Static recharge plan catalog (hardcoded, not from database)
- Budget extraction uses keyword matching (not advanced NLU)
- Voice transcription dependent on Google Speech API free tier (60 min/month)
- Gemini API free tier: 15 requests/minute limit
