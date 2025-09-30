import re
import os
import json
import streamlit as st
from typing import List, Dict, Any

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
    st.warning("Adicione a chave da OpenAI em **Settings → Secrets** do Streamlit Cloud.")
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

# Ordem oficial
AGENT_ORDER = ["PCA", "DFD", "ETP", "TR", "CONTRATO", "FISCALIZACAO", "CHECKLIST"]

# -------------------------------------------------
# CLASSIFICAÇÃO DE CONTRATAÇÃO
# -------------------------------------------------
def detect_tipo(texto: str) -> str:
    low = texto.lower()
    if re.search(r"\b(obra|engenharia|reforma|constru[çc][aã]o|execu[cç][aã]o)\b", low):
        return "obra"
    if re.search(r"\b(servi[cç]o|manuten[cç][aã]o|limpeza|vigil[âa]ncia|suporte|gest[aã]o|capacita[cç][aã]o)\b", low):
        return "servico"
    if re.search(r"\b(aquisi[cç][aã]o|compra|fornecimento|material|equipamento|computador|notebook|licen[cç]a)\b", low):
        return "produto"
    return "indefinido"

# -------------------------------------------------
# PARSER RESILIENTE
# -------------------------------------------------
def extract_json(text: str) -> Dict[str, Any] | None:
    if not text:
        return None
    s = text.strip()
    if s.startswith("```"):
        nl = s.find("\n")
        if nl != -1:
            s = s[nl+1:]
        if s.endswith("```"):
            s = s[:-3]
    start, end = s.find("{"), s.rfind("}")
    if start == -1 or end == -1:
        return None
    candidate = s[start:end+1].strip()
    try:
        return json.loads(candidate)
    except:
        candidate = re.sub(r"(?<!\\)'", '"', candidate)
        try:
            return json.loads(candidate)
        except:
            return None

# -------------------------------------------------
# RENDERIZAÇÃO
# -------------------------------------------------
def render_dict_as_md(d: Dict[str, Any], level: int = 0):
    indent = "  " * level
    for k, v in d.items():
        title = k.replace("_", " ").capitalize()
        if isinstance(v, dict):
            st.markdown(f"{indent}- **{title}:**")
            render_dict_as_md(v, level + 1)
        elif isinstance(v, list):
            st.markdown(f"{indent}- **{title}:**")
            for item in v:
                if isinstance(item, dict):
                    render_dict_as_md(item, level + 2)
                else:
                    st.markdown(f"{indent}  - {item}")
        else:
            st.markdown(f"{indent}- **{title}:** {v}")

def render_resumo(resumo: Any):
    if not resumo:
        return
    st.markdown("### 📄 Resumo")
    if isinstance(resumo, dict):
        render_dict_as_md(resumo)
    elif isinstance(resumo, list):
        for item in resumo:
            st.markdown(f"- {item}")
    else:
        st.markdown(str(resumo))

def render_insumos(insumos: Dict[str, str]):
    if not insumos:
        return
    st.markdown("### 📌 Status dos Insumos")
    for chave, valor in insumos.items():
        cor = "green" if valor == "✅" else "orange" if valor == "⚠️" else "red" if valor == "❌" else "gray"
        st.markdown(
            f"- **{chave.replace('_',' ').capitalize()}**: "
            f"<span style='color:{cor}; font-weight:bold'>{valor}</span>",
            unsafe_allow_html=True
        )

def render_proximos_passos(data: Dict[str, Any]):
    passos = data.get("proximos_passos") or data.get("próximos_passos")
    if not passos:
        return
    st.markdown("### ▶️ Próximos passos")
    if isinstance(passos, list):
        for p in passos:
            st.markdown(f"- {p}")
    else:
        st.markdown(f"- {passos}")

