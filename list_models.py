from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

for model in client.models.list():
    # Solo muestra modelos que soportan generación de contenido
    if "generateContent" in model.supported_actions:
        print(model.name)