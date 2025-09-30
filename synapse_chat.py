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
st.caption(
    "Chat único com **Agente Orquestrador** e **Agentes Especializados** "
    "(PCA, DFD, ETP, Pesquisa de Preços, ITF, Mapa de Riscos, TR, Parecer Jurídico, Edital, Contrato, Fiscalização, Checklist)."
)

# -------------------------------------------------
# SEGREDO (CHAVE)
# -------------------------------------------------
if "openai_api_key" not in st.secrets:
    st.warning("⚠️ Adicione a chave da OpenAI em **Settings → Secrets** do Streamlit Cloud")
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

# Ordem oficial dos agentes (fase preparatória completa)
AGENT_ORDER = [
    "PCA",
    "DFD",
    "ETP",
    "PESQUISA_PRECOS",
    "ITF",
    "MAPA_RISCOS",
    "TR",
    "PARECER_JURIDICO",
    "EDITAL",
    "CONTRATO",
    "FISCALIZACAO",
    "CHECKLIST"
]

# -------------------------------------------------
# FUNÇÕES AUXILIARES
# -------------------------------------------------
def progresso() -> str:
    marcadores = []
    for s in AGENT_ORDER:
        marcadores.append(f"[{'X' if st.session_state.artefatos.get(s) else ' '}] {s}")
    return "📊 Progresso atual: " + " ".join(marcadores)

def proximo_artefato(stage: str) -> str:
    try:
        idx = AGENT_ORDER.index(stage)
        return AGENT_ORDER[idx + 1] if idx + 1 < len(AGENT_ORDER) else None
    except ValueError:
        return None

def _insumo_emoji(v: str) -> str:
    v = (v or "").strip()
    if "✅" in v: return "✅"
    if "⚠️" in v or "⚠" in v: return "⚠️"
    if "❌" in v or "✖" in v: return "❌"
    return "•"

def _render_insumos(insumos: Dict[str,str]):
    if not insumos: 
        return
    st.markdown("### 📌 Status dos Insumos")
    for k, v in insumos.items():
        st.markdown(f"- **{k.capitalize()}**: {_insumo_emoji(v)}")

def _download_doc(stage: str, conteudo: str):
    if not conteudo:
        return
    nome = f"{stage}_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    st.download_button(
        label="⬇️ Baixar documento (.md)",
        data=conteudo,
        file_name=nome,
        mime="text/markdown"
    )

def call_agent(stage: str, user_text: str, history: List[Dict]) -> Dict:
    """
    Chama agente especializado e exige retorno JSON com:
    {
      "titulo": str,
      "insumos": {k: "✅/⚠️/❌", ...},
      "artefato": str,    # documento integral (Markdown)
      "resumo": str,      # resumo curto
      "proximos_passos": [ ... ],
      "perguntas_faltantes": [ ... ]
    }
    """
    system_prompt = load_prompt(stage) + "\n\n"
    system_prompt += (
        "=== Diretrizes Globais do Orquestrador ===\n"
        "1) Gere o **ARTEFATO COMPLETO** (documento integral), em **Markdown** com seções numeradas.\n"
        "2) Se faltar insumo essencial, liste perguntas em `perguntas_faltantes` ANTES de concluir o artefato.\n"
        "3) Classifique os insumos em ✅/⚠️/❌ em `insumos`.\n"
        "4) Fundamente nas normas aplicáveis: " + ", ".join(NORMAS_BASE) + ".\n"
        "5) Responda **EXCLUSIVAMENTE** em **JSON válido** (UTF-8, aspas duplas), sem texto fora do JSON, sem blocos ```.\n"
    )

    # últimas trocas dão contexto
    ctx = [f"{m['role']}: {m['content']}" for m in history[-4:]]
    context_block = "\n".join(ctx) if ctx else "Sem histórico relevante."

    # schema explícito para reduzir erro de parsing
    schema = (
        '{\n'
        '  "titulo": "string",\n'
        '  "insumos": {"objeto":"✅","justificativa":"⚠️"},\n'
        '  "artefato": "documento completo em Markdown; use \\n para quebras",\n'
        '  "resumo": "síntese em 3-6 linhas",\n'
        '  "proximos_passos": ["ETP"],\n'
        '  "perguntas_faltantes": []\n'
        '}'
    )

    user_prompt = (
        f"Etapa atual: {stage}\n"
        f"Contexto recente:\n{context_block}\n\n"
        f"Insumos do usuário:\n{user_text}\n\n"
        "Formato de saída obrigatório (JSON válido, use aspas duplas e escape \\n):\n"
        + schema
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=2200
        )
        conteudo = resp.choices[0].message.content.strip()
        return json.loads(conteudo)
    except Exception as e:
        return {"erro": f"Falha ao gerar artefato ({stage}): {e}"}

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
    # 1) salvar entrada do usuário
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    # 2) chamar agente atual
    stage = st.session_state.current_stage
    resposta = call_agent(stage, user_input, st.session_state.messages)

    # 3) exibir/armazenar
    with st.chat_message("assistant"):
        if "erro" in resposta:
            st.error(resposta["erro"])
        else:
            titulo = resposta.get("titulo") or f"Documento — {stage}"
            artefato = resposta.get("artefato", "").strip()
            resumo = resposta.get("resumo", "").strip()
            insumos = resposta.get("insumos", {})
            perguntas = resposta.get("perguntas_faltantes", []) or []
            proxs = resposta.get("proximos_passos", [])

            # documento integral
            st.markdown(f"## 📄 {titulo}")
            if artefato:
                st.markdown(artefato)
                _download_doc(stage, artefato)
            else:
                st.warning("O agente não retornou o campo **artefato**. Verifique o prompt do agente e o schema.")

            # status de insumos
            _render_insumos(insumos)

            # perguntas faltantes (se houver)
            if perguntas:
                st.markdown("### ❔ Informações faltantes")
                for p in perguntas:
                    st.markdown(f"- {p}")

            # resumo curto
            if resumo:
                with st.expander("Resumo do agente"):
                    st.markdown(resumo)

            # persistência
            st.session_state.artefatos[stage] = resposta
            st.session_state.log_normativo.append({
                "etapa": stage, "entrada": user_input, "saida": resposta
            })

            # 4) sugerir próximo passo
            prox = proxs[0] if isinstance(proxs, list) and proxs else proximo_artefato(stage)
            if prox:
                st.session_state.current_stage = prox
                st.markdown("---")
                st.markdown(progresso())
                st.markdown(f"👉 **Próximo passo sugerido: {prox}**. Deseja avançar?")
