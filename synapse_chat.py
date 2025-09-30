import os
import json
import streamlit as st
from openai import OpenAI

# Inicializa o cliente OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Função para carregar os prompts de cada agente
def load_prompt(agent_name):
    try:
        with open(f"prompts/{agent_name}.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data["prompt"]
    except FileNotFoundError:
        return f"⚠️ Prompt do agente {agent_name} não encontrado."

# Função que envia mensagem ao modelo
def run_agent(agent_name, insumos):
    prompt_base = load_prompt(agent_name)

    # Monta entrada
    user_message = f"Insumos fornecidos:\n{insumos}\n\nElabore o documento conforme instruções do agente {agent_name}."

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt_base},
            {"role": "user", "content": user_message}
        ],
        temperature=0.4,
        max_tokens=1800
    )

    return response.choices[0].message.content

# Interface do Streamlit
st.set_page_config(page_title="Synapse.IA - Orquestrador", layout="wide")

st.title("🧠 Synapse.IA – Prova de Conceito (POC)")

# Entrada dos insumos iniciais
st.subheader("📥 Insumos")
insumos = st.text_area("Descreva o objeto, justificativa, requisitos, prazos, critérios etc.", height=200)

# Seleção do agente
st.subheader("🤖 Selecionar Agente")
agent_list = [
    "PCA", "DFD", "ETP", "PESQUISA_PRECOS", "TR", "CONTRATO",
    "FISCALIZACAO", "CHECKLIST", "PARECER_JURIDICO", "MAPA_RISCOS", "EDITAL"
]
agent_name = st.selectbox("Escolha o agente:", agent_list)

# Botão de execução
if st.button("▶️ Executar Agente"):
    if not insumos.strip():
        st.warning("⚠️ Por favor, insira os insumos antes de executar.")
    else:
        with st.spinner("Gerando documento..."):
            result = run_agent(agent_name, insumos)

        st.subheader("📄 Saída do Agente")

        # Para CHECKLIST mantém formato especial
        if agent_name == "CHECKLIST":
            st.markdown(result)
        else:
            # Para todos os outros agentes, retorna o documento completo
            st.text_area("Documento Gerado:", value=result, height=600)