# -------------------------------------------------
# CALL AGENT
# -------------------------------------------------
def call_agent(stage: str, user_text: str, history: List[Dict]) -> Dict:
    tipo = detect_tipo(user_text)
    proximo_fix = {
        "PCA": "DFD", "DFD": "ETP", "ETP": "TR",
        "TR": "CONTRATO", "CONTRATO": "FISCALIZACAO",
        "FISCALIZACAO": "CHECKLIST"
    }.get(stage)

    if tipo == "servico":
        schema_resumo = (
            '"resumo": { "contexto": "...", "escopo": "...", "locais": "...", '
            '"periodicidade": "...", "vigencia": "...", "criterios_medicao": "..." }'
        )
        tipo_rules = "Tipo: SERVIÇO. Não invente quantidade; foque em escopo, locais, periodicidade, vigência."
    elif tipo == "produto":
        schema_resumo = (
            '"resumo": { "contexto": "...", "detalhes": { "quantidade": null, "especificacoes": { "modelo": "...", "caracteristicas": "..." } } }'
        )
        tipo_rules = "Tipo: PRODUTO. Use quantidade/especificações se fornecidas; não invente valores."
    else:
        schema_resumo = (
            '"resumo": { "contexto": "...", "escopo": "...", "local": "...", "prazo_execucao": "...", "criterios_medicao": "..." }'
        )
        tipo_rules = "Tipo: OBRA/INDEFINIDO. Foque em escopo, local, prazo de execução."

    etapa_rules = f"Etapa atual: {stage}. O próximo passo deve ser {proximo_fix}."

    system_prompt = load_prompt(stage) + "\n\n"
    system_prompt += (
        "1) Seja claro e institucional.\n"
        "2) Classifique insumos em ✅ ⚠️ ❌.\n"
        f"3) Fundamente nas normas: {', '.join(NORMAS_BASE)}.\n"
        "IMPORTANTE: responda apenas JSON válido (UTF-8, aspas duplas), sem crases/markdown.\n"
        "NUNCA invente valores padrão (ex.: quantidade: 1)."
    )

    ctx = [f"{m['role']}: {m['content']}" for m in history[-4:]]
    user_prompt = (
        f"{etapa_rules}\n{tipo_rules}\n\n"
        f"Contexto:\n{''.join(ctx)}\n\n"
        f"Entrada:\n{user_text}\n\n"
        "Formato rigoroso de saída (JSON puro):\n"
        "{\n"
        '  "insumos": { "objeto": "✅", "justificativa": "⚠️" },\n'
        f"  {schema_resumo},\n"
        f'  "proximos_passos": ["{proximo_fix}", "..."]\n'
        "}"
    )

    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
            temperature=0.2,
            max_tokens=1100
        )
        conteudo = resp.choices[0].message.content.strip()
        data = extract_json(conteudo) or {"resumo": conteudo, "insumos": {}}

        if proximo_fix and (not data.get("proximos_passos")):
            data["proximos_passos"] = [proximo_fix]

        return data
    except Exception as e:
        return {"resumo": f"⚠️ Erro: {e}", "insumos": {}}

# -------------------------------------------------
# ESTADO DO CHAT
# -------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
if "current_stage" not in st.session_state:
    st.session_state.current_stage = "PCA"
if "artefatos" not in st.session_state:
    st.session_state.artefatos = {}

# Mensagem inicial
if not st.session_state.messages:
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Olá! Sou o Agente Orquestrador. Vamos começar verificando o **Plano de Contratações Anual (PCA)**. Deseja iniciar por ele?"
    })

# Render histórico
for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

# Entrada
user_input = st.chat_input("Descreva seu pedido ou responda às perguntas do agente...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    stage = st.session_state.current_stage
    resposta = call_agent(stage, user_input, st.session_state.messages)

    resumo = resposta.get("resumo")
    insumos = resposta.get("insumos", {})

    st.session_state.artefatos[stage] = resposta
    st.session_state.messages.append({"role": "assistant", "content": f"Resumo gerado na etapa {stage}."})

    with st.chat_message("assistant"):
        render_resumo(resumo)
        render_insumos(insumos)
        render_proximos_passos(resposta)

    prox = {"PCA": "DFD", "DFD": "ETP", "ETP": "TR", "TR": "CONTRATO", "CONTRATO": "FISCALIZACAO", "FISCALIZACAO": "CHECKLIST"}.get(stage)
    if prox:
        st.session_state.current_stage = prox
        with st.chat_message("assistant"):
            st.markdown(f"{' '.join(['[X] '+s if s in st.session_state.artefatos else '[ ] '+s for s in AGENT_ORDER])}\n\n👉 Próximo passo: **{prox}**. Deseja avançar?")
