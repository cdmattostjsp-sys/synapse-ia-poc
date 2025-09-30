import re
import os
import json
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
st.caption("Chat único com **Agente Orquestrador** e **Agentes Especializados** (PCA, DFD, ETP, TR, Contrato, Fiscalização, Checklist).")

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
# NORMAS BASE
# -------------------------------------------------
NORMAS_BASE = [
    "Lei 14.133/2021 (Nova Lei de Licitações e Contratos)",
    "Decreto Estadual 67.381/2022",
    "Provimento CSM 2724/2023",
    "Manuais TJSP de Licitações e Contratos (2025)",
    "Boas práticas TCU/TCE-SP"
]

# -------------------------------------------------
# PROMPTS EXTERNALIZADOS
# -------------------------------------------------
def load_prompt(agent: str) -> str:
    """Carrega prompt externo (JSON) com base no nome do agente"""
    base_path = "./prompts"
    path = os.path.join(base_path, f"{agent}.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("prompt", "")
    return f"Você é o Agente {agent}."

# Ordem oficial dos agentes
AGENT_ORDER = ["PCA", "DFD", "ETP", "TR", "CONTRATO", "FISCALIZACAO", "CHECKLIST"]

# -------------------------------------------------
# FUNÇÕES AUXILIARES
# -------------------------------------------------
def progresso(stage: str) -> str:
    marcadores = []
    for s in AGENT_ORDER:
        if st.session_state.artefatos.get(s):
            marcadores.append(f"[X] {s}")
        else:
            marcadores.append(f"[ ] {s}")
    return "📊 Progresso atual: " + " ".join(marcadores)

def proximo_artefato(stage: str) -> str:
    try:
        idx = AGENT_ORDER.index(stage)
        return AGENT_ORDER[idx + 1] if idx + 1 < len(AGENT_ORDER) else None
    except ValueError:
        return None

def call_agent(stage: str, user_text: str, history: List[Dict]) -> Dict:
    """Chama agente especializado. Retorna estrutura com insumos classificados (✅/⚠️/❌)."""
    system_prompt = load_prompt(stage) + "\n\nInstruções gerais:\n"
    system_prompt += (
        "1) Seja claro e institucional.\n"
        "2) Pergunte insumos obrigatórios se faltarem.\n"
        "3) Estruture saída em seções.\n"
        "4) Classifique cada insumo em ✅ Pronto, ⚠️ Parcial ou ❌ Pendente.\n"
        "5) Fundamente nas normas aplicáveis.\n"
        f"Normas de referência: {', '.join(NORMAS_BASE)}.\n"
        "6) Ao final, sugira o próximo passo.\n"
        "IMPORTANTE: responda SEMPRE em JSON válido."
    )

    ctx = [f"{m['role']}: {m['content']}" for m in history[-4:]]
    context_block = "\n".join(ctx) if ctx else "Sem histórico relevante."

    user_prompt = (
        f"Etapa: {stage}\n"
        f"Contexto recente:\n{context_block}\n\n"
        f"Entrada do usuário:\n{user_text}\n\n"
        "Responda em formato JSON estruturado:\n"
        "{ 'insumos': { 'objeto': '✅', 'justificativa': '⚠️' }, 'resumo': 'texto estruturado' }"
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        conteudo = resp.choices[0].message.content.strip()
        try:
            return json.loads(conteudo)
        except:
            # fallback: mostra texto cru se não for JSON
            return {"resumo": conteudo, "insumos": {}}
    except Exception as e:
        return {"resumo": f"⚠️ Erro ao consultar modelo: {e}", "insumos": {}}

def render_resumo(resumo):
    """Renderiza o campo 'resumo' do JSON como texto amigável"""
    if not resumo:
        return
    
    st.markdown("### 📄 Resumo")
    
    if isinstance(resumo, dict):
        for chave, valor in resumo.items():
            if isinstance(valor, dict):
                st.markdown(f"**{chave.capitalize()}:**")
                for subk, subv in valor.items():
                    st.markdown(f"- {subk.capitalize()}: {subv}")
            else:
                st.markdown(f"- **{chave.capitalize()}**: {valor}")
    else:
        st.markdown(resumo)

def render_insumos(insumos: Dict):
    """Renderiza insumos como tabela colorida"""
    if not insumos:
        return
    st.markdown("### 📌 Status dos Insumos")
    for chave, valor in insumos.items():
        if valor == "✅":
            cor = "green"
        elif valor == "⚠️":
            cor = "orange"
        elif valor == "❌":
            cor = "red"
        else:
            cor = "gray"
        st.markdown(f"- **{chave.capitalize()}**: <span style='color:{cor}; font-weight:bold'>{valor}</span>", unsafe_allow_html=True)

# -------------------------------------------------
# ESTADO DO CHAT
# -------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_stage" not in st.session_state:
    st.session_state.current_stage = "PCA"
if "artefatos" not in st.session_state:
    st.session_state.artefatos = {}
if "log_normativo" not in st.session_state:
    st.session_state.log_normativo = []

# Mensagem inicial
if not st.session_state.messages:
    st.session_state.messages.append({
        "role": "assistant",
        "content": (
            "Olá! Sou o **Agente Orquestrador** do Synapse.IA. "
            "Antes de iniciar, precisamos verificar se a contratação está no **Plano de Contratações Anual (PCA)**. "
            "Deseja começar pelo PCA?"
        )
    })

# Render histórico
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Entrada do usuário
user_input = st.chat_input("Descreva seu pedido ou responda às perguntas do agente...")

if user_input:
    # salvar entrada
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # chamar agente
    stage = st.session_state.current_stage
    resposta = call_agent(stage, user_input, st.session_state.messages)

    # salvar e mostrar resultado
    if "resumo" in resposta:
        st.session_state.artefatos[stage] = resposta
        st.session_state.messages.append({"role": "assistant", "content": str(resposta["resumo"])})
        with st.chat_message("assistant"):
            render_resumo(resposta.get("resumo"))
            render_insumos(resposta.get("insumos", {}))

        # log normativo
        st.session_state.log_normativo.append({
            "etapa": stage,
            "entrada": user_input,
            "saida": resposta
        })

        # sugerir próxima etapa
        prox = proximo_artefato(stage)
        if prox:
            st.session_state.current_stage = prox
            sugestao = f"{progresso(stage)}\n\n👉 Próximo passo sugerido: **{prox}**. Deseja avançar?"
            st.session_state.messages.append({"role": "assistant", "content": sugestao})
            with st.chat_message("assistant"):
                st.markdown(sugestao)
