# agent.py - Improved Telecom AI Agent with FAISS Retrieval
import speech_recognition as sr
from gtts import gTTS
import pygame
import os
import google.generativeai as genai
from dotenv import load_dotenv
from sqlalchemy import text
from faiss_retriever import FAISSRetriever

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")  # Default to 2.0-flash if not set

genai.configure(api_key=GEMINI_API_KEY)

try:
    from db import engine
except ImportError:
    print("Create db.py with TiDB connection")
    exit(1)

class TelecomAIAgent:
    def __init__(self):
        self.recognizer = sr.Recognizer()
        self.model = genai.GenerativeModel(GEMINI_MODEL)
        pygame.mixer.init()
        self.engine = engine
        self.current_phone = None
        print(f"[INFO] Using Gemini model: {GEMINI_MODEL}")

        # Initialize FAISS retriever for FAQ search
        print("[INFO] Initializing FAISS retriever...")
        try:
            self.faiss_retriever = FAISSRetriever()
            print("[INFO] FAISS retriever ready")
        except Exception as e:
            print(f"[WARNING] FAISS initialization failed: {e}")
            self.faiss_retriever = None

        # Metrics tracking
        self.total_queries = 0
        self.faiss_hits = 0
        self.llm_calls = 0  
        
        self.telecom_data = {
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
    
    def listen(self):
        """Voice input from user - English recognition like admission assistant"""
        with sr.Microphone() as source:
            print("Listening...")
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                audio = self.recognizer.listen(source, timeout=10)
                text = self.recognizer.recognize_google(audio, language="en-IN")
                print(f"You said: {text}")
                return text.lower()
            except sr.WaitTimeoutError:
                print("Listening timeout")
                return ""
            except sr.UnknownValueError:
                print("Could not understand audio")
                return ""
            except Exception as e:
                print(f"Error: {e}")
                return ""
    
    def speak(self, text):
        """Voice output to user"""
        print(f"Telecom Assistant: {text}")
        filename = f"telecom_response_{os.getpid()}.mp3"
        try:
            tts = gTTS(text=text, lang='en', tld='co.in', slow=False)
            tts.save(filename)
            pygame.mixer.music.load(filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            pygame.mixer.music.unload()
            if os.path.exists(filename):
                os.remove(filename)
        except Exception as e:
            print(f"Speech error: {e}")
    
    def get_user_info(self, phone):
        """Get user data from database"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT u.name, u.balance_mb, p.plan_name, p.price, p.data_gb, p.validity_days
                    FROM users u 
                    JOIN plans p ON u.plan_id = p.plan_id
                    WHERE u.phone = :phone
                """), {'phone': phone})
                return result.fetchone()
        except Exception as e:
            print(f"Database error: {e}")
            return None
    
    def get_plans_by_budget(self, max_price):
        """Get plans within budget"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT plan_name, price, data_gb, validity_days
                    FROM plans 
                    WHERE price <= :max_price
                    ORDER BY price
                """), {'max_price': max_price})
                return result.fetchall()
        except Exception as e:
            print(f"Database error: {e}")
            return []
    
    def get_last_recharge(self, phone):
        """Get recent transaction"""
        try:
            with self.engine.connect() as conn:
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
            print(f"Database error: {e}")
            return None
    
    def extract_phone_number(self, user_input):
        """Extract phone number from user input"""
        import re
        phone_pattern = r'\b\d{10}\b'
        match = re.search(phone_pattern, user_input)
        if match:
            return match.group()
        return None
    
    def find_relevant_data(self, user_input):
        """Extract relevant telecom data based on user query"""
        relevant_info = ""
        
        if not self.current_phone:
            return "Account verification required. Please restart the application."
        
        user_data = self.get_user_info(self.current_phone)
        if not user_data:
            return "User data not available from database. Please contact customer care 199."
        
        name, balance_mb, plan_name, price, data_gb, validity_days = user_data
        balance_gb = balance_mb / 1024 if balance_mb else 0
        
        if any(word in user_input for word in ["balance", "data", "remaining", "left", "kitna", "how much"]):
            relevant_info += f"Dear {name}, your current data balance is {balance_gb:.1f} GB remaining. "
        
        if any(word in user_input for word in ["plan", "current", "my plan", "active plan", "subscription"]):
            relevant_info += f"Your active plan: {plan_name} at Rs.{price} with {data_gb}GB data for {validity_days} days validity. "
        
        if any(word in user_input for word in ["recharge", "new plan", "plan change", "under", "budget", "cheap", "affordable"]):
            budget = 300 
            if "200" in user_input or "two hundred" in user_input:
                budget = 200
            elif "500" in user_input or "five hundred" in user_input:
                budget = 500
            elif "1000" in user_input or "thousand" in user_input:
                budget = 1000
            
            plans = self.get_plans_by_budget(budget)
            if plans:
                relevant_info += f"Available plans under Rs.{budget}: "
                for i, plan in enumerate(plans[:3]):
                    relevant_info += f"{plan[0]} Rs.{plan[1]} with {plan[2]}GB for {plan[3]} days"
                    if i < len(plans[:3]) - 1:
                        relevant_info += ", "
                relevant_info += ". "
            
            if budget <= 400:
                budget_plans = self.telecom_data["recharge_plans"]["prepaid"]["budget_plans"]
                relevant_info += f"Popular options: "
                for plan in budget_plans:
                    if plan["price"] <= budget:
                        relevant_info += f"{plan['name']} Rs.{plan['price']} with {plan['data']} for {plan['validity']}, "
        
        if any(word in user_input for word in ["last recharge", "history", "payment", "transaction", "when recharged"]):
            txn = self.get_last_recharge(self.current_phone)
            if txn:
                date_str = txn[1].strftime('%d %B %Y') if txn[1] else "N/A"
                relevant_info += f"Your last recharge: Rs.{txn[0]} on {date_str}. Status: {txn[2]}. "
        
        if any(word in user_input for word in ["help", "problem", "support", "customer care", "complaint", "issue"]):
            services = self.telecom_data["services"]
            relevant_info += f"Customer support available at {services['customer_care']}. Check balance: {services['balance_check']}, data: {services['data_check']}. "
        
        if any(word in user_input for word in ["network", "slow", "not working", "connection", "internet"]):
            support = self.telecom_data["support_info"]
            relevant_info += f"For network issues: {support['network_issues']}. Data not working: {support['data_not_working']}. "
        
        if any(word in user_input for word in ["offer", "discount", "deal", "cashback", "free"]):
            offers = self.telecom_data["offers"]
            relevant_info += f"Current offers: {offers['weekend_offer']}. {offers['student_discount']}. {offers['family_pack']}. "
        
        if any(word in user_input for word in ["bill", "payment due", "amount", "pay"]):
            relevant_info += f"For bill queries: {self.telecom_data['support_info']['bill_queries']}. Use {self.telecom_data['services']['app']} or website {self.telecom_data['services']['website']}. "
        
        return relevant_info
    
    def get_ai_response(self, user_input):
        """Generate AI response using FAISS retrieval first, then LLM fallback"""
        self.total_queries += 1

        # Step 1: Try FAISS retrieval first (reduces LLM calls by ~70%)
        if self.faiss_retriever:
            faq_match = self.faiss_retriever.get_best_answer(user_input, threshold=0.65)

            if faq_match:
                self.faiss_hits += 1
                print(f"[FAISS HIT] Score: {faq_match['score']:.3f} | Category: {faq_match['category']}")

                # Personalize FAQ answer with user data
                answer = faq_match['answer']
                if self.current_phone:
                    user_data = self.get_user_info(self.current_phone)
                    if user_data:
                        name, balance_mb, plan_name, price, data_gb, validity_days = user_data
                        # Replace placeholders in FAQ answer
                        answer = answer.replace("{balance_mb}", str(balance_mb))
                        answer = answer.replace("{plan_name}", plan_name)
                        answer = answer.replace("{price}", str(price))
                        answer = answer.replace("{data_gb}", str(data_gb))
                        answer = answer.replace("{validity_days}", str(validity_days))

                print(f"[METRICS] FAISS: {self.faiss_hits}/{self.total_queries} | LLM Reduction: {(self.faiss_hits/self.total_queries)*100:.1f}%")
                return answer

        # Step 2: Fallback to LLM if no FAQ match
        self.llm_calls += 1
        print(f"[LLM FALLBACK] No FAISS match found, using Gemini...")

        relevant_data = self.find_relevant_data(user_input)

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
            response = self.model.generate_content(prompt)
            print(f"[METRICS] FAISS: {self.faiss_hits}/{self.total_queries} | LLM Reduction: {(self.faiss_hits/self.total_queries)*100:.1f}%")
            return response.text
        except Exception as e:
            print(f"AI Error: {e}")
            return "Maaf kijiye, kuch technical problem hai. Customer care 199 par call kariye immediate help ke liye."
    
    def get_phone_number_input(self):
        """Get phone number via CLI input after voice greeting"""
        greeting = "Namaskar! Main aap ki telecom assistant hun. Kripaya apna 10-digit mobile number type kariye terminal mein verification ke liye."
        self.speak(greeting)
        
        while True:
            try:
                print("\n" + "="*50)
                phone = input("Enter your 10-digit mobile number: ").strip()
                if len(phone) == 10 and phone.isdigit():
                    print(f"Checking account for {phone}...")
                    user_data = self.get_user_info(phone)
                    if user_data:
                        print(f"Account verified: {user_data[0]}")
                        verification_msg = f"Account verified ho gaya! Welcome {user_data[0]}. Ab aap voice commands use kar sakte hain."
                        self.speak(verification_msg)
                        self.current_phone = phone
                        return True
                    else:
                        print("Mobile number not found in our records.")
                        error_msg = "Ye number hamare records mein nahi mila. Kripaya sahi number type kariye ya customer care 199 par call kariye."
                        self.speak(error_msg)
                        retry = input("Try again? (y/n): ").strip().lower()
                        if retry != 'y':
                            return False
                else:
                    print("Please enter a valid 10-digit mobile number.")
                    error_msg = "Galat number format. Kripaya 10-digit mobile number type kariye."
                    self.speak(error_msg)
            except KeyboardInterrupt:
                print("\nExiting...")
                return False
            except Exception as e:
                print(f"Error: {e}")
                return False
    
    def start_conversation(self):
        """Start the conversation"""
        print("="*60)
        print("         TELECOM AI AGENT STARTED")
        print("="*60)
        print("1. Listen to voice instruction")
        print("2. Type your mobile number when asked")
        print("3. Then use voice commands for queries")
        print("4. Say 'bye' or 'goodbye' to exit")
        print("="*60)
        
        if not self.get_phone_number_input():
            farewell_msg = "Dhanyawad! Customer care 199 par call kariye help ke liye."
            self.speak(farewell_msg)
            print("Unable to verify account. Contact customer care: 199")
            return
        
        user_data = self.get_user_info(self.current_phone)
        print(f"\n🎤 Voice conversation started with {user_data[0]}")
        print("Listening for your queries...")
        
        conversation_start = f"Ab main ready hun aap ke queries ke liye {user_data[0]}! Data balance, recharge plans, bill payment ya koi bhi sawal kar sakte hain."
        self.speak(conversation_start)
        
        while True:
            user_input = self.listen()
            
            if user_input and any(word in user_input for word in ["bye", "goodbye", "exit", "quit", "thank you", "dhanyawad"]):
                if self.current_phone:
                    user_data = self.get_user_info(self.current_phone)
                    farewell = f"Dhanyawad {user_data[0] if user_data else 'sir/madam'}! Customer care 199 par call kariye agar aur help chahiye. Aap ka din shubh ho!"
                else:
                    farewell = "Dhanyawad! Customer care 199 par call kariye agar help chahiye. Good day!"
                self.speak(farewell)
                break
                
            if user_input:
                response = self.get_ai_response(user_input)
                self.speak(response)
            else:
                self.speak("Main aap ki baat samajh nahin payi. Kripaya apna sawal repeat kar dijiye.")

def main():
    try:
        agent = TelecomAIAgent()
        agent.start_conversation()
    except KeyboardInterrupt:
        print("\nProgram stopped by user.")
    except Exception as e:
        print(f"Error starting telecom agent: {e}")
        print("Please ensure all dependencies are installed and database is configured.")

if __name__ == "__main__":
    main()