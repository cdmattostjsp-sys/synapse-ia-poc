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
st.caption("Chat único com **Agente Orquestrador** e **Agentes Especializados** (PCA, DFD, ETP, TR, etc.), em conformidade com a Lei 14.133/21.")

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
# PROMPTS DOS AGENTES (ajustados à Lei 14.133/21)
# -------------------------------------------------
AGENTS: Dict[str, str] = {
    "PCA": (
        "Você é o Agente PCA (Plano de Contratações Anual). "
        "Objetivo: verificar se a contratação está contemplada no PCA, conforme art. 12, VII, da Lei 14.133/21. "
        "Saída: confirmação da aderência ao PCA ou recomendação de ajuste no planejamento."
    ),
    "DFD": (
        "Você é o Agente DFD. "
        "Objetivo: estruturar escopo, motivação, aderência ao PCA, requisitos mínimos, benefícios esperados. "
        "Verifique também sustentabilidade, acessibilidade e análise de riscos."
    ),
    "ETP": (
        "Você é o Agente ETP. "
        "Objetivo: analisar alternativas, estimativa de preços, justificativas, riscos e critérios de viabilidade. "
        "Considere obrigatoriamente a pesquisa de preços (art. 23 da Lei 14.133/21)."
    ),
    "TR": (
        "Você é o Agente TR. "
        "Objetivo: elaborar Termo de Referência conforme a Lei 14.133/21. "
        "Inclua objeto, justificativa, especificações, critérios de medição, SLAs, prazo, obrigações, julgamento, "
        "sustentabilidade e acessibilidade quando aplicáveis. "
        "Saída: TR estruturado + checklist normativo automático (modelo da Cartilha)."
    ),
    "PESQUISA": (
        "Você é o Agente Pesquisa de Preços. "
        "Objetivo: orientar fontes, metodologia, tratamento de outliers e consolidação."
    ),
    "MATRIZ": (
        "Você é o Agente Matriz de Riscos. "
        "Objetivo: identificar riscos por fase, impacto, probabilidade, mitigação e alocação contratante/contratada."
    ),
    "EDITAL": (
        "Você é o Agente Edital. "
        "Objetivo: estruturar edital em conformidade com a Lei 14.133/21. "
        "Inclua cláusulas obrigatórias e lembrete de publicação no PNCP."
    ),
    "CONTRATO": (
        "Você é o Agente Contrato Administrativo. "
        "Objetivo: consolidar minuta contratual conforme a Lei 14.133/21. "
        "Inclua objeto, vigência, reajuste, garantias, fiscalização, sanções, "
        "e lembrete de integração ao PNCP para transparência."
    ),
    "FISCALIZACAO": (
        "Você é o Agente de Fiscalização Contratual. "
        "Objetivo: estruturar plano de fiscalização conforme a Lei 14.133/21. "
        "Inclua indicadores, periodicidade de relatórios, responsáveis e linhas de defesa. "
        "Saída: plano estruturado + checklist de conformidade."
    ),
    "CHECKLIST": (
        "Você é o Agente Checklist Normativo. "
        "Objetivo: gerar checklist automático baseado na Cartilha da Lei 14.133/21 "
        "(compras, serviços comuns, obras e serviços de engenharia)."
    ),
}

# -------------------------------------------------
# FLUXO DE ETAPAS
# -------------------------------------------------
FLUXO_ARTEFATOS = ["PCA", "DFD", "ETP", "TR", "CONTRATO", "FISCALIZACAO", "CHECKLIST"]

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
    r"\bpca\b|plano de contrata": "PCA",
    r"\bdfd\b|formaliza": "DFD",
    r"\betp\b|estudo t[ée]cnico": "ETP",
    r"\btr\b|termo de refer[êe]ncia": "TR",
    r"pesquisa de pre[çc]os|cota[çc][aã]o": "PESQUISA",
    r"matriz de riscos|riscos\b": "MATRIZ",
    r"edital|minuta": "EDITAL",
    r"contrato\b": "CONTRATO",
    r"fiscaliza[çc][aã]o|gest[aã]o contratual": "FISCALIZACAO",
    r"checklist|conformidade": "CHECKLIST",
}

AGENT_ORDER = list(AGENTS.keys())
CONFIRMATIONS = ["sim", "ok", "vamos", "prossiga", "seguir", "continuar", "pode", "claro"]

# -------------------------------------------------
# ORQUESTRAÇÃO
# -------------------------------------------------
def route_stage(text: str) -> str:
    low = text.lower()
    for pattern, stage in SYNONYMS.items():
        if re.search(pattern, low):
            return stage
    if "current_stage" in st.session_state and st.session_state.current_stage:
        prox = proximo_artefato(st.session_state.current_stage)
        if prox:
            return prox
    return "PCA"

def call_agent(stage: str, user_text: str, history: List[Dict]) -> str:
    system = AGENTS.get(stage, AGENTS["TR"])
    ctx = [f"{m['role']}: {m['content']}" for m in history[-4:]]
    context_block = "\n".join(ctx) if ctx else "Sem histórico relevante."
    user_prompt = (
        f"Etapa: {stage}\n"
        f"Contexto recente:\n{context_block}\n\n"
        "Instruções ao agente:\n"
        "1) Verifique se o usuário forneceu dados obrigatórios da Lei 14.133/21.\n"
        "2) Se faltar algo (ex.: PCA, sustentabilidade, indicadores), pergunte antes de gerar.\n"
        "3) Se estiver completo, entregue o artefato estruturado.\n"
        "4) Inclua checklist ou lembrete de PNCP quando aplicável.\n"
        "5) Sempre sugira o próximo passo natural.\n\n"
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
    manual = st.selectbox("Escolher etapa:", AGENT_ORDER, index=0) if mode.startswith("Manual") else None
    st.divider()
    st.caption("POC com aderência à Lei 14.133/21. Respostas geradas por agentes com LLM.")

# Mensagem inicial
if not st.session_state.messages:
    st.session_state.messages.append({
        "role": "assistant",
        "content": (
            "Olá! Sou o **Agente Orquestrador** do Synapse.IA. "
            "Antes de elaborar o DFD, vamos confirmar se a contratação está contemplada no **Plano de Contratações Anual (PCA)**. "
            "Deseja começar pelo PCA ou prefere já iniciar pelo DFD?"
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
