import os
import streamlit as st
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

# Configuração da página
st.set_page_config(page_title="Copiloto Gupy", page_icon="🎯", layout="wide")

# Estrutura de saída garantida via Pydantic
class AnaliseGupy(BaseModel):
    score_aderencia: int = Field(description="Nota de 0 a 100 de aderência real entre currículo e vaga.")
    requisitos_eliminatorios: list[str] = Field(description="Lista de requisitos obrigatórios da vaga e status (Atende / Atenção / Não atende).")
    palavras_chave: list[str] = Field(description="Até 20 habilidades e palavras-chave exatas extraídas da vaga para marcar na Gupy.")
    resumo_profissional: str = Field(description="Texto otimizado para o campo 'Apresente-se / Resumo' da Gupy (máx. 600 caracteres), sem inventar fatos.")
    experiencias_otimizadas: str = Field(description="Reescrita dos tópicos de experiência real do candidato incorporando as palavras-chave da vaga de forma natural.")
    dicas_triagem: list[str] = Field(description="Alertas sobre perguntas eliminatórias ou pontos de destaque para entrevista.")

st.title("🎯 Copiloto de Otimização para Gupy")
st.markdown("Cole a descrição da vaga e gere os campos estruturados com base **estritamente** no seu histórico real.")

# Barra lateral para configuração da API Key
with st.sidebar:
    st.header("Configuração")
    api_key = st.text_input("Gemini API Key", type="password", value=os.getenv("GEMINI_API_KEY", ""))
    st.caption("Obtenha sua chave gratuitamente no Google AI Studio.")
    modelo = st.selectbox("Modelo", ["gemini-3.5-flash", "gemini-3.5-pro"], index=0)

# Colunas principais: Entrada de dados
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Seu Currículo Base (Fatos Reais)")
    curriculo_base = st.text_area(
        "Cole aqui suas experiências, formação, projetos e ferramentas reais:",
        height=320,
        placeholder="Ex: Formação em Análise e Desenvolvimento de Sistemas...\nExperiência com Python, SQL, automação...\nProjetos desenvolvidos..."
    )

with col2:
    st.subheader("2. Descrição da Vaga (Gupy)")
    descricao_vaga = st.text_area(
        "Cole aqui o texto completo da vaga (Responsabilidades + Requisitos):",
        height=320,
        placeholder="Cole todo o texto da página da vaga na Gupy..."
    )

# Botão de execução
if st.button("Analisar Aderência e Gerar Campos", type="primary", use_container_width=True):
    if not api_key:
        st.error("Insira sua Gemini API Key na barra lateral.")
    elif not curriculo_base.strip() or not descricao_vaga.strip():
        st.warning("Preencha tanto o seu currículo base quanto a descrição da vaga.")
    else:
        with st.spinner("Analisando requisitos e otimizando textos..."):
            try:
                client = genai.Client(api_key=api_key)
                
                prompt = f"""
                Você é um especialista em recrutamento e algoritmos de triagem semântica (ATS/Gupy).
                Analise o CURRÍCULO BASE do candidato em relação à DESCRIÇÃO DA VAGA.

                REGRAS ESTRITAS:
                1. NUNCA invente experiências, cargos, diplomas ou ferramentas que não estejam no currículo base.
                2. Adapte apenas o vocabulário e a ênfase para refletir os termos exatos da vaga onde houver correspondência real.
                3. Mantenha tom profissional, direto e humano (evite clichês genéricos de IA como 'apaixonado por desafios' ou 'profissional dinâmico').

                CURRÍCULO BASE:
                {curriculo_base}

                DESCRIÇÃO DA VAGA:
                {descricao_vaga}
                """

                response = client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=AnaliseGupy,
                        temperature=0.2,
                    ),
                )

                resultado = AnaliseGupy.model_validate_json(response.text)

                st.divider()
                st.subheader(f"📊 Aderência Estimada: {resultado.score_aderencia}%")
                st.progress(resultado.score_aderencia / 100)

                # Exibição dos resultados em abas organizadas
                tab1, tab2, tab3, tab4 = st.tabs([
                    "📝 Resumo e Experiências (Copiar)", 
                    "🏷️ Habilidades (Tags)", 
                    "⚠️ Requisitos Eliminatórios", 
                    "💡 Dicas para Etapas"
                ])

                with tab1:
                    st.markdown("**Campo: Apresente-se / Resumo Profissional**")
                    st.code(resultado.resumo_profissional, language="text")
                    
                    st.markdown("**Campo: Experiências Profissionais (Tópicos Otimizados)**")
                    st.code(resultado.experiencias_otimizadas, language="markdown")

                with tab2:
                    st.markdown("**Marque estas habilidades no cadastro da Gupy (se você as possuir):**")
                    st.write(", ".join([f"`{kw}`" for kw in resultado.palavras_chave]))

                with tab3:
                    for req in resultado.requisitos_eliminatorios:
                        st.markdown(f"- {req}")

                with tab4:
                    for dica in resultado.dicas_triagem:
                        st.info(dica)

            except Exception as e:
                st.error(f"Erro ao processar análise: {e}")


