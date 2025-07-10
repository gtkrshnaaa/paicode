# pai_code/llm.py

import os
import google.generativeai as genai
from dotenv import load_dotenv

# Muat environment variable dari file .env
load_dotenv()

# Konfigurasi API key
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY tidak ditemukan. Pastikan ada di file .env")

genai.configure(api_key=API_KEY)

# Inisialisasi model
model = genai.GenerativeModel('gemini-1.5-flash')

def generate_text(prompt: str) -> str:
    """Mengirim prompt ke Gemini API dan mengembalikan respons teks."""
    print("Berpikir...")
    try:
        response = model.generate_content(prompt)
        # Membersihkan output dari markdown code blocks jika ada
        cleaned_text = response.text.strip()
        if cleaned_text.startswith("```python"):
            cleaned_text = cleaned_text[len("```python"):].strip()
        elif cleaned_text.startswith("```"):
             cleaned_text = cleaned_text[len("```"):].strip()

        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-len("```")].strip()
            
        return cleaned_text
    except Exception as e:
        print(f"Terjadi kesalahan pada API LLM: {e}")
        return ""