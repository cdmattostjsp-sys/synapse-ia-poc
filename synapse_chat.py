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
# SEGREDO (CHAVE)
# -------------------------------------------------
if "openai_api_key" not in st.secrets:
    st.warning("""Adicione a chave da OpenAI em **Settings → Secrets** do Streamlit Cloud:""")
    client = None
else:
    client = OpenAI(api_key=st.secrets["openai_api_key"])

if not _client_ok:
    st.error("Pacote `openai` não encontrado. Garanta que seu `requirements.txt` contém `openai`.")
    st.stop()

# -------------------------------------------------
# PROMPTS DOS AGENTES
# -------------------------------------------------
AGENTS: Dict[str, str] = {
    "DFD": "Você é o Agente DFD. Objetivo: estruturar escopo, motivação, requisitos e benefícios.",
    "ETP": "Você é o Agente ETP. Objetivo: analisar alternativas, preços, riscos e viabilidade.",
    "ITF": "Você é o Agente ITF. Objetivo: consolidar justificativa técnico-finalística.",
    "TR": "Você é o Agente TR. Objetivo: redigir TR com objeto, justificativa, especificações e critérios.",
    "PESQUISA": "Você é o Agente de Pesquisa de Preços. Objetivo: orientar fontes e consolidar cotações.",
    "MATRIZ": "Você é o Agente Matriz de Riscos. Objetivo: identificar riscos, impacto e mitigação.",
    "EDITAL": "Você é o Agente Minutas/Editais. Objetivo: estruturar edital com cláusulas e critérios.",
    "CONTRATO": "Você é o Agente Contrato. Objetivo: consolidar minuta contratual resumida.",
    "FISCALIZACAO": "Você é o Agente de Fiscalização. Objetivo: plano de fiscalização e checklists.",
    "CHECKLIST": "Você é o Agente Checklist. Objetivo: checar conformidade mínima com normas."
}

# -------------------------------------------------
# FLUXO DE ETAPAS
# -------------------------------------------------
FLUXO_ARTEFATOS = ["DFD", "ETP", "TR", "CONTRATO", "FISCALIZACAO", "CHECKLIST"]

def proximo_artefato(stage_atual: str) -> str:
    if stage_atual in FLUXO_ARTEFATOS:
        idx = FLUXO_ARTEFATOS.index(stage_atual)
        if idx + 1 < len(FLUXO_ARTEFATOS):
            return FLUXO_ARTEFATOS[idx+1]
    return None

def progresso(stage_atual: str) -> str:
    etapas = [f"[{'X' if etapa == stage_atual else ' '}] {etapa}" for etapa in FLUXO_ARTEFATOS]
    return "📊 Progresso atual:\n" + "\n".join(etapas)

# -------------------------------------------------
# SINÔNIMOS
# -------------------------------------------------
SYNONYMS = {
    r"\bdfd\b|formaliza": "DFD",
    r"\betp\b|estudo t[ée]cnico": "ETP",
    r"\bitf\b|justificativa t[ée]cnica|final[íi]stica": "ITF",
    r"\btr\b|termo de refer[êe]ncia": "TR",
    r"pesquisa de pre[çc]os|cota[çc][aã]o": "PESQUISA",
    r"matriz de riscos|riscos\b": "MATRIZ",
    r"edital|minuta": "EDITAL",
    r"contrato\b": "CONTRATO",
    r"fiscaliza[çc][aã]o|gest[aã]o contratual": "FISCALIZACAO",
    r"checklist|conformidade": "CHECKLIST",
}

AGENT_ORDER = list(AGENTS.keys())

# -------------------------------------------------
# CONFIRMAÇÕES SIMPLES
# -------------------------------------------------
CONFIRMATIONS = ["sim", "ok", "vamos", "prossiga", "seguir", "continuar", "pode", "claro"]

# -------------------------------------------------
# ORQUESTRAÇÃO
# -------------------------------------------------
def route_stage(text: str) -> str:
    low = text.lower()
    for pattern, stage in SYNONYMS.items():
        if re.search(pattern, low):
            return stage
    # fallback: se não encontrar nada, usa próxima etapa do fluxo
    if "current_stage" in st.session_state and st.session_state.current_stage:
        prox = proximo_artefato(st.session_state.current_stage)
        if prox:
            return prox
    return "DFD"  # inicial

def call_agent(stage: str, user_text: str, history: List[Dict]) -> str:
    system = AGENTS.get(stage, AGENTS["TR"])
    ctx = [f"{m['role']}: {m['content']}" for m in history[-4:]]
    context_block = "\n".join(ctx) if ctx else "Sem histórico relevante."
    user_prompt = (
        f"Etapa: {stage}\n"
        f"Contexto recente:\n{context_block}\n\n"
        "Instruções ao agente:\n"
        "1) Verifique se o usuário forneceu todos os dados essenciais desta etapa.\n"
        "2) Se faltar algo importante, pergunte antes de gerar.\n"
        "3) Se estiver completo, entregue o artefato estruturado.\n"
        "4) Sempre sugira o próximo passo natural.\n\n"
        f"Entrada do usuário:\n{user_text}"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user_prompt}],
            temperature=0.3,
            max_tokens=900
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ Erro: {e}"

def orchestrator_acknowledgement(stage: str, user_text: str) -> str:
    # se for confirmação simples, avança para próxima etapa do fluxo
    if user_text.strip().lower() in CONFIRMATIONS:
        stage = proximo_artefato(st.session_state.current_stage) or stage
    
    barra = progresso(stage)
    msg = f"✅ Entendi, vamos trabalhar no artefato **{stage}**.\n\n{barra}\n"
    prox = proximo_artefato(stage)
    if prox:
        msg += f"\n👉 Após concluir, o próximo passo natural seria o **{prox}**. Deseja avançar nessa direção?"
    st.session_state.current_stage = stage
    return msg

# -------------------------------------------------
# ESTADO DO CHAT
# -------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_stage" not in st.session_state:
    st.session_state.current_stage = None
if "artefatos" not in st.session_state:
    st.session_state.artefatos = {}
if "insumos" not in st.session_state:
    st.session_state.insumos = {}

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
            "Qual artefato você deseja elaborar? Exemplos: *DFD, ETP, TR, Contrato, Fiscalização...*\n\n"
            "Você pode também já descrever seus **insumos** (objeto, justificativa, requisitos, prazos, critérios etc.)."
        )
    })

# Render histórico
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Entrada do usuário
user_input = st.chat_input("Escreva sua solicitação (ex.: 'Quero um TR para vigilância...')")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    stage = manual or route_stage(user_input)
    ack = orchestrator_acknowledgement(stage, user_input)
    st.session_state.messages.append({"role": "assistant", "content": ack})
    with st.chat_message("assistant"):
        st.markdown(ack)

    agent_answer = call_agent(stage, user_input, st.session_state.messages)
    st.session_state.messages.append({"role": "assistant", "content": agent_answer})
    st.session_state.artefatos[stage] = agent_answer
    with st.chat_message("assistant"):
        st.markdown(agent_answer)

    # Sugere próxima etapa
    proximo = proximo_artefato(stage)
    if proximo and proximo not in st.session_state.artefatos:
        with st.chat_message("assistant"):
            st.info(f"🔄 Deseja que eu gere o artefato **{proximo}** com base neste conteúdo de **{stage}**?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Avançar para {proximo}"):
                    prompt_base = f"Use o conteúdo do artefato {stage} abaixo como base para gerar o {proximo}:\n\n{agent_answer}"
                    nova_resposta = call_agent(proximo, prompt_base, st.session_state.messages)
                    st.session_state.messages.append({"role": "assistant", "content": nova_resposta})
                    st.session_state.artefatos[proximo] = nova_resposta
                    st.markdown(nova_resposta)
            with col2:
                if st.button("Quero revisar melhor esta etapa"):
                    st.session_state.messages.append({"role": "assistant", "content": "🔄 Ok, vamos detalhar melhor este artefato antes de seguir."})
                    st.markdown("🔄 Ok, vamos detalhar melhor este artefato antes de seguir.")
