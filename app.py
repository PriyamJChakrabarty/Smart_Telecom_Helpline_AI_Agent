"""
Streamlit Frontend for Telecom AI Voice Assistant
Provides web-based interface with audio recording and playback
"""

import streamlit as st
import speech_recognition as sr
from gtts import gTTS
import google.generativeai as genai
from dotenv import load_dotenv
import os
from sqlalchemy import text
from db import engine
import tempfile
import time
from io import BytesIO
import traceback
from datetime import datetime

load_dotenv()

# Configure Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")  # Default to 2.0-flash if not set

if not GEMINI_API_KEY:
    st.error("⚠️ GEMINI_API_KEY not found in environment variables!")
    st.stop()

try:
    genai.configure(api_key=GEMINI_API_KEY)
    print(f"[INFO] Configured Gemini model: {GEMINI_MODEL}")
except Exception as e:
    st.error(f"⚠️ Failed to configure Gemini API: {e}")
    st.stop()

# Page config
st.set_page_config(
    page_title="Smart Telecom Helpline",
    page_icon="📞",
    layout="centered",
    initial_sidebar_state="auto"
)

# Console startup message
print("\n" + "="*60)
print("📞 SMART TELECOM HELPLINE - STREAMLIT APP")
print("="*60)
print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Application started")
print(f"Gemini API: {'✓ Configured' if GEMINI_API_KEY else '✗ Missing'}")
print(f"Gemini Model: {GEMINI_MODEL}")
print(f"Database: {'✓ Connected' if engine else '✗ Not connected'}")
print("="*60 + "\n")

# Custom CSS
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #1f77b4;
        padding: 1rem 0;
        margin-bottom: 2rem;
    }
    .stButton>button {
        width: 100%;
        background-color: #1f77b4;
        color: white;
        font-weight: bold;
        border-radius: 8px;
        padding: 0.75rem;
    }
    .user-info-box {
        background-color: #f0f7ff;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
        margin: 1rem 0;
    }
    .response-box {
        background-color: #f9f9f9;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
        border-left: 4px solid #28a745;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
if 'phone' not in st.session_state:
    st.session_state.phone = None
if 'user_name' not in st.session_state:
    st.session_state.user_name = None
if 'conversation_history' not in st.session_state:
    st.session_state.conversation_history = []
if 'error_logs' not in st.session_state:
    st.session_state.error_logs = []
if 'api_call_count' not in st.session_state:
    st.session_state.api_call_count = 0
if 'session_start_time' not in st.session_state:
    st.session_state.session_start_time = datetime.now()

# Helper function to log errors
def log_error(error_type, error_message, details=None):
    """Log errors to session state and console"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    error_entry = {
        "timestamp": timestamp,
        "type": error_type,
        "message": error_message,
        "details": details
    }
    st.session_state.error_logs.append(error_entry)

    # Console logging
    print(f"\n{'='*60}")
    print(f"[{timestamp}] ERROR: {error_type}")
    print(f"Message: {error_message}")
    if details:
        print(f"Details: {details}")
    print(f"{'='*60}\n")

    return error_entry

# Telecom data (same as main.py)
TELECOM_DATA = {
    "recharge_plans": {
        "prepaid": {
            "budget_plans": [
                {"name": "Smart 199", "price": 199, "data": "2GB/day", "validity": "28 days", "calls": "Unlimited"},
                {"name": "Value 299", "price": 299, "data": "1.5GB/day", "validity": "28 days", "calls": "Unlimited"},
                {"name": "Popular 349", "price": 349, "data": "2.5GB/day", "validity": "28 days", "calls": "Unlimited"}
            ],
            "premium_plans": [
                {"name": "Max 599", "price": 599, "data": "2GB/day", "validity": "84 days", "calls": "Unlimited"},
                {"name": "Super 999", "price": 999, "data": "3GB/day", "validity": "84 days", "calls": "Unlimited"}
            ]
        }
    },
    "services": {
        "customer_care": "199 (toll-free)",
        "balance_check": "*123#",
        "data_check": "*121#",
        "plan_info": "*333#",
        "website": "www.telecom.com",
        "app": "MyTelecom App"
    },
    "support_info": {
        "network_issues": "Restart phone, check network settings, or visit service center",
        "recharge_failed": "Check payment method, sufficient balance, or try again after 30 minutes",
        "data_not_working": "Check APN settings, restart phone, or contact 199",
        "bill_queries": "Login to app or website, or call 199 for bill details"
    },
    "offers": {
        "weekend_offer": "Double data on weekends with select plans",
        "student_discount": "20% off on annual plans with valid student ID",
        "family_pack": "Additional connections at 50% discount"
    }
}

# Database functions
def get_user_info(phone):
    """Get user data from database"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT u.name, u.balance_mb, p.plan_name, p.price, p.data_gb, p.validity_days
                FROM users u
                JOIN plans p ON u.plan_id = p.plan_id
                WHERE u.phone = :phone
            """), {'phone': phone})
            return result.fetchone()
    except Exception as e:
        error_msg = str(e)
        log_error("DATABASE_ERROR", "Failed to fetch user info", error_msg)
        st.error(f"❌ Database error: {error_msg}")

        # Show detailed error in expander
        with st.expander("🔍 Error Details"):
            st.code(traceback.format_exc())
        return None

def get_plans_by_budget(max_price):
    """Get plans within budget"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT plan_name, price, data_gb, validity_days
                FROM plans
                WHERE price <= :max_price
                ORDER BY price
            """), {'max_price': max_price})
            return result.fetchall()
    except Exception as e:
        error_msg = str(e)
        log_error("DATABASE_ERROR", "Failed to fetch plans", error_msg)
        st.warning(f"⚠️ Could not fetch plans from database: {error_msg}")
        return []

def get_last_recharge(phone):
    """Get recent transaction"""
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT t.amount, t.txn_date, t.status
                FROM transactions t
                JOIN users u ON t.user_id = u.user_id
                WHERE u.phone = :phone
                ORDER BY t.txn_date DESC
                LIMIT 1
            """), {'phone': phone})
            return result.fetchone()
    except Exception as e:
        error_msg = str(e)
        log_error("DATABASE_ERROR", "Failed to fetch transaction history", error_msg)
        st.warning(f"⚠️ Could not fetch transaction history: {error_msg}")
        return None

def find_relevant_data(user_input, phone):
    """Extract relevant telecom data based on user query"""
    relevant_info = ""

    user_data = get_user_info(phone)
    if not user_data:
        return "User data not available from database. Please contact customer care 199."

    name, balance_mb, plan_name, price, data_gb, validity_days = user_data
    balance_gb = balance_mb / 1024 if balance_mb else 0

    user_input_lower = user_input.lower()

    if any(word in user_input_lower for word in ["balance", "data", "remaining", "left", "kitna", "how much"]):
        relevant_info += f"Dear {name}, your current data balance is {balance_gb:.1f} GB remaining. "

    if any(word in user_input_lower for word in ["plan", "current", "my plan", "active plan", "subscription"]):
        relevant_info += f"Your active plan: {plan_name} at Rs.{price} with {data_gb}GB data for {validity_days} days validity. "

    if any(word in user_input_lower for word in ["recharge", "new plan", "plan change", "under", "budget", "cheap", "affordable"]):
        budget = 300
        if "200" in user_input_lower or "two hundred" in user_input_lower:
            budget = 200
        elif "500" in user_input_lower or "five hundred" in user_input_lower:
            budget = 500
        elif "1000" in user_input_lower or "thousand" in user_input_lower:
            budget = 1000

        plans = get_plans_by_budget(budget)
        if plans:
            relevant_info += f"Available plans under Rs.{budget}: "
            for i, plan in enumerate(plans[:3]):
                relevant_info += f"{plan[0]} Rs.{plan[1]} with {plan[2]}GB for {plan[3]} days"
                if i < len(plans[:3]) - 1:
                    relevant_info += ", "
            relevant_info += ". "

        if budget <= 400:
            budget_plans = TELECOM_DATA["recharge_plans"]["prepaid"]["budget_plans"]
            relevant_info += f"Popular options: "
            for plan in budget_plans:
                if plan["price"] <= budget:
                    relevant_info += f"{plan['name']} Rs.{plan['price']} with {plan['data']} for {plan['validity']}, "

    if any(word in user_input_lower for word in ["last recharge", "history", "payment", "transaction", "when recharged"]):
        txn = get_last_recharge(phone)
        if txn:
            date_str = txn[1].strftime('%d %B %Y') if txn[1] else "N/A"
            relevant_info += f"Your last recharge: Rs.{txn[0]} on {date_str}. Status: {txn[2]}. "

    if any(word in user_input_lower for word in ["help", "problem", "support", "customer care", "complaint", "issue"]):
        services = TELECOM_DATA["services"]
        relevant_info += f"Customer support available at {services['customer_care']}. Check balance: {services['balance_check']}, data: {services['data_check']}. "

    if any(word in user_input_lower for word in ["network", "slow", "not working", "connection", "internet"]):
        support = TELECOM_DATA["support_info"]
        relevant_info += f"For network issues: {support['network_issues']}. Data not working: {support['data_not_working']}. "

    if any(word in user_input_lower for word in ["offer", "discount", "deal", "cashback", "free"]):
        offers = TELECOM_DATA["offers"]
        relevant_info += f"Current offers: {offers['weekend_offer']}. {offers['student_discount']}. {offers['family_pack']}. "

    if any(word in user_input_lower for word in ["bill", "payment due", "amount", "pay"]):
        relevant_info += f"For bill queries: {TELECOM_DATA['support_info']['bill_queries']}. Use {TELECOM_DATA['services']['app']} or website {TELECOM_DATA['services']['website']}. "

    return relevant_info

def get_ai_response(user_input, phone):
    """Generate AI response using Gemini"""
    relevant_data = find_relevant_data(user_input, phone)

    if relevant_data and "not found" not in relevant_data.lower() and "not available" not in relevant_data.lower():
        prompt = f"""You are a professional telecom customer service agent speaking in formal yet friendly Hinglish.

        TONE GUIDELINES:
        - Use formal, respectful language appropriate for customer service
        - Mix Hindi and English naturally but maintain professionalism
        - Avoid casual expressions, use respectful terms like "aap", "ji", "sir/madam"
        - Keep responses concise (2-3 sentences) but informative
        - Sound helpful and courteous, like a professional telecom agent

        Customer query: {user_input}
        Relevant telecom data: {relevant_data}

        Answer the query using ONLY the provided data. Be helpful, formal yet friendly."""
    else:
        return relevant_data if relevant_data else "Maaf kijiye sir/madam, abhi technical issues aa rahe hain. Customer care 199 par call kariye."

    try:
        st.session_state.api_call_count += 1
        print(f"[INFO] Gemini API Call #{st.session_state.api_call_count} using model: {GEMINI_MODEL}")

        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)

        print(f"[INFO] Gemini API Response received successfully")
        return response.text

    except Exception as e:
        error_msg = str(e)
        error_details = traceback.format_exc()

        # Check for specific error types
        if "429" in error_msg or "quota" in error_msg.lower() or "rate" in error_msg.lower():
            log_error("API_RATE_LIMIT", "Gemini API rate limit exceeded", error_msg)
            st.error("🚫 **API Rate Limit Exceeded!**")
            st.warning(f"""
            **Gemini API Free Tier Limits:**
            - 15 requests per minute
            - 1500 requests per day

            **Your Session Stats:**
            - API Calls Made: {st.session_state.api_call_count}
            - Session Duration: {(datetime.now() - st.session_state.session_start_time).seconds // 60} minutes

            **Solutions:**
            1. Wait 1 minute and try again
            2. Upgrade to paid Gemini API plan
            3. Check quota: https://makersuite.google.com
            """)
            return "Maaf kijiye sir/madam, abhi bahut zyada requests aa rahi hain. Kripaya 1 minute baad try kariye ya customer care 199 par call kariye."

        elif "401" in error_msg or "403" in error_msg or "api key" in error_msg.lower():
            log_error("API_AUTH_ERROR", "Gemini API authentication failed", error_msg)
            st.error("🔑 **API Authentication Error!**")
            st.warning(f"""
            **Issue:** Invalid or missing Gemini API key

            **Solutions:**
            1. Check `.env` file has `GEMINI_API_KEY=your_key`
            2. Get new API key: https://makersuite.google.com/app/apikey
            3. Restart the application after updating `.env`

            **Error:** {error_msg}
            """)
            return "Technical error: Invalid API configuration. Please contact support."

        elif "timeout" in error_msg.lower() or "connection" in error_msg.lower():
            log_error("API_NETWORK_ERROR", "Network timeout connecting to Gemini API", error_msg)
            st.error("🌐 **Network Error!**")
            st.warning(f"""
            **Issue:** Could not connect to Gemini API

            **Solutions:**
            1. Check your internet connection
            2. Try again in a few seconds
            3. Check if Google AI services are down

            **Error:** {error_msg}
            """)
            return "Network error. Kripaya apna internet connection check kariye aur phir try kariye."

        else:
            log_error("API_UNKNOWN_ERROR", "Gemini API unknown error", error_msg)
            st.error(f"❌ **AI Error:** {error_msg}")

            with st.expander("🔍 Technical Details"):
                st.code(error_details)

            return "Maaf kijiye, kuch technical problem hai. Customer care 199 par call kariye immediate help ke liye."

def text_to_speech(text):
    """Convert text to speech and return audio bytes"""
    try:
        print("[INFO] Generating TTS audio...")
        tts = gTTS(text=text, lang='en', tld='co.in', slow=False)
        audio_bytes = BytesIO()
        tts.write_to_fp(audio_bytes)
        audio_bytes.seek(0)
        print("[INFO] TTS audio generated successfully")
        return audio_bytes.getvalue()
    except Exception as e:
        error_msg = str(e)
        log_error("TTS_ERROR", "Text-to-speech conversion failed", error_msg)
        st.warning(f"⚠️ Could not generate voice response: {error_msg}")

        if "timeout" in error_msg.lower() or "connection" in error_msg.lower():
            st.info("💡 Network issue with TTS service. Text response is still available above.")

        return None

def transcribe_audio(audio_file):
    """Transcribe audio file to text using Google Speech Recognition"""
    recognizer = sr.Recognizer()
    tmp_path = None
    try:
        print("[INFO] Starting audio transcription...")
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            tmp_file.write(audio_file.getvalue())
            tmp_path = tmp_file.name

        # Transcribe
        with sr.AudioFile(tmp_path) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="en-IN")

        # Cleanup
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)

        print(f"[INFO] Transcription successful: {text}")
        return text

    except sr.UnknownValueError:
        log_error("SPEECH_RECOGNITION_ERROR", "Could not understand audio", "Audio was unclear or silent")
        st.warning("⚠️ Could not understand audio. Please try again with clearer speech or use text input.")
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return None

    except sr.RequestError as e:
        error_msg = str(e)
        log_error("SPEECH_API_ERROR", "Google Speech Recognition API error", error_msg)
        st.error(f"🌐 Speech Recognition API Error: {error_msg}")
        st.info("""
        **Possible Issues:**
        1. No internet connection
        2. Google Speech API quota exceeded (60 min/month free)
        3. Service temporarily unavailable

        **Solution:** Use text input instead
        """)
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return None

    except Exception as e:
        error_msg = str(e)
        log_error("TRANSCRIPTION_ERROR", "Audio transcription failed", error_msg)
        st.error(f"❌ Transcription error: {error_msg}")

        with st.expander("🔍 Error Details"):
            st.code(traceback.format_exc())

        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return None

# Sidebar - System Monitoring
with st.sidebar:
    st.markdown("### 🔧 System Monitor")

    # Connection status
    st.markdown("#### 🔌 Service Status")
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        st.success("✅ Database: Connected")
    except Exception as e:
        st.error("❌ Database: Disconnected")
        st.caption(f"Error: {str(e)[:50]}...")

    st.success(f"✅ Gemini API: Configured")
    st.caption(f"Model: {GEMINI_MODEL}")
    st.info(f"✅ Speech API: Ready")
    st.info(f"✅ TTS: Ready")

    st.markdown("---")

    # Session stats
    st.markdown("#### 📊 Session Stats")
    st.metric("API Calls", st.session_state.api_call_count)
    session_mins = (datetime.now() - st.session_state.session_start_time).seconds // 60
    st.metric("Uptime", f"{session_mins} min")

    if st.session_state.authenticated:
        st.metric("User", st.session_state.user_name)
        st.metric("Conversations", len(st.session_state.conversation_history))

    # Error summary
    error_count = len(st.session_state.error_logs)
    if error_count > 0:
        st.markdown("---")
        st.markdown("#### ⚠️ Errors")
        st.error(f"{error_count} error(s) logged")

        # Group errors by type
        error_types = {}
        for error in st.session_state.error_logs:
            error_type = error['type']
            error_types[error_type] = error_types.get(error_type, 0) + 1

        for err_type, count in error_types.items():
            st.caption(f"• {err_type}: {count}")

    st.markdown("---")

    # Quick links
    st.markdown("#### 🔗 Quick Links")
    st.markdown("[Gemini API Console](https://makersuite.google.com)")
    st.markdown("[Check API Quota](https://makersuite.google.com)")
    st.markdown("[TiDB Dashboard](https://tidbcloud.com)")

    st.markdown("---")
    st.caption(f"🕐 {datetime.now().strftime('%H:%M:%S')}")

    # Auto-refresh button
    if st.button("🔄 Refresh Stats"):
        st.rerun()

