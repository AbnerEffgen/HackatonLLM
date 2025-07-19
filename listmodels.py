import os
from dotenv import load_dotenv
import google.generativeai as genai

# Carrega variáveis do .env
load_dotenv()

def listar_modelos():
    API_KEY = os.getenv("GEMINI_API_KEY")
    if not API_KEY:
        print("❌ A variável 'GEMINI_API_KEY' não está definida.")
        return

    # Configura a API
    genai.configure(api_key=API_KEY, transport="grpc")

    try:
        modelos = genai.list_models()
        print("\nModelos disponíveis:")
        for modelo in modelos:
            nome = modelo.name
            desc = getattr(modelo, "description", "Sem descrição")
            methods = getattr(modelo, "supported_generation_methods", [])
            print(f"- {nome}\n  ▶ {desc}\n  ▶ Métodos: {methods}\n")
    except Exception as e:
        print(f"❌ Erro ao listar modelos: {e}")

if __name__ == "__main__":
    listar_modelos()