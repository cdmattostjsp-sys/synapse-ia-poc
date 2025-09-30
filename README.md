# 🧠 Synapse.IA — POC TJSP

Prova de conceito de **Agente Orquestrador** com **Agentes Especializados** para apoiar a elaboração de artefatos de contratação pública no TJSP, de acordo com a **Lei 14.133/2021 (Nova Lei de Licitações e Contratos)**.

## 🚀 Objetivo

- Centralizar em um único chat a interação com diferentes agentes especializados (PCA, DFD, ETP, TR, Contrato, Fiscalização, Checklist).
- Guiar o usuário passo a passo no fluxo de contratação, sugerindo a próxima etapa automaticamente.
- Validar insumos obrigatórios de cada artefato, classificando-os como:
  - ✅ Pronto  
  - ⚠️ Parcial  
  - ❌ Pendente  
- Fundamentar cada etapa nas normas aplicáveis (Lei 14.133/2021, Decreto Estadual 67.381/2022, etc.).

---

## 📦 Estrutura do Projeto


---

## ⚙️ Instalação

Clone o repositório e instale as dependências:

```bash
git clone https://github.com/seu-usuario/synapse-ia-poc.git
cd synapse-ia-poc
pip install -r requirements.txt
Settings → Secrets → openai_api_key = "sua-chave"
export OPENAI_API_KEY="sua-chave"
streamlit run synapse_chat.py
Fluxo de Artefatos

O orquestrador guia automaticamente pelo fluxo:

PCA → Verificação no Plano de Contratações Anual

DFD → Documento de Formalização da Demanda

ETP → Estudo Técnico Preliminar

TR → Termo de Referência

CONTRATO → Minuta Contratual

FISCALIZAÇÃO → Plano de Gestão e Fiscalização

CHECKLIST → Validação de conformidade normativa
