import os
import json
import streamlit as st
from typing import Dict, Any
from openai import OpenAI

# ==============================================
# CONFIGURAÇÃO DA PÁGINA
# ==============================================
st.set_page_config(
    page_title="Synapse.IA — POC TJSP",
    page_icon="🧠",
    layout="wide"
)

# ==============================================
# CLIENTE OPENAI
# ==============================================
client = None
try:
    client = OpenAI()
    _client_ok = True
except Exception as e:
    _client_ok = False
    st.error(f"Falha ao inicializar cliente OpenAI: {e}")

# ==============================================
# FUNÇÕES AUXILIARES
# ==============================================
PROMPTS_DIR = "prompts"

def load_prompt(agent: str) -> str:
    """Carrega o prompt de um agente a partir de um arquivo JSON na pasta /prompts"""
    file_path = os.path.join(PROMPTS_DIR, f"{agent.upper()}.json")
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("prompt", f"[Prompt não definido no {agent}.json]")
        except Exception as e:
            return f"[Erro ao carregar {agent}.json: {e}]"
    return f"[Arquivo {agent}.json não encontrado em {PROMPTS_DIR}/]"

def call_openai(prompt: str, user_input: str) -> str:
    """Executa chamada ao modelo da OpenAI"""
    if not _client_ok:
        return "⚠️ Cliente OpenAI não configurado corretamente."
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_input}
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"⚠️ Erro na API: {e}"

# ==============================================
# INTERFACE STREAMLIT
# ==============================================
st.title("🧠 Synapse.IA — POC TJSP")
st.caption("Agente Orquestrador com prompts externos")

# Caixa de entrada do usuário
user_input = st.text_area("Descreva seu pedido ou responda às perguntas do agente...", "")

if st.button("Enviar") and user_input.strip():
    # Exemplo: rodando sempre pelo agente DFD (pode evoluir para lógica de fluxo)
    agent_name = "DFD"
    prompt = load_prompt(agent_name)
    
    st.subheader(f"🤖 Resposta do agente {agent_name}")
    output = call_openai(prompt, user_input)
    st.write(output)

