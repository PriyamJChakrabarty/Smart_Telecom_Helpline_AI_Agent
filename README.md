# Smart Telecom Helpline: AI Agent

An intelligent Hinglish-speaking voice assistant that makes telecom services simple, accessible, and human-like — no more confusing IVRs or endless menus.

🌐 **Now available with Web Interface!** Choose between CLI or beautiful Streamlit web UI.





📌 Problem Statement

Telecom companies in India serve hundreds of millions of users, many of whom:

Face difficulty navigating complex IVR menus.

Struggle with digital apps due to limited literacy or smartphone knowledge.

Prefer speaking in Hinglish (natural Hindi-English mix).

Need instant answers about mobile recharges, data balance, validity, or network issues.

Current systems — SMS notifications, mobile apps, or call center IVRs — often create confusion, frustration, and delays, leading to poor customer satisfaction and high operational costs.

💡 Solution Overview

This project implements an Agentic AI Call Agent that acts as a telecom helpline representative, but in a friendly Hinglish voice conversation. It provides users with direct, spoken answers about their telecom needs without navigating endless menus.

Key Features

Natural Hinglish Conversation – Customers can ask:

"Mera data balance kitna bacha hai?"

"Best recharge plan under 300 rupees kya hai?"

"Mera number kab tak valid hai?"

Voice-Based Interaction – Listens to queries and replies in spoken Hinglish, removing text barriers.

Preloaded Telecom Knowledge – Handles FAQs like recharge packs, balance check, SIM validity, complaint status.

Respectful & Clear Tone – Uses polite Hinglish (“aap”, “sir/madam”) to sound like a professional telecom agent.

Fallback Support – If query is too complex, politely directs the customer to a human agent or service center.

🎯 Business Logic

User calls the AI agent → Asks queries in Hinglish.

Agent listens & extracts intent → Identifies topic: recharge, balance, validity, complaints, etc.

Knowledge Lookup → Finds structured telecom info (plans, balances, offers).

Response Generated in Hinglish → Example:

"Ji madam, aapke number ka data balance 1.2 GB hai aur validity 3 din tak hai."

"Best recharge ₹249 hai, jo 1.5 GB/day aur unlimited calls deta hai, 28 din ke liye."

Agent speaks the reply → No need to press keys or read SMS.

📊 Why This Matters for Telecoms

Better Customer Experience → Removes IVR pain, offers instant answers.

Accessibility → Works for people with limited literacy or app access.

Reduced Call Center Load → Automates common queries like data balance, recharge packs.

Stronger Customer Loyalty → Conversational Hinglish feels familiar and trustworthy.

24/7 Service → Always available, unlike human agents.

## 🚀 Quick Start

### Option 1: Web Interface (Recommended)
```bash
pip install -r requirements.txt
streamlit run app.py
```
Open browser at `http://localhost:8501` → Enter phone number → Use voice or text queries!

### Option 2: CLI Version
```bash
pip install -r requirements.txt
python main.py
```

📖 **Full Setup Guide**: See [RUN_GUIDE.md](RUN_GUIDE.md)
☁️ **Cloud Deployment**: See [DEPLOYMENT.md](DEPLOYMENT.md)

## 🎨 Features

### Web Interface (`app.py`)
- ✅ Beautiful Streamlit UI with voice recording
- ✅ Browser-based audio input/output
- ✅ Text input alternative
- ✅ Conversation history
- ✅ User dashboard with balance/plan info
- ✅ Cloud deployment ready (Streamlit Cloud, Hugging Face)

### CLI Version (`main.py`)
- ✅ System microphone voice input
- ✅ Speaker audio output
- ✅ Terminal-based interaction
- ✅ Lightweight and fast

## 🧪 Test Accounts

| Phone | Name | Plan | Data |
|-------|------|------|------|
| 9876543210 | Rajesh Kumar | Jio Basic | 800 MB |
| 9123456789 | Priya Sharma | Airtel Smart | 1.2 GB |
| 9988776655 | Amit Singh | Vi Power | 2 GB |

## 🏗️ Tech Stack

- **Frontend**: Streamlit (Python web framework)
- **Voice**: Google Speech Recognition + gTTS
- **LLM**: Google Gemini 1.5 Flash
- **Database**: TiDB Cloud (MySQL-compatible)
- **Language**: Python 3.8+

## 📦 Deployment Options

❌ **Vercel** - Not compatible (Node.js only)

✅ **Streamlit Cloud** - Free, recommended (see DEPLOYMENT.md)
✅ **Hugging Face Spaces** - Free alternative
✅ **Railway / Render** - Free tier available

## 🚀 Future Extensions

Integration with live telecom systems → Check actual balance, process recharges.

Regional Language Support → Beyond Hinglish, add Tamil, Bengali, Marathi, etc.

Complaint Management → Log and track network issues automatically.

Smart Upselling → Suggest personalized recharge packs based on user behavior.