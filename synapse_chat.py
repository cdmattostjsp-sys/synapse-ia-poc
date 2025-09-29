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
    "DFD": (
        "Você é o Agente DFD (Documento de Formalização da Demanda) do TJSP. "
        "Objetivo: estruturar escopo, motivação, aderência à necessidade, requisitos "
        "mínimos e benefícios esperados. Saída: DFD em tópicos claros."
    ),
    "ETP": (
        "Você é o Agente ETP (Estudo Técnico Preliminar) do TJSP. "
        "Objetivo: analisar alternativas, estimativa de preços, justificativas, "
        "riscos, critérios objetivos e viabilidade. Saída: ETP resumido e estruturado."
    ),
    "ITF": (
        "Você é o Agente ITF (Justificativa Técnica e Finalística / Instrumento de Planejamento). "
        "Objetivo: consolidar justificativa técnica-finalística, resultados esperados, "
        "indicadores e alinhamento estratégico. Saída: ITF claro e objetivo."
    ),
    "TR": (
        "Você é o Agente TR (Termo de Referência) do TJSP. "
        "Objetivo: redigir TR com objeto, justificativa, especificações, critérios "
        "de medição, SLAs, prazo, obrigações e critérios de julgamento. Saída: TR em seções."
    ),
    "PESQUISA": (
        "Você é o Agente de Pesquisa de Preços. "
        "Objetivo: orientar fontes, metodologia (painel, contratações similares, mercado), "
        "tratamento de outliers e consolidação. Saída: guia resumido + quadro sintético."
    ),
    "MATRIZ": (
        "Você é o Agente Matriz de Riscos. "
        "Objetivo: identificar riscos por fase, impacto e probabilidade, mitigações "
        "e alocação (contratante/contratada). Saída: tabela simples + comentários."
    ),
    "EDITAL": (
        "Você é o Agente Minutas/Editais. "
        "Objetivo: compor/minutar edital com cláusulas padrão, critérios objetivos, "
        "habilitação e penalidades. Saída: estrutura de edital em tópicos."
    ),
    "CONTRATO": (
        "Você é o Agente Contrato Administrativo. "
        "Objetivo: consolidar minuta contratual com objeto, vigência, reajuste, "
        "garantias, fiscalização e sanções. Saída: minuta resumida estruturada."
    ),
    "FISCALIZACAO": (
        "Você é o Agente de Gestão e Fiscalização Contratual. "
        "Objetivo: plano de fiscalização, indicadores, prazos de medição, "
        "checklists e comunicação. Saída: plano de fiscalização enxuto."
    ),
    "CHECKLIST": (
        "Você é o Agente Checklist Normativo. "
        "Objetivo: checar conformidade mínima com boa prática e leis aplicáveis. "
        "Saída: checklist de verificação simples (itens OK/NOK e observações)."
    ),
}

# -------------------------------------------------
# SINÔNIMOS PARA ROTEAMENTO (regex simples)
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

AGENT_ORDER = list(AGENTS.keys())  # para validação

# -------------------------------------------------
# FUNÇÕES DE ORQUESTRAÇÃO
# -------------------------------------------------
def route_stage(text: str) -> str:
    """Roteia pela regra; se não achar, pede ajuda para o LLM (fallback)."""
    low = text.lower()
    for pattern, stage in SYNONYMS.items():
        if re.search(pattern, low):
            return stage
    if client:
        msg = [
            {"role": "system", "content":
             "Classifique a intenção do usuário em UM rótulo: DFD, ETP, ITF, TR, PESQUISA, MATRIZ, EDITAL, CONTRATO, FISCALIZACAO, CHECKLIST. Responda apenas o rótulo."},
            {"role": "user", "content": low}
        ]
        try:
            out = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=msg,
                temperature=0.0,
                max_tokens=5
            ).choices[0].message.content.strip().upper()
            return out if out in AGENTS else "TR"
        except Exception:
            return "TR"
    return "TR"

def call_agent(stage: str, user_text: str, history: List[Dict]) -> str:
    """Chama o agente especializado (LLM) com um prompt de sistema + contexto curto."""
    system = AGENTS.get(stage, AGENTS["TR"])
    ctx = []
    for m in history[-4:]:
        ctx.append(f"{m['role']}: {m['content']}")
    context_block = "\n".join(ctx) if ctx else "Sem histórico relevante."

    user_prompt = (
        f"Etapa: {stage}\n"
        f"Contexto recente:\n{context_block}\n\n"
        f"Instruções ao agente: responda de forma objetiva, com seções e listas quando fizer sentido. "
        f"Se faltarem dados essenciais, pergunte de forma clara o que falta antes de concluir o artefato.\n\n"
        f"Entrada do usuário:\n{user_text}"
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=900
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"⚠️ Não consegui consultar o modelo agora. Detalhe: {e}"

def orchestrator_acknowledgement(stage: str, user_text: str) -> str:
    """Resposta mais natural/inteligente do agente orquestrador."""
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content":
                 "Você é o Agente Orquestrador do Synapse.IA. Sua tarefa é reconhecer a intenção do usuário, dizer que entendeu de forma amigável e indicar qual agente especializado irá responder. Seja acolhedor e natural, evite repetir o texto do usuário."},
                {"role": "user", "content": f"Etapa: {stage}\nMensagem do usuário: {user_text}"}
            ],
            temperature=0.6,
            max_tokens=120
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        return f"Entendido! Acionando o agente {stage} para te ajudar."

# -------------------------------------------------
# ESTADO DO CHAT
# -------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_stage" not in st.session_state:
    st.session_state.current_stage = None

# Sidebar: modo de roteamento (opcional)
with st.sidebar:
    st.markdown("### ⚙️ Opções")
    mode = st.radio("Roteamento", ["Automático (Orquestrador)", "Manual (eu escolho)"], index=0)
    if mode.startswith("Manual"):
        manual = st.selectbox("Escolher etapa:", AGENT_ORDER, index=3)  # default TR
    else:
        manual = None
    st.divider()
    st.caption("POC sem biblioteca. Respostas geradas por agentes com LLM.")

# Mensagem de boas-vindas (uma vez)
if not st.session_state.messages:
    st.session_state.messages.append({
        "role": "assistant",
        "content": (
            "Olá! Sou o **Agente Orquestrador** do Synapse.IA. "
            "Qual artefato você deseja elaborar? Exemplos: *DFD, ETP, ITF, TR, Pesquisa de Preços, Matriz de Riscos, Edital, Contrato, Fiscalização, Checklist*.\n\n"
            "Você pode também já descrever seus **insumos** (objeto, justificativa, requisitos, prazos, critérios etc.)."
        )
    })

# Render do histórico
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Entrada do usuário
user_input = st.chat_input("Escreva sua solicitação (documento desejado + contexto). Ex.: 'Quero um TR para vigilância...'")

if user_input:
    # 1) adiciona mensagem do usuário
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2) descobre a etapa
    if manual:
        stage = manual
    else:
        stage = route_stage(user_input)
    st.session_state.current_stage = stage

    # 3) resposta inteligente do orquestrador
    ack = orchestrator_acknowledgement(stage, user_input)
    st.session_state.messages.append({"role": "assistant", "content": ack})
    with st.chat_message("assistant"):
        st.markdown(ack)

    # 4) chama o agente especializado
    agent_answer = call_agent(stage, user_input, st.session_state.messages)

    # 5) exibe e grava
    st.session_state.messages.append({"role": "assistant", "content": agent_answer})
    with st.chat_message("assistant"):
        st.markdown(agent_answer)

# Rodapé
st.caption("🔒 POC para o TJSP. Nenhum dado é armazenado pelo app. Configure a chave em *Settings → Secrets* do Streamlit Cloud.")
