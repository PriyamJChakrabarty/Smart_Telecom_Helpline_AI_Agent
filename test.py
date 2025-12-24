import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables from .env file
load_dotenv()

# Get the API key from environment variables
api_key = os.getenv('GEMINI_API_KEY')

if not api_key:
    print("Error: GEMINI_API_KEY not found in .env file")
    exit(1)

# Configure the Gemini API
genai.configure(api_key=api_key)

# Create the model
model = genai.GenerativeModel('gemini-2.5-flash')

# Ask the question
question = "What is the capital of India?"
print(f"Question: {question}\n")

# Generate response
response = model.generate_content(question)

# Print the response
print(f"Gemini's Response:\n{response.text}")