# 📚 Gestor de Estudos do Casal — Telegram Bot

Bot modular em Python 3.10+ para acompanhamento mútuo de estudos com foco em **prestação de contas (accountability)**, **comprovação por foto em canal**, **registro sem atrito** (em cliques) e **gamificação com gráficos comparativos semanais e ofensivas diárias**.

---

## 🛠️ Stack Tecnológica

- **Linguagem:** Python 3.10+
- **Framework do Bot:** [aiogram 3.x](https://docs.aiogram.dev/) (FSM, Routers e Inline Keyboards)
- **Banco de Dados Assíncrono:** SQLAlchemy 2.0 + `aiosqlite` (SQLite assíncrono)
- **Relatórios Visuais:** Matplotlib (gráfico de barras comparativo e gráfico de pizza em Dark Mode)
- **Agendador de Tarefas:** APScheduler (Cutucão / Nudges diários às 20h00)

---

## 📸 Novo: Comprovação por Foto no Canal do Casal

1. Ao enviar `/estudar`, você escolhe a matéria e o tempo via botões.
2. O bot solicita uma **foto do material ou anotações** para provar que o estudo foi realizado (você pode incluir uma legenda com resumo).
3. O bot posta automaticamente a foto com o comprovante formatado no **Canal do Casal** (estilo feed de estudos).
4. Se naquele momento você não puder tirar foto, basta clicar em **⏭️ Pular Foto**.

---

## 📂 Estrutura do Projeto

```plaintext
gestor_estudos_bot/
├── .env.example          # Modelo de variáveis de ambiente (apenas BOT_TOKEN necessário)
├── .gitignore            # Arquivos ignorados pelo Git (.env, caches, banco)
├── requirements.txt      # Dependências do projeto
├── bot.py                # Ponto de entrada, inicialização do bot e APScheduler
├── config.py             # Leitura do .env e variáveis globais
├── database/
│   ├── models.py         # Tabelas SQLAlchemy (User, StudySession, RegisteredGroup, RegisteredChannel)
│   └── crud.py           # Funções CRUD (registro de sessão com foto, ofensivas, grupos e canais)
├── handlers/
│   ├── registrar.py      # FSM de /estudar com envio de fotos comprovatórias para canal
│   ├── relatorios.py     # Comandos /ranking (gráfico PNG), /hoje e /ofensiva
│   └── gamificacao.py    # Comandos /start, /ajuda, /setcanal e /badges
└── utils/
    ├── graficos.py       # Renderização não-bloqueante dos gráficos com Matplotlib
    └── teclados.py       # Construtores de Inline Keyboards (CallbackData tipados)
```

---

## 🚀 Como Executar Localmente

### 1. Criar o Bot no Telegram
1. Abra o Telegram e procure por [@BotFather](https://t.me/BotFather).
2. Envie o comando `/newbot` e defina o nome do seu bot.
3. Copie o **HTTP API Token** gerado.

### 2. Configurar o `.env`
1. Crie o arquivo `.env` na pasta `gestor_estudos_bot/`:
   ```env
   BOT_TOKEN=seu_token_aqui_do_botfather
   ```
   *(Não precisa caçar IDs! O bot detecta você, sua namorada e o grupo automaticamente).*

### 3. Instalar Dependências e Iniciar
```bash
# Crie e ative um ambiente virtual
python -m venv venv

# Windows:
.\venv\Scripts\activate

# Linux/Mac:
source venv/bin/activate

# Instale os pacotes:
pip install -r requirements.txt

# Inicie o bot:
python bot.py
```

---

## 📢 Como Configurar o Canal de Comprovantes

1. Crie um canal no Telegram (ex: `Feed de Estudos do Casal`).
2. Adicione o seu bot como **Administrador** do canal (com permissão para postar mensagens).
3. No chat privado com o bot (ou no grupo), envie:
   ```text
   /setcanal @nome_do_seu_canal
   ```
4. Pronto! A partir desse momento, cada sessão de estudo registrada com foto ou texto será postada no canal automaticamente.

---

## 🎮 Comandos do Bot

| Comando | Descrição |
|---|---|
| `/start` | Apresenta o bot e cadastra o usuário no sistema automaticamente. |
| `/estudar` | Inicia o fluxo interativo: exibe as 6 disciplinas mais estudadas (com opção de ver mais), tempo e foto de comprovante. |
| `/addmateria` | Cadastra uma nova disciplina (ex: `/addmateria Economia`). |
| `/removermateria` | Abre menu com botões para excluir uma disciplina em 1 clique. |
| `/materias` | Lista todas as disciplinas e a contagem de vezes estudadas. |
| `/setregistro` | Vincula o tópico do grupo com fórum como mural oficial de comprovantes. |
| `/setcanal` | Vincula um canal de comprovantes (ex: `/setcanal @canal_casal`). |
| `/ranking` | Gera e envia o gráfico comparativo da semana (barras + pizza). |
| `/hoje` | Mostra quem já bateu o ponto de estudos no dia. |
| `/ofensiva` | Exibe o contador de dias seguidos (streaks) de cada um. |
| `/badges` | Galeria de medalhas e conquistas por consistência. |
| `/ajuda` | Manual rápido de instruções. |

---

## 🐍 Como Hospedar no PythonAnywhere (`lowfield`)

O repositório já está no seu GitHub: [github.com/lowfierd/gestor_estudos_bot](https://github.com/lowfierd/gestor_estudos_bot).

No console Bash do PythonAnywhere:
```bash
git clone https://github.com/lowfierd/gestor_estudos_bot.git
cd gestor_estudos_bot
mkvirtualenv --python=/usr/bin/python3.10 gestor-bot-env
pip install -r requirements.txt
nano .env # Cole o BOT_TOKEN=...
python bot.py
```
*(Ou configure na aba **Tasks** como Always-on task para rodar 24h).*
