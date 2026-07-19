from google import genai
from dotenv import load_dotenv
import os

load_dotenv()
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google-key.json"

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

try:
    response = client.models.generate_content(
        model="gemini-1.5-flash",  # Cambiado de gemini-2.5-flash-lite a este
        contents="Di únicamente: Hola"
    )
    print(response.text)
except Exception as e:
    print(f"Error encontrado: {e}")