# 📚 Gestor de Estudos do Casal — Telegram Bot

Bot modular em Python 3.10+ para acompanhamento mútuo de estudos com foco em **prestação de contas (accountability)**, **registro sem atrito** (em 2 cliques) e **gamificação com gráficos comparativos semanais e ofensivas diárias**.

---

## 🛠️ Stack Tecnológica

- **Linguagem:** Python 3.10+
- **Framework do Bot:** [aiogram 3.x](https://docs.aiogram.dev/) (FSM, Routers e Inline Keyboards)
- **Banco de Dados Assíncrono:** SQLAlchemy 2.0 + `aiosqlite` (SQLite assíncrono)
- **Relatórios Visuais:** Matplotlib (gráfico de barras comparativo e gráfico de pizza em Dark Mode)
- **Agendador de Tarefas:** APScheduler (Cutucão / Nudges diários às 20h00)

---

## 📂 Estrutura do Projeto

```plaintext
gestor_estudos_bot/
├── .env.example          # Modelo de variáveis de ambiente
├── .gitignore            # Arquivos ignorados pelo Git (.env, caches, banco)
├── requirements.txt      # Dependências do projeto
├── bot.py                # Ponto de entrada, inicialização do bot e APScheduler
├── config.py             # Leitura do .env e variáveis globais
├── database/
│   ├── models.py         # Tabelas SQLAlchemy (User, StudySession) e engine assíncrono
│   └── crud.py           # Funções CRUD (registro de sessão, cálculo de streak, estatísticas)
├── handlers/
│   ├── registrar.py      # FSM e botões do fluxo de /estudar
│   ├── relatorios.py     # Comandos /ranking (gráfico PNG), /hoje e /ofensiva
│   └── gamificacao.py    # Comandos /start, /ajuda e /badges
└── utils/
    ├── graficos.py       # Renderização não-bloqueante dos gráficos com Matplotlib
    └── teclados.py       # Construtores de Inline Keyboards (CallbackData tipados)
```

---

## 🚀 Como Executar Localmente

### 1. Criar o Bot no Telegram
1. Abra o Telegram e procure por [@BotFather](https://t.me/BotFather).
2. Envie o comando `/newbot` e siga as instruções para definir o nome e username do seu bot.
3. Copie o **HTTP API Token** gerado.

### 2. Configurar o `.env`
1. Dentro da pasta `gestor_estudos_bot/`, copie o arquivo `.env.example` para `.env`:
   ```bash
   cp .env.example .env   # Linux/Mac
   copy .env.example .env # Windows CMD
   ```
2. Abra o `.env` e preencha:
   - `BOT_TOKEN`: cole o token do @BotFather.
   - `USER_A_ID` e `USER_B_ID`: pegue seus IDs enviando `/id` para o bot [@userinfobot](https://t.me/userinfobot).
   - `GROUP_CHAT_ID`: (opcional) se vocês criarem um grupo no Telegram com o bot dentro, adicione o bot como admin do grupo e coloque o ID do grupo aqui.

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

## 📤 Como Colocar no GitHub

No seu terminal (na pasta raiz onde está o projeto):

```bash
# 1. Inicialize o repositório Git
git init

# 2. Adicione os arquivos (o .gitignore garantirá que seu .env e banco não vazem)
git add .

# 3. Faça o commit inicial
git commit -m "feat: bot gestor de estudos para casal finalizado"

# 4. Renomeie a branch principal para main
git branch -M main

# 5. Crie um novo repositório vazio no seu GitHub (ex: gestor_estudos_bot)
# Em seguida, vincule o repositório remoto (substitua pelo seu link do GitHub):
git remote add origin https://github.com/lowfierd/gestor_estudos_bot.git

# 6. Envie o código:
git push -u origin main
```

---

## 🐍 Como Hospedar no PythonAnywhere (`lowfield`)

O [PythonAnywhere](https://www.pythonanywhere.com/user/lowfield/) já possui suporte a Python e o domínio da API do Telegram (`api.telegram.org`) está liberado na whitelist de conexões de saída (mesmo para contas gratuitas).

### Passo a Passo no PythonAnywhere:

1. **Acesse o Console Bash:**
   - Faça login na sua conta `lowfield` no [PythonAnywhere](https://www.pythonanywhere.com/).
   - Vá na aba **Consoles** e abra um console **Bash**.

2. **Clonar o Repositório do GitHub:**
   ```bash
   git clone https://github.com/lowfierd/gestor_estudos_bot.git
   cd gestor_estudos_bot
   ```

3. **Criar e Ativar a Virtualenv com Python 3.10:**
   ```bash
   mkvirtualenv --python=/usr/bin/python3.10 gestor-bot-env
   pip install -r requirements.txt
   ```

4. **Criar o arquivo `.env` de Produção:**
   ```bash
   nano .env
   ```
   Cole o seu token e variáveis (use `Ctrl+O` para salvar e `Ctrl+X` para sair).

5. **Manter o Bot Rodando:**
   - **Opção A (Plano Hacker/Pago com Always-on Tasks - Recomendado):**
     - Vá na aba **Tasks**.
     - Na seção *Always-on tasks*, crie uma nova tarefa com o comando:
       ```bash
       /home/lowfield/.virtualenvs/gestor-bot-env/bin/python /home/lowfield/gestor_estudos_bot/bot.py
       ```
     - O PythonAnywhere manterá o processo rodando 24 horas por dia e reiniciará caso caia.
   - **Opção B (Plano Gratuito / Free via Console ou Scheduled Task):**
     - No plano gratuito, você pode rodar direto no console `python bot.py` para testes.
     - Para uso contínuo no plano gratuito, você pode configurar uma **Scheduled Task** diária para rodar rotinas ou manter uma tela de console aberta.

---

## 🎮 Comandos do Bot

| Comando | Descrição |
|---|---|
| `/start` | Apresenta o bot e cadastra o usuário no sistema. |
| `/estudar` | Inicia o fluxo interativo com botões de matéria e tempo. |
| `/ranking` | Gera e envia a imagem do gráfico comparativo da semana (barras + pizza). |
| `/hoje` | Mostra quem já bateu o ponto de estudos no dia. |
| `/ofensiva` | Exibe o contador de dias seguidos (streaks) de cada um. |
| `/badges` | Galeria de medalhas e conquistas por consistência. |
| `/ajuda` | Manual rápido de instruções. |
