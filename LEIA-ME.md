# Git Fácil

Aplicativo simples para baixar, atualizar e enviar projetos Git sem precisar
digitar comandos. A tela abre no navegador, mas o app roda no próprio
computador do usuário, então ele enxerga os arquivos locais.

## Para quem vai usar

1. Dê dois cliques no atalho **Git Fácil** da área de trabalho.
2. No primeiro acesso, informe seu nome e e-mail.
3. Escolha o que quer fazer:
   - **📥 Baixar um projeto**: cole o endereço do repositório e clique em *Baixar*.
   - **🔄 Atualizar meu projeto**: escolha o projeto e clique em *Atualizar*.
   - **📤 Enviar minhas alterações**: escolha o projeto, confira a lista de
     arquivos, escreva o que fez e clique em *Enviar*.
4. Ao terminar, clique em **🚪 Fechar o Git Fácil** (na barra lateral) e
   depois feche a aba do navegador.

Os projetos ficam em `Documentos\Projetos`. Edite os arquivos normalmente
por lá e depois use o app para enviar.

## Para quem vai instalar (uma vez por computador)

**Pré-requisitos**
- [Python 3.10+](https://www.python.org/downloads/): marque *"Add python.exe to PATH"*.
- [Git for Windows](https://git-scm.com/download/win): opções padrão.

**Instalação**
1. Copie a pasta `git-facil` para o computador (ex.: `C:\GitFacil`).
2. Dê dois cliques em `instalar.bat`.
3. Pronto: o atalho **Git Fácil** aparece na área de trabalho.

**Acesso ao GitHub/GitLab** (escolha um)
- **Sem configurar nada:** no primeiro envio, o Git for Windows abre uma
  janela de login do GitHub/GitLab e guarda o acesso no Windows.
- **Com token:** copie `config.env.example` para `config.env` e preencha
  `TOKEN` e `TOKEN_USUARIO`. O token é usado só durante cada comando e não é
  gravado dentro dos projetos.

## O que acontece por trás

| Botão | Comandos Git |
|---|---|
| Baixar | `git clone` |
| Atualizar | `git pull --rebase --autostash` |
| Enviar | `git add --all` → `git commit` → `git pull --rebase` → `git push` |

Proteções incluídas:
- Lista os arquivos que serão enviados antes de confirmar.
- Alerta sobre arquivos que parecem conter senhas ou chaves (`.env`, `.pem`, etc.).
- Busca as novidades da equipe antes de enviar.
- Em caso de conflito, desfaz a tentativa, mantém as alterações do usuário
  salvas e mostra uma mensagem clara, sem tentar resolver sozinho.
- O app só aceita acesso do próprio computador (`localhost`).

## Estrutura

```
git-facil/
├── app.py               tela (Streamlit)
├── git_ops.py           operações Git, separadas da tela
├── requirements.txt     dependências (todas open source)
├── config.env.example   modelo de configuração
├── instalar.bat         instalação no Windows
├── iniciar.bat          abre o app (usado pelo atalho)
└── .streamlit/config.toml
```

Para rodar em modo de desenvolvimento (qualquer sistema):

```
pip install -r requirements.txt
streamlit run app.py
```
