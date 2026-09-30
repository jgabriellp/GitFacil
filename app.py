"""
Git Fácil — tela do aplicativo (Streamlit).

Para rodar:  streamlit run app.py
"""

import os
import threading
from pathlib import Path

import streamlit as st
from dotenv import dotenv_values, set_key

import git_ops
from git_ops import Config

PASTA_APP = Path(__file__).parent
ARQUIVO_CONFIG = PASTA_APP / "config.env"
PASTA_PADRAO = Path.home() / "Documents" / "Projetos"

st.set_page_config(page_title="Git Fácil", page_icon="📁", layout="centered")


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

def carregar_config() -> Config:
    valores = dotenv_values(ARQUIVO_CONFIG) if ARQUIVO_CONFIG.exists() else {}
    return Config(
        pasta_projetos=Path(valores.get("PASTA_PROJETOS") or PASTA_PADRAO).expanduser(),
        nome=valores.get("NOME") or "",
        email=valores.get("EMAIL") or "",
        token_usuario=valores.get("TOKEN_USUARIO") or "",
        token=valores.get("TOKEN") or "",
    )


def salvar_config(**valores: str) -> None:
    ARQUIVO_CONFIG.touch(exist_ok=True)
    for chave, valor in valores.items():
        set_key(str(ARQUIVO_CONFIG), chave, valor, quote_mode="always")


def mostrar_resultado(resultado: git_ops.Resultado) -> None:
    if resultado.ok:
        st.success(resultado.mensagem, icon="✅")
    else:
        st.error(resultado.mensagem, icon="⚠️")
    if resultado.detalhes:
        with st.expander("Detalhes técnicos"):
            st.code(resultado.detalhes, language=None)


cfg = carregar_config()

st.title("📁 Git Fácil")


# ---------------------------------------------------------------------------
# Primeira vez: pede nome e e-mail
# ---------------------------------------------------------------------------

if not cfg.nome or not cfg.email:
    st.subheader("Bem-vindo! Antes de começar:")
    st.write("Seu nome e e-mail aparecem no histórico, mostrando quem fez cada alteração. "
             "Você só precisa preencher isso uma vez.")
    with st.form("primeiro_acesso"):
        nome = st.text_input("Seu nome")
        email = st.text_input("Seu e-mail")
        if st.form_submit_button("Salvar e começar", type="primary"):
            if nome.strip() and "@" in email:
                salvar_config(NOME=nome.strip(), EMAIL=email.strip())
                st.rerun()
            else:
                st.error("Preencha o nome e um e-mail válido.")
    st.stop()


# ---------------------------------------------------------------------------
# Barra lateral: configurações
# ---------------------------------------------------------------------------

with st.sidebar:
    st.write(f"👤 **{cfg.nome}**  \n{cfg.email}")
    st.caption(f"Pasta dos projetos:  \n`{cfg.pasta_projetos}`")
    with st.expander("⚙️ Configurações"):
        with st.form("config"):
            nome = st.text_input("Nome", cfg.nome)
            email = st.text_input("E-mail", cfg.email)
            pasta = st.text_input("Pasta dos projetos", str(cfg.pasta_projetos))
            if st.form_submit_button("Salvar"):
                salvar_config(NOME=nome.strip(), EMAIL=email.strip(), PASTA_PROJETOS=pasta.strip())
                st.rerun()
    st.divider()
    fechar = st.button("🚪 Fechar o Git Fácil", use_container_width=True)

if fechar:
    st.success("O Git Fácil foi fechado. Pode fechar esta aba do navegador.", icon="👋")
    # Espera um pouco para a mensagem chegar ao navegador antes de encerrar.
    # Ao encerrar, o iniciar.bat termina e a janela preta fecha sozinha.
    threading.Timer(1.5, os._exit, args=(0,)).start()
    st.stop()


# ---------------------------------------------------------------------------
# Tela principal
# ---------------------------------------------------------------------------

acao = st.radio(
    "O que você quer fazer?",
    ["📥 Baixar um projeto", "🔄 Atualizar meu projeto", "📤 Enviar minhas alterações"],
    horizontal=True,
)
st.divider()

# Resultado da última ação (mostrado no topo, depois que a tela recarrega)
if "resultado" in st.session_state:
    ultimo = st.session_state.pop("resultado")
    mostrar_resultado(ultimo)
    if ultimo.ok and st.session_state.pop("comemorar", False):
        st.balloons()


def executar(funcao, *args, espera: str, comemorar: bool = False) -> None:
    with st.spinner(espera):
        st.session_state["resultado"] = funcao(cfg, *args)
    st.session_state["comemorar"] = comemorar
    st.rerun()

projetos = git_ops.listar_projetos(cfg)


# --- Baixar (clone) -------------------------------------------------------

if acao.startswith("📥"):
    st.write("Cole o endereço do projeto. Ele fica no botão **Code** (GitHub) "
             "ou **Clonar** (GitLab), na página do repositório.")
    url = st.text_input("Endereço do projeto", placeholder="https://github.com/empresa/projeto.git")
    if st.button("Baixar", type="primary", disabled=not url.strip()):
        executar(git_ops.baixar, url, espera="Baixando o projeto...")


# --- Atualizar (pull) -----------------------------------------------------

elif acao.startswith("🔄"):
    if not projetos:
        st.info("Você ainda não tem projetos. Comece por **Baixar um projeto**.")
    else:
        projeto = st.selectbox("Qual projeto?", projetos)
        st.write("Isso traz para o seu computador as alterações feitas pela equipe.")
        if st.button("Atualizar", type="primary"):
            executar(git_ops.atualizar, projeto, espera="Buscando novidades...")


# --- Enviar (add + commit + pull + push) ----------------------------------

else:
    if not projetos:
        st.info("Você ainda não tem projetos. Comece por **Baixar um projeto**.")
    else:
        projeto = st.selectbox("Qual projeto?", projetos)
        with st.spinner("Procurando arquivos alterados..."):
            alteracoes = git_ops.ver_alteracoes(cfg, projeto)

        if not alteracoes:
            st.info("Nenhum arquivo foi alterado neste projeto.")
        else:
            st.write(f"**{len(alteracoes)} arquivo(s) serão enviados:**")
            # Lista simples em vez de st.dataframe: aparece na hora no navegador.
            # Com muitos arquivos, a caixa ganha barra de rolagem.
            with st.container(height=250 if len(alteracoes) > 8 else "content", border=True):
                st.markdown("\n".join(f"- **{a.tipo}:** `{a.arquivo}`" for a in alteracoes))

            sensiveis = git_ops.arquivos_sensiveis(alteracoes)
            confirmou_sensiveis = True
            if sensiveis:
                st.warning(
                    "Atenção: estes arquivos parecem conter senhas ou chaves e "
                    "normalmente **não devem** ser enviados:\n\n"
                    + "\n".join(f"- `{s}`" for s in sensiveis),
                    icon="🔒",
                )
                confirmou_sensiveis = st.checkbox("Tenho certeza, quero enviar mesmo assim")

            mensagem = st.text_input(
                "O que você alterou?", placeholder="Ex.: Atualizei a planilha de preços",
            )
            pode_enviar = bool(mensagem.strip()) and confirmou_sensiveis
            if st.button("Enviar", type="primary", disabled=not pode_enviar):
                executar(git_ops.enviar, projeto, mensagem,
                         espera="Enviando suas alterações...", comemorar=True)
