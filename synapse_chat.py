# synapse_chat.py
import re
import os
import streamlit as st
from datetime import datetime
from typing import List, Dict

# === OpenAI (SDK novo) ===
try:
    from openai import OpenAI
    _client_ok = True
except Exception:
    _client_ok = False

# -------------------------------------------------
# CONFIGURAÇÃO DA PÁGINA
# -------------------------------------------------
st.set_page_config(
    page_title="Synapse.IA – POC TJSP",
    page_icon="🧠",
    layout="wide"
)

st.markdown("# 🧠 Synapse.IA — POC TJSP")
st.caption("Chat único com **Agente Orquestrador** e **Agentes Especializados** (DFD, ETP, TR, etc.).")

# -------------------------------------------------
# SEGREDO (CHAVE) — VIA STREAMLIT SECRETS
# -------------------------------------------------
if "openai_api_key" not in st.secrets:
    st.warning("Adicione a chave da OpenAI em **Settings → Secrets** do Streamlit Cloud:\n\n```\nopenai_api_key = \"sk-...\"\n```")
    client = None
else:
    client = OpenAI(api_key=st.secrets["openai_api_key"])

if not _client_ok:
    st.error("Pacote `openai` não encontrado. Garanta que seu `requirements.txt` contém `openai`.")
    st.stop()

# -------------------------------------------------
# PROMPTS DOS AGENTES (enxutos e objetivos)
# -------------------------------------------------
AGENTS: Dict[str, str] = {
    "DFD": "...",  # [MANTER IGUAL]
    "ETP": "...",
    "ITF": "...",
    "TR": "...",
    "PESQUISA": "...",
    "MATRIZ": "...",
    "EDITAL": "...",
    "CONTRATO": "...",
    "FISCALIZACAO": "...",
    "CHECKLIST": "..."
}

SYNONYMS = { ... }  # [MANTER IGUAL]
AGENT_ORDER = list(AGENTS.keys())

# -------------------------------------------------
# FUNÇÕES DE ORQUESTRAÇÃO
# -------------------------------------------------
def route_stage(text: str) -> str:
    ...

def call_agent(stage: str, user_text: str, history: List[Dict]) -> str:
    ...

def orchestrator_acknowledgement(stage: str, user_text: str) -> str:
    ...

def sugestao_proximo_artefato(stage_atual: str) -> str:
    """Define o próximo artefato sugerido com base no anterior."""
    mapa = {
        "DFD": "ETP",
        "ETP": "TR",
        "TR": "CONTRATO",
        "CONTRATO": "FISCALIZACAO"
    }
    return mapa.get(stage_atual)

# -------------------------------------------------
# ESTADO DO CHAT
# -------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_stage" not in st.session_state:
    st.session_state.current_stage = None
if "artefatos" not in st.session_state:
    st.session_state.artefatos = {}

# Sidebar
with st.sidebar:
    st.markdown("### ⚙️ Opções")
    mode = st.radio("Roteamento", ["Automático (Orquestrador)", "Manual (eu escolho)"], index=0)
    manual = st.selectbox("Escolher etapa:", AGENT_ORDER, index=3) if mode.startswith("Manual") else None
    st.divider()
    st.caption("POC sem biblioteca. Respostas geradas por agentes com LLM.")

# Mensagem de boas-vindas
if not st.session_state.messages:
    st.session_state.messages.append({
        "role": "assistant",
        "content": (
            "Olá! Sou o **Agente Orquestrador** do Synapse.IA. "
            "Qual artefato você deseja elaborar? Exemplos: *DFD, ETP, ITF, TR, Pesquisa de Preços, Matriz de Riscos, Edital, Contrato, Fiscalização, Checklist*.\n\n"
            "Você pode também já descrever seus **insumos** (objeto, justificativa, requisitos, prazos, critérios etc.)."
        )
    })

# Render histórico
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Entrada do usuário
user_input = st.chat_input("Escreva sua solicitação (documento desejado + contexto). Ex.: 'Quero um TR para vigilância...'")

if user_input:
    # 1) salva entrada
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2) define etapa
    stage = manual or route_stage(user_input)
    st.session_state.current_stage = stage

    # 3) resposta inteligente do orquestrador
    ack = orchestrator_acknowledgement(stage, user_input)
    st.session_state.messages.append({"role": "assistant", "content": ack})
    with st.chat_message("assistant"):
        st.markdown(ack)

    # 4) chama agente especializado
    agent_answer = call_agent(stage, user_input, st.session_state.messages)

    # 5) exibe, grava e salva artefato
    st.session_state.messages.append({"role": "assistant", "content": agent_answer})
    st.session_state.artefatos[stage] = agent_answer
    with st.chat_message("assistant"):
        st.markdown(agent_answer)

    # 6) Sugere próximo artefato com base no atual
    proximo = sugestao_proximo_artefato(stage)
    if proximo and proximo not in st.session_state.artefatos:
        sugestao_texto = f"🔄 Deseja que eu gere o artefato **{proximo}** com base neste conteúdo de **{stage}**?"
        st.session_state.messages.append({"role": "assistant", "content": sugestao_texto})
        with st.chat_message("assistant"):
            st.markdown(sugestao_texto)

            if st.button(f"Gerar {proximo} automaticamente"):
                prompt_base = f"Use o conteúdo do artefato {stage} abaixo como base para gerar o {proximo}:\n\n{agent_answer}"
                nova_resposta = call_agent(proximo, prompt_base, st.session_state.messages)
                st.session_state.messages.append({"role": "assistant", "content": nova_resposta})
                st.session_state.artefatos[proximo] = nova_resposta
                st.markdown(nova_resposta)
