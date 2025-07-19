import google.generativeai as genai
from dotenv import load_dotenv
import json
import os
from flask import Flask, request, jsonify

# --- 1. CONFIGURAÇÃO DA API GEMINI ---
load_dotenv()
try:
    API_KEY = os.getenv("GEMINI_API_KEY")

    if not API_KEY:
        print("Variavel de Ambiente 'GEMINI_API_KEY' não está definida.")
        exit()

    genai.configure(api_key=API_KEY)

except Exception as e:
    print(f"Erro ao configurar a API do Gemini: {e}")
    print("Verifique se a chave de API está correta e se a biblioteca 'google-generativeai' está instalada.")
    exit()

# --- 2. DEFINIÇÃO DOS SYSTEM PROMPTS ---

# System Prompt para a LLM 1:
SYSTEM_PROMPT_LLM1 = """
You are an intelligent JSON data processing assistant.
Your task is to update a JSON object based on a natural language instruction.
You will receive a current JSON object and a new transaction description.
1. Identify the user ID and the value of the new transaction from the description.
2. Calculate the total value if necessary (e.g., '3 items at $12 each' is $36).
3. Add this new value to the existing 'gastos' (spend) for the correct user ID.
4. Return the ENTIRE, UPDATED JSON object.
You MUST provide a brief, one-sentence explanation of the calculation you performed BEFORE providing the final JSON block.
"""

# System Prompt para a LLM 2:
SYSTEM_PROMPT_LLM2 = """
You are a JSON extraction tool.
Your sole purpose is to find and extract a valid JSON object from the given text.
Do NOT add any explanation, commentary, or any text before or after the JSON.
Only return the JSON object itself.
Your output must be *only* the JSON object itself, starting with `{` and ending with `}`.
If no JSON is found, output an empty JSON object: {}.
"""

# --- 3. DEFINIÇÃO DOS MODELOS ---
llm1_calculator = genai.GenerativeModel(
    model_name='gemini-1.5-flash', # Recomendo usar 1.5-flash que é mais recente
    system_instruction=SYSTEM_PROMPT_LLM1
)

llm2_guardrail = genai.GenerativeModel(
    model_name='gemini-1.5-flash', # Recomendo usar 1.5-flash que é mais recente
    system_instruction=SYSTEM_PROMPT_LLM2
)

# --- 4. CRIAÇÃO DA APLICAÇÃO FLASK ---
app = Flask(__name__)


def run_fluxo_completo(dados_iniciais, nova_transacao):
    """
    Executa o fluxo completo de duas LLMs.
    Esta função permanece a mesma, mas agora será chamada pela API.
    """
    print("----------- INÍCIO DO FLUXO -----------")
    print("\n[ETAPA 1: LLM CALCULADORA]")

    # --- CONSTRUÇÃO DO PROMPT PARA A LLM 1 ---
    prompt_usuario_llm1 = f"""
    Here is the current data:
    ```json
    {json.dumps(dados_iniciais, indent=2)}
    ```

    Now, process the following new transaction:
    - User ID: {nova_transacao['usuario_id']}
    - Description: "{nova_transacao['descricao']}"

    Update the JSON and provide the full new object.
    """

    print(f"Enviando para a LLM 1 a seguinte tarefa:\n'{nova_transacao['descricao']}' para o usuário {nova_transacao['usuario_id']}")

    # --- EXECUÇÃO DA LLM 1 ---
    try:
        response_llm1 = llm1_calculator.generate_content(prompt_usuario_llm1)
        output_llm1 = response_llm1.text
    except Exception as e:
        print(f"Erro ao chamar a LLM 1: {e}")
        return None # Retorna None em caso de erro

    print("\n[SAÍDA BRUTA DA LLM 1 (COM TEXTO EXTRA)]:")
    print("-----------------------------------------")
    print(output_llm1)
    print("-----------------------------------------")

    print("\n[ETAPA 2: LLM GUARDIÃO (GUARDRAIL)]")
    print("Enviando a saída da LLM 1 para a LLM 2 para extrair apenas o JSON...")

    # --- EXECUÇÃO DA LLM 2 ---
    try:
        response_llm2 = llm2_guardrail.generate_content(output_llm1)
        output_llm2_json_str = response_llm2.text.strip()
    except Exception as e:
        print(f"Erro ao chamar a LLM 2: {e}")
        return None # Retorna None em caso de erro

    print("\n[SAÍDA FINAL E LIMPA DA LLM 2]:")
    print("-----------------------------------------")
    print(output_llm2_json_str)
    print("-----------------------------------------")

    # --- VERIFICAÇÃO FINAL ---
    try:
        if output_llm2_json_str.startswith("```json"):
            output_llm2_json_str = output_llm2_json_str[7:]
        if output_llm2_json_str.endswith("```"):
            output_llm2_json_str = output_llm2_json_str[:-3]
        
        output_llm2_json_str = output_llm2_json_str.strip()
        final_json_obj = json.loads(output_llm2_json_str)

        print("\n✅ SUCESSO! A saída da LLM 2 é um JSON válido.")
        print("----------- FIM DO FLUXO -----------")
        return final_json_obj
    except json.JSONDecodeError as e:
        print(f"\n❌ ERRO! A saída da LLM 2 não é um JSON válido: {e}")
        print("----------- FIM DO FLUXO -----------")
        return None

# --- 5. DEFINIÇÃO DO ENDPOINT DA API REST ---
@app.route('/processar_transacao', methods=['POST'])
def processar_transacao_api():
    """
    Endpoint da API para receber os dados, processar e retornar o resultado.
    """
    # Pega o JSON do corpo da requisição
    dados_requisicao = request.get_json()

    # Validação básica do JSON de entrada
    if not dados_requisicao or 'usuarios' not in dados_requisicao or 'gastos' not in dados_requisicao or 'ultima_transacao' not in dados_requisicao:
        return jsonify({"erro": "JSON inválido ou chaves 'usuarios', 'gastos', 'ultima_transacao' ausentes."}), 400

    # Prepara os dados para a função de fluxo
    dados_iniciais = {
        "usuarios": dados_requisicao['usuarios'],
        "gastos": dados_requisicao['gastos']
    }
    nova_transacao = dados_requisicao['ultima_transacao']

    # Executa o fluxo completo
    json_resultado = run_fluxo_completo(dados_iniciais, nova_transacao)

    # Retorna o resultado
    if json_resultado:
        return jsonify(json_resultado), 200
    else:
        # Se o fluxo falhou, retorna um erro do servidor
        return jsonify({"erro": "Ocorreu um erro interno ao processar a transação com os modelos de IA."}), 500

# --- 6. EXECUÇÃO DO SERVIDOR FLASK ---
if __name__ == "__main__":
    # Instale as dependências com: pip install Flask google-generativeai python-dotenv
    # Rode a API com: python seu_arquivo.py
    # O servidor estará disponível em http://127.0.0.1:5000
    print("Iniciando servidor Flask...")
    app.run(debug=True, port=5000)