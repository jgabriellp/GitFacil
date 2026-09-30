"""
Operações Git do Git Fácil.

Toda a lógica do Git fica aqui, separada da tela (app.py). Assim, no futuro,
dá para criar outro modo (por exemplo, servidor com upload) reaproveitando
estas mesmas funções.

Cada função devolve um Resultado com:
  - ok: se deu certo
  - mensagem: texto simples para o usuário final
  - detalhes: saída técnica do Git (para quem for dar suporte)
"""

from __future__ import annotations

import base64
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from git import GitCommandError, InvalidGitRepositoryError, Repo


# ---------------------------------------------------------------------------
# Estruturas de retorno
# ---------------------------------------------------------------------------

@dataclass
class Resultado:
    ok: bool
    mensagem: str
    detalhes: str = ""


@dataclass
class Alteracao:
    tipo: str      # "Novo", "Alterado", "Apagado", "Renomeado"
    arquivo: str


@dataclass
class Config:
    pasta_projetos: Path
    nome: str = ""
    email: str = ""
    token_usuario: str = ""   # GitHub: qualquer texto (ex.: "x-access-token"); GitLab: "oauth2"
    token: str = ""           # Token pessoal (opcional). Sem token, usa o login salvo no Windows.
    extras: dict = field(default_factory=dict)


# Arquivos que quase nunca devem ser enviados (senhas, chaves etc.)
PADROES_SENSIVEIS = [
    r"(^|/)\.env$", r"(^|/)\.env\.", r"\.pem$", r"\.key$", r"\.pfx$", r"\.p12$",
    r"(^|/)id_rsa", r"(^|/)id_ed25519", r"senha", r"password", r"credenciais",
]


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------

def _ambiente_git(cfg: Config) -> dict:
    """
    Variáveis de ambiente passadas para o Git em cada comando.

    Se houver token, ele é enviado como cabeçalho HTTP apenas durante o
    comando. Ele NÃO fica gravado dentro do projeto (.git/config).
    """
    env = {
        "GIT_TERMINAL_PROMPT": "0",  # nunca travar esperando senha no terminal
    }
    if cfg.token:
        usuario = cfg.token_usuario or "x-access-token"
        credencial = base64.b64encode(f"{usuario}:{cfg.token}".encode()).decode()
        env.update({
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.extraHeader",
            "GIT_CONFIG_VALUE_0": f"Authorization: Basic {credencial}",
        })
    return env


def _abrir(cfg: Config, projeto: str) -> Repo:
    repo = Repo(cfg.pasta_projetos / projeto)
    repo.git.update_environment(**_ambiente_git(cfg))
    return repo


# ---------------------------------------------------------------------------
# Tradução de erros técnicos para linguagem simples
# ---------------------------------------------------------------------------

def _traduzir_erro(erro: Exception) -> str:
    texto = str(erro).lower()
    if any(p in texto for p in ("authentication failed", "could not read username",
                                "403", "401", "permission denied", "access denied",
                                "terminal prompts disabled")):
        return ("Não foi possível acessar o repositório. Confira se o endereço está "
                "correto e se você tem permissão nele. Se continuar, peça ao "
                "responsável para conferir o token de acesso.")
    if any(p in texto for p in ("could not resolve host", "failed to connect",
                                "timed out", "network is unreachable")):
        return "Sem conexão com o servidor. Verifique sua internet e tente de novo."
    if any(p in texto for p in ("repository not found", "not found", "does not exist",
                                "does not appear to be a git repository")):
        return "Repositório não encontrado. Confira se o endereço está correto."
    if "conflict" in texto or "could not apply" in texto:
        return ("Outra pessoa alterou os mesmos arquivos que você. Suas alterações "
                "estão salvas no seu computador, mas não foram enviadas. "
                "Fale com o responsável pelo projeto.")
    if "rejected" in texto or "non-fast-forward" in texto:
        return ("O servidor recusou o envio porque há alterações mais novas lá. "
                "Clique em \"Atualizar meu projeto\" e tente enviar de novo.")
    return "Algo deu errado. Abra \"Detalhes técnicos\" e envie o texto ao responsável."


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------

def listar_projetos(cfg: Config) -> list[str]:
    pasta = cfg.pasta_projetos
    if not pasta.exists():
        return []
    projetos = []
    for item in sorted(pasta.iterdir(), key=lambda p: p.name.lower()):
        if item.is_dir() and (item / ".git").exists():
            projetos.append(item.name)
    return projetos


def ver_alteracoes(cfg: Config, projeto: str) -> list[Alteracao]:
    repo = _abrir(cfg, projeto)
    saida = repo.git.status("--porcelain=v1", "-uall")
    alteracoes = []
    for linha in saida.splitlines():
        if not linha.strip():
            continue
        codigo, caminho = linha[:2], linha[3:].strip().strip('"')
        if codigo == "??":
            tipo = "Novo"
        elif "R" in codigo:
            tipo = "Renomeado"
            caminho = caminho.split(" -> ")[-1]
        elif "D" in codigo:
            tipo = "Apagado"
        elif "A" in codigo:
            tipo = "Novo"
        else:
            tipo = "Alterado"
        alteracoes.append(Alteracao(tipo, caminho))
    return alteracoes


def arquivos_sensiveis(alteracoes: list[Alteracao]) -> list[str]:
    suspeitos = []
    for a in alteracoes:
        if a.tipo == "Apagado":
            continue
        caminho = a.arquivo.lower()
        if any(re.search(p, caminho) for p in PADROES_SENSIVEIS):
            suspeitos.append(a.arquivo)
    return suspeitos


def _branch_remota_existe(repo: Repo, branch: str) -> bool:
    return bool(repo.git.ls_remote("--heads", "origin", branch).strip())


def _envios_pendentes(repo: Repo) -> int:
    """Quantos commits locais ainda não foram enviados."""
    branch = repo.active_branch.name
    if not _branch_remota_existe(repo, branch):
        return len(list(repo.iter_commits(branch))) if repo.head.is_valid() else 0
    try:
        return int(repo.git.rev_list("--count", f"origin/{branch}..{branch}"))
    except GitCommandError:
        return 0


# ---------------------------------------------------------------------------
# Ações
# ---------------------------------------------------------------------------

def baixar(cfg: Config, url: str) -> Resultado:
    url = url.strip()
    if not re.match(r"^(https://|git@)[\w.@:/~+-]+$", url):
        return Resultado(False, "Endereço inválido. Ele deve começar com https:// "
                                "(copie o endereço do botão \"Code\" / \"Clonar\" do repositório).")

    nome = url.rstrip("/").split("/")[-1].split(":")[-1]
    nome = nome[:-4] if nome.endswith(".git") else nome
    destino = cfg.pasta_projetos / nome

    if destino.exists():
        return Resultado(False, f"Você já tem o projeto \"{nome}\". "
                                "Use \"Atualizar meu projeto\" para pegar as novidades.")

    cfg.pasta_projetos.mkdir(parents=True, exist_ok=True)
    try:
        Repo.clone_from(url, destino, env={**os.environ, **_ambiente_git(cfg)})
    except GitCommandError as e:
        if destino.exists():
            _apagar_pasta(destino)
        return Resultado(False, _traduzir_erro(e), str(e))

    return Resultado(True, f"Projeto \"{nome}\" baixado na pasta:\n{destino}")


def atualizar(cfg: Config, projeto: str) -> Resultado:
    repo = None
    try:
        repo = _abrir(cfg, projeto)
        branch = repo.active_branch.name
        if not _branch_remota_existe(repo, branch):
            return Resultado(True, "Não há nada novo no servidor ainda.")

        if not repo.head.is_valid():
            # Projeto baixado quando ainda estava vazio: pega tudo pela primeira vez
            repo.git.pull("origin", branch)
            arquivos = repo.git.ls_files().splitlines()
            return Resultado(True, f"Projeto atualizado! {len(arquivos)} arquivo(s) "
                                   "recebido(s) da equipe.", "\n".join(arquivos))

        antes = repo.head.commit.hexsha
        repo.git.pull("--rebase", "--autostash", "origin", branch)
        depois = repo.head.commit.hexsha
    except GitCommandError as e:
        if repo is not None:
            _desfazer_rebase(repo)
        return Resultado(False, _traduzir_erro(e), str(e))
    except (InvalidGitRepositoryError, TypeError) as e:
        return Resultado(False, "Esta pasta não é um projeto válido.", str(e))

    if antes == depois:
        return Resultado(True, "Seu projeto já estava em dia. Nada novo no servidor.")

    arquivos = repo.git.diff("--name-only", antes, depois).splitlines()
    return Resultado(True, f"Projeto atualizado! {len(arquivos)} arquivo(s) "
                           "recebido(s) da equipe.", "\n".join(arquivos))


def enviar(cfg: Config, projeto: str, mensagem: str) -> Resultado:
    mensagem = mensagem.strip()
    if not mensagem:
        return Resultado(False, "Escreva uma frase curta dizendo o que você alterou.")
    if not cfg.nome or not cfg.email:
        return Resultado(False, "Preencha seu nome e e-mail na configuração antes de enviar.")

    try:
        repo = _abrir(cfg, projeto)
        alteracoes = ver_alteracoes(cfg, projeto)

        # 1) Registra as alterações (git add . + git commit)
        if alteracoes:
            repo.git.add("--all")
            repo.git.commit(
                "-m", mensagem,
                env={
                    "GIT_AUTHOR_NAME": cfg.nome, "GIT_AUTHOR_EMAIL": cfg.email,
                    "GIT_COMMITTER_NAME": cfg.nome, "GIT_COMMITTER_EMAIL": cfg.email,
                },
            )
        elif _envios_pendentes(repo) == 0:
            return Resultado(False, "Não há nada para enviar: nenhum arquivo foi alterado.")

        branch = repo.active_branch.name

        # 2) Pega as novidades dos colegas antes de enviar (git pull)
        if _branch_remota_existe(repo, branch):
            try:
                repo.git.pull("--rebase", "origin", branch)
            except GitCommandError as e:
                _desfazer_rebase(repo)
                return Resultado(False, _traduzir_erro(e), str(e))

        # 3) Envia (git push)
        repo.git.push("--set-upstream", "origin", branch)

    except GitCommandError as e:
        return Resultado(False, _traduzir_erro(e), str(e))

    qtd = len(alteracoes)
    texto = f"{qtd} arquivo(s)" if qtd else "Alterações pendentes"
    return Resultado(True, f"{texto} enviado(s) com sucesso!",
                     "\n".join(f"{a.tipo}: {a.arquivo}" for a in alteracoes))


# ---------------------------------------------------------------------------
# Auxiliares
# ---------------------------------------------------------------------------

def _desfazer_rebase(repo: Repo) -> None:
    """Se um pull parou no meio por conflito, volta tudo ao estado anterior."""
    try:
        git_dir = Path(repo.git_dir)
        if (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists():
            repo.git.rebase("--abort")
    except Exception:
        pass


def _apagar_pasta(pasta: Path) -> None:
    import shutil
    import stat

    def _forcar(func, caminho, _):
        os.chmod(caminho, stat.S_IWRITE)
        func(caminho)

    shutil.rmtree(pasta, onerror=_forcar)
