import hashlib
import os
import gspread
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
import streamlit as st

# 1. Configuração única da página
st.set_page_config(page_title="Copiloto Gupy", page_icon="🎯", layout="wide")


# --- FUNÇÕES DE SEGURANÇA E BANCO (GOOGLE SHEETS) ---
def gerar_hash(senha: str) -> str:
  return hashlib.sha256(senha.encode()).hexdigest()


@st.cache_resource
def conectar_planilha():
  credenciais = dict(st.secrets["gcp_service_account"])
  gc = gspread.service_account_from_dict(credenciais)
  return gc.open("Clientes_Aderencia").sheet1


def buscar_usuario(sheet, email: str):
  registros = sheet.get_all_records()
  for idx, row in enumerate(
      registros, start=2
  ): # Linha 1 é o cabeçalho da planilha
    if str(row["email"]).strip().lower() == email.strip().lower():
      return idx, row
  return None, None


# --- CONTROLE DE SESSÃO ---
if "logado" not in st.session_state:
  st.session_state["logado"] = False

# --- TELA DE LOGIN / CADASTRO (ANTES DE ENTRAR NO SISTEMA) ---
if not st.session_state["logado"]:
  st.title("🎯 Copiloto de Otimização para Gupy")
  st.markdown(
      "Descubra sua aderência real às vagas e gere campos otimizados para"
      " passar nos filtros (ATS) sem inventar informações."
  )

  aba_login, aba_cadastro = st.tabs(["Entrar", "Criar Conta (3 Testes Grátis)"])

  with aba_login:
    with st.form("form_login"):
      email_login = st.text_input("E-mail")
      senha_login = st.text_input("Senha", type="password")
      btn_entrar = st.form_submit_button("Entrar", type="primary")

      if btn_entrar:
        try:
          sheet = conectar_planilha()
          linha, user = buscar_usuario(sheet, email_login)
          if user and str(user["senha"]) == gerar_hash(senha_login):
            st.session_state["logado"] = True
            st.session_state["email"] = user["email"]
            st.session_state["linha"] = linha
            st.session_state["plano"] = str(user["plano"]).strip().lower()
            st.session_state["creditos"] = int(user["creditos"])
            st.rerun()
          else:
            st.error("E-mail ou senha incorretos.")
        except Exception as e:
          st.error(f"Erro ao conectar ao banco de dados: {e}")

  with aba_cadastro:
    with st.form("form_cadastro"):
      novo_email = st.text_input("Seu melhor E-mail")
      nova_senha = st.text_input("Crie uma Senha", type="password")
      btn_cadastrar = st.form_submit_button("Criar Conta Grátis")

      if btn_cadastrar:
        if novo_email.strip() and nova_senha.strip():
          try:
            sheet = conectar_planilha()
            linha, user = buscar_usuario(sheet, novo_email)
            if user:
              st.warning("Este e-mail já está cadastrado. Acesse a aba Entrar.")
            else:
              sheet.append_row([
                  novo_email.strip().lower(),
                  gerar_hash(nova_senha),
                  "gratis",
                  3,
              ])
              st.success(
                  "Conta criada com 3 análises grátis! Faça login na aba"
                  " 'Entrar'."
              )
          except Exception as e:
            st.error(f"Erro ao cadastrar: {e}")
        else:
          st.warning("Preencha o e-mail e a senha.")

  st.stop() # Bloqueia o restante do app até o login ser concluído

# =====================================================================
# ÁREA LOGADA (SEU SISTEMA ORIGINAL INTEGRADO)
# =====================================================================


# Estrutura de saída garantida via Pydantic
class AnaliseGupy(BaseModel):
  score_aderencia: int = Field(
      description="Nota de 0 a 100 de aderência real entre currículo e vaga."
  )
  requisitos_eliminatorios: list[str] = Field(
      description=(
          "Lista de requisitos obrigatórios da vaga e status (Atende / Atenção"
          " / Não atende)."
      )
  )
  palavras_chave: list[str] = Field(
      description=(
          "Até 20 habilidades e palavras-chave exatas extraídas da vaga para"
          " marcar na Gupy."
      )
  )
  resumo_profissional: str = Field(
      description=(
          "Texto otimizado para o campo 'Apresente-se / Resumo' da Gupy (máx."
          " 600 caracteres), sem inventar fatos."
      )
  )
  experiencias_otimizadas: str = Field(
      description=(
          "Reescrita dos tópicos de experiência real do candidato incorporando"
          " as palavras-chave da vaga de forma natural."
      )
  )
  dicas_triagem: list[str] = Field(
      description=(
          "Alertas sobre perguntas eliminatórias ou pontos de destaque para"
          " entrevista."
      )
  )


# Barra lateral: Dados da conta do cliente e configuração
with st.sidebar:
  st.header("Sua Conta")
  st.write(f"👤 **{st.session_state['email']}**")
  st.write(f"🏷️ Plano: **{st.session_state['plano'].upper()}**")

  if st.session_state["plano"] == "gratis":
    st.write(f"🎟️ Análises restantes: **{st.session_state['creditos']}**")
  else:
    st.write("🎟️ Análises: **Ilimitadas**")

  if st.button("Sair da Conta", use_container_width=True):
    st.session_state["logado"] = False
    st.rerun()

  st.divider()
  st.header("Configuração")
  # Puxa automaticamente dos Secrets do Streamlit Cloud (cliente não precisa digitar)
  api_key_secret = st.secrets.get(
      "GEMINI_API_KEY", os.getenv("GEMINI_API_KEY", "")
  )
  if api_key_secret:
    api_key = api_key_secret
    st.success("Motor de IA conectado")
  else:
    api_key = st.text_input("Gemini API Key", type="password")

  modelo = st.selectbox(
      "Modelo", ["gemini-2.5-flash", "gemini-2.5-pro"], index=0
  )

# Paywall: Bloqueia se acabaram os 3 testes gratuitos
if (
    st.session_state["plano"] == "gratis"
    and st.session_state["creditos"] <= 0
):
  st.warning("⚠️ Você utilizou todas as suas 3 análises gratuitas!")
  st.subheader("🚀 Desbloqueie o Acesso Ilimitado por 30 dias")
  st.write(
      "Continue analisando vagas e gerando currículos otimizados para"
      " conquistar sua entrevista."
  )
  st.info("💰 **Valor Promocional de Lançamento:** R$ 29,90 (Pix único)")
  st.code("88841600144", language="text")
  st.markdown(
      "[📲 Enviar comprovante no WhatsApp para liberação"
      " imediata](5561991263988)"
  )
  st.stop()

st.title("🎯 Copiloto de Otimização para Gupy")
st.markdown(
    "Cole a descrição da vaga e gere os campos estruturados com base"
    " **estritamente** no seu histórico real."
)

# Colunas principais: Entrada de dados
col1, col2 = st.columns(2)

with col1:
  st.subheader("1. Seu Currículo Base (Fatos Reais)")
  curriculo_base = st.text_area(
      "Cole aqui suas experiências, formação, projetos e ferramentas reais:",
      height=320,
      placeholder=(
          "Ex: Formação em Análise e Desenvolvimento de"
          " Sistemas...\nExperiência com Python, SQL, automação...\nProjetos"
          " desenvolvidos..."
      ),
  )

with col2:
  st.subheader("2. Descrição da Vaga (Gupy)")
  descricao_vaga = st.text_area(
      "Cole aqui o texto completo da vaga (Responsabilidades + Requisitos):",
      height=320,
      placeholder="Cole todo o texto da página da vaga na Gupy...",
  )

# Botão de execução
if st.button(
    "Analisar Aderência e Gerar Campos", type="primary", use_container_width=True
):
  if not api_key:
    st.error("API Key do Gemini não configurada nos Secrets do sistema.")
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

        # Desconta 1 crédito do plano gratuito na planilha
        if st.session_state["plano"] == "gratis":
          novo_saldo = max(0, st.session_state["creditos"] - 1)
          st.session_state["creditos"] = novo_saldo
          sheet = conectar_planilha()
          sheet.update_cell(st.session_state["linha"], 4, novo_saldo)

        st.divider()
        st.subheader(f"📊 Aderência Estimada: {resultado.score_aderencia}%")
        st.progress(resultado.score_aderencia / 100)

        # Exibição dos resultados em abas organizadas
        tab1, tab2, tab3, tab4 = st.tabs([
            "📝 Resumo e Experiências (Copiar)",
            "🏷️ Habilidades (Tags)",
            "⚠️ Requisitos Eliminatórios",
            "💡 Dicas para Etapas",
        ])

        with tab1:
          st.markdown("**Campo: Apresente-se / Resumo Profissional**")
          st.code(resultado.resumo_profissional, language="text")
          st.markdown("**Campo: Experiências Otimizadas**")
          st.code(resultado.experiencias_otimizadas, language="text")

        import hashlib
import os
import gspread
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
import streamlit as st

# 1. Configuração única da página
st.set_page_config(page_title="Copiloto Gupy", page_icon="🎯", layout="wide")


# --- FUNÇÕES DE SEGURANÇA E BANCO (GOOGLE SHEETS) ---
def gerar_hash(senha: str) -> str:
  return hashlib.sha256(senha.encode()).hexdigest()