# Main UI
st.markdown('<h1 class="main-header">📞 Smart Telecom Helpline</h1>', unsafe_allow_html=True)
st.markdown('<p style="text-align: center; color: #666;">AI-Powered Hinglish Voice Assistant</p>', unsafe_allow_html=True)

# Authentication Section
if not st.session_state.authenticated:
    st.markdown("### 🔐 Account Verification")
    st.info("Namaskar! Main aap ki telecom assistant hun. Kripaya apna mobile number enter kariye.")

    col1, col2 = st.columns([3, 1])
    with col1:
        phone_input = st.text_input("Enter your 10-digit mobile number", max_chars=10, placeholder="9876543210")
    with col2:
        st.write("")
        st.write("")
        verify_btn = st.button("Verify")

    if verify_btn:
        if len(phone_input) == 10 and phone_input.isdigit():
            user_data = get_user_info(phone_input)
            if user_data:
                st.session_state.authenticated = True
                st.session_state.phone = phone_input
                st.session_state.user_name = user_data[0]
                st.success(f"✅ Account verified! Welcome {user_data[0]}")
                st.rerun()
            else:
                st.error("❌ Mobile number not found in our records. Please contact customer care: 199")
        else:
            st.error("❌ Please enter a valid 10-digit mobile number")

    # Show test accounts
    with st.expander("🧪 Test Accounts (For Demo)"):
        st.markdown("""
        - **9876543210** - Rajesh Kumar (Jio Basic)
        - **9123456789** - Priya Sharma (Airtel Smart)
        - **9988776655** - Amit Singh (Vi Power)
        - **9555444333** - Sneha Gupta (BSNL Value)
        - **9111222333** - Vikash Yadav (Jio Premium)
        """)

