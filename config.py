import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env localizado na raiz do projeto
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# IDs do Telegram do casal (opcional: para restringir o bot ou direcionar os nudges)
USER_A_ID = int(os.getenv("USER_A_ID", "0"))
USER_B_ID = int(os.getenv("USER_B_ID", "0"))

# ID do grupo/canal compartilhado do casal (se usarem um grupo mútuo)
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID", None)
if GROUP_CHAT_ID:
    try:
        GROUP_CHAT_ID = int(GROUP_CHAT_ID)
    except ValueError:
        pass

# ID ou @username do Canal oficial de comprovantes (onde o bot posta fotos e registros)
CHANNEL_ID = os.getenv("CHANNEL_ID", None)
if CHANNEL_ID:
    try:
        CHANNEL_ID = int(CHANNEL_ID)
    except ValueError:
        # Se for string (ex: @canal_estudos), mantém string
        pass

# URL de conexão do banco de dados (SQLite assíncrono padrão)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{BASE_DIR / 'database' / 'gestor_estudos.db'}")

if not BOT_TOKEN:
    print("[AVISO] BOT_TOKEN não foi configurado no arquivo .env!")
