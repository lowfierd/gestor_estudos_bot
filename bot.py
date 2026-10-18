import asyncio
import logging
from datetime import date
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

import config
from database.models import init_db, async_session
from database import crud
from handlers import registrar, relatorios, gamificacao

# Configuração de Logs
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("GestorEstudosBot")


async def job_nudge_20h(bot: Bot):
    """
    Rotina executada diariamente às 20h00:
    Verifica se um dos membros do casal estudou e o outro não, enviando o cutucão (nudge).
    """
    logger.info("Executando verificação de cutucão (nudge) das 20h00...")
    today = date.today()

    async with async_session() as session:
        status = await crud.get_today_study_status(session, target_date=today)

    users_list = list(status.values())
    if len(users_list) < 2:
        logger.info("Menos de 2 usuários cadastrados no banco. Nudge não enviado.")
        return

    user_a = users_list[0]
    user_b = users_list[1]

    user_a_obj, user_a_studied = user_a["user"], user_a["studied_today"]
    user_b_obj, user_b_studied = user_b["user"], user_b["studied_today"]

    msg_text = None

    # Caso 1: Usuário A estudou e Usuário B não
    if user_a_studied and not user_b_studied:
        msg_text = (
            f"👀 *Alerta das 20h00: Cutucão Ativado!*\n\n"
            f"🔥 *{user_a_obj.first_name}* já estudou hoje e abriu vantagem!\n"
            f"E você, *{user_b_obj.first_name}*, vai deixar ficar para trás? ⏰\n\n"
            f"Use `/estudar` para registrar sua sessão e manter sua ofensiva acesa!"
        )
    # Caso 2: Usuário B estudou e Usuário A não
    elif user_b_studied and not user_a_studied:
        msg_text = (
            f"👀 *Alerta das 20h00: Cutucão Ativado!*\n\n"
            f"🔥 *{user_b_obj.first_name}* já estudou hoje e abriu vantagem!\n"
            f"E você, *{user_a_obj.first_name}*, vai deixar barato? ⏰\n\n"
            f"Use `/estudar` para registrar sua sessão e manter sua ofensiva acesa!"
        )
    # Caso 3: Nenhum dos dois estudou ainda
    elif not user_a_studied and not user_b_studied:
        msg_text = (
            f"🚨 *Atenção Casal! Já são 20h00!*\n\n"
            f"Nenhum de vocês registrou estudos hoje! 😱\n"
            f"Não deixem a ofensiva zerar. Que tal uma sessão de foco agora?\n\n"
            f"Basta enviar `/estudar` para salvar!"
        )
    # Caso 4: Ambos estudaram
    else:
        msg_text = (
            f"✨ *Parabéns ao Casal! Meta Batida!*\n\n"
            f"Tanto *{user_a_obj.first_name}* quanto *{user_b_obj.first_name}* já cumpriram o foco de hoje! 🏆\n"
            f"Orgulho mútuo e consistência mantida!"
        )

    # Envia para o grupo compartilhado se configurado, ou para os chats privados
    if config.GROUP_CHAT_ID:
        try:
            await bot.send_message(chat_id=config.GROUP_CHAT_ID, text=msg_text, parse_mode=ParseMode.MARKDOWN)
        except Exception as e:
            logger.error(f"Erro ao enviar nudge para o grupo {config.GROUP_CHAT_ID}: {e}")
    else:
        # Se não houver grupo configurado, envia no privado de ambos
        for user_data in [user_a, user_b]:
            try:
                await bot.send_message(chat_id=user_data["user"].telegram_id, text=msg_text, parse_mode=ParseMode.MARKDOWN)
            except Exception as e:
                logger.error(f"Erro ao enviar mensagem para {user_data['user'].telegram_id}: {e}")


async def main():
    if not config.BOT_TOKEN or config.BOT_TOKEN == "seu_token_aqui":
        logger.error("ERRO: BOT_TOKEN não configurado no arquivo .env!")
        print("\n[ERRO CRÍTICO] Configure seu BOT_TOKEN no arquivo .env antes de rodar o bot.")
        return

    # Inicializa as tabelas do banco de dados assíncrono
    logger.info("Criando/verificando tabelas do banco de dados SQLite...")
    await init_db()

    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher()

    # Registro dos Routers modulares
    dp.include_router(gamificacao.router)
    dp.include_router(registrar.router)
    dp.include_router(relatorios.router)

    # Configuração do Agendador de Tarefas (APScheduler)
    scheduler = AsyncIOScheduler(timezone="America/Sao_Paulo")
    
    # Agendamento diário às 20:00 (Horário de Brasília)
    scheduler.add_job(
        job_nudge_20h,
        trigger=CronTrigger(hour=20, minute=0, timezone="America/Sao_Paulo"),
        args=[bot],
        id="daily_nudge_20h",
        replace_existing=True
    )

    scheduler.start()
    logger.info("APScheduler iniciado. Job das 20h00 agendado com sucesso no fuso de São Paulo.")

    logger.info("Bot iniciado com sucesso! Aguardando mensagens...")
    try:
        # Limpa eventuais updates acumulados enquanto o bot esteve offline
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot finalizado pelo usuário.")