else:
    # Authenticated User Interface
    user_data = get_user_info(st.session_state.phone)
    if user_data:
        name, balance_mb, plan_name, price, data_gb, validity_days = user_data
        balance_gb = balance_mb / 1024

        # User info header
        st.markdown(f"""
        <div class="user-info-box">
            <h3>👤 {name}</h3>
            <p><strong>Phone:</strong> {st.session_state.phone} | <strong>Plan:</strong> {plan_name} (Rs.{price})</p>
            <p><strong>Data Balance:</strong> {balance_gb:.1f} GB | <strong>Validity:</strong> {validity_days} days</p>
        </div>
        """, unsafe_allow_html=True)

        # Logout button
        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.session_state.phone = None
            st.session_state.user_name = None
            st.session_state.conversation_history = []
            st.rerun()

    st.markdown("---")
    st.markdown("### 🎙️ Voice Query or Type Your Question")

    # Two input methods: Voice and Text
    tab1, tab2 = st.tabs(["🎤 Voice Input", "⌨️ Text Input"])

    with tab1:
        st.info("Click 'Record Audio' below, speak your query, then click 'Stop Recording'")
        audio_file = st.audio_input("Record your voice query")

        if audio_file is not None:
            st.audio(audio_file, format="audio/wav")

            if st.button("🎯 Process Voice Query", key="voice_submit"):
                with st.spinner("Transcribing audio..."):
                    user_query = transcribe_audio(audio_file)

                if user_query:
                    st.success(f"📝 You said: {user_query}")

                    with st.spinner("Getting response..."):
                        response = get_ai_response(user_query, st.session_state.phone)

                        # Display response
                        st.markdown(f'<div class="response-box"><strong>🤖 Assistant:</strong><br>{response}</div>', unsafe_allow_html=True)

                        # Generate audio response
                        audio_response = text_to_speech(response)
                        if audio_response:
                            st.audio(audio_response, format="audio/mp3", autoplay=True)

                        # Add to history
                        st.session_state.conversation_history.append({
                            "query": user_query,
                            "response": response,
                            "timestamp": time.strftime("%H:%M:%S")
                        })
                else:
                    st.error("❌ Could not understand audio. Please try again or use text input.")

    with tab2:
        text_query = st.text_area("Type your question here", placeholder="e.g., Mera data balance kitna hai? or Best plan under 300?", height=100)

        if st.button("📤 Send Query", key="text_submit"):
            if text_query.strip():
                with st.spinner("Getting response..."):
                    response = get_ai_response(text_query, st.session_state.phone)

                    # Display response
                    st.markdown(f'<div class="response-box"><strong>🤖 Assistant:</strong><br>{response}</div>', unsafe_allow_html=True)

                    # Generate audio response
                    audio_response = text_to_speech(response)
                    if audio_response:
                        st.audio(audio_response, format="audio/mp3")

                    # Add to history
                    st.session_state.conversation_history.append({
                        "query": text_query,
                        "response": response,
                        "timestamp": time.strftime("%H:%M:%S")
                    })
            else:
                st.warning("⚠️ Please enter a question")

    # Conversation History
    if st.session_state.conversation_history:
        st.markdown("---")
        st.markdown("### 📜 Conversation History")

        for i, conv in enumerate(reversed(st.session_state.conversation_history)):
            with st.expander(f"🕐 {conv['timestamp']} - {conv['query'][:50]}..."):
                st.markdown(f"**You:** {conv['query']}")
                st.markdown(f"**Assistant:** {conv['response']}")

        if st.button("🗑️ Clear History"):
            st.session_state.conversation_history = []
            st.rerun()

    # System Status & Error Logs (visible when authenticated)
    st.markdown("---")
    st.markdown("### 📊 System Status")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("API Calls", st.session_state.api_call_count, delta="Free Tier: 15/min")

    with col2:
        session_duration = (datetime.now() - st.session_state.session_start_time).seconds // 60
        st.metric("Session Duration", f"{session_duration} min")

    with col3:
        error_count = len(st.session_state.error_logs)
        st.metric("Errors", error_count, delta="0 is good" if error_count == 0 else None, delta_color="inverse")

    # Display error logs if any
    if st.session_state.error_logs:
        with st.expander(f"⚠️ Error Logs ({len(st.session_state.error_logs)} errors)", expanded=False):
            st.warning("**Recent errors detected. Click entries below for details.**")

            for i, error in enumerate(reversed(st.session_state.error_logs[-10:])):  # Show last 10 errors
                error_color = "🔴" if "RATE_LIMIT" in error['type'] or "AUTH" in error['type'] else "🟡"

                with st.expander(f"{error_color} [{error['timestamp']}] {error['type']}"):
                    st.markdown(f"**Message:** {error['message']}")
                    if error['details']:
                        st.code(error['details'], language="text")

            if st.button("🗑️ Clear Error Logs"):
                st.session_state.error_logs = []
                st.rerun()

    # API Usage Info
    with st.expander("ℹ️ API Usage & Limits"):
        st.markdown("""
        **Gemini API Free Tier:**
        - 15 requests per minute
        - 1,500 requests per day
        - Current session: {calls} API calls

        **Google Speech Recognition:**
        - 60 minutes per month (free)
        - Resets monthly

        **gTTS (Text-to-Speech):**
        - Unlimited & free
        - No API key required

        **Need more quota?**
        - Gemini: https://makersuite.google.com
        - Speech API: https://cloud.google.com/speech-to-text
        """.format(calls=st.session_state.api_call_count))

# Footer (visible to all)
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #888; padding: 1rem;">
    <p>🆘 Need help? Call Customer Care: <strong>199 (toll-free)</strong></p>
    <p style="font-size: 0.8rem;">Smart Telecom Helpline - AI-Powered Voice Assistant</p>
</div>
""", unsafe_allow_html=True)
