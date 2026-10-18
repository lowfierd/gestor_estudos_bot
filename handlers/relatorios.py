from datetime import date, timedelta
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, BufferedInputFile

from database.models import async_session
from database import crud
from utils.graficos import generate_weekly_report_chart

router = Router(name="relatorios_router")


@router.message(Command("ranking"))
async def cmd_ranking(message: Message):
    """
    Gera e envia o relatório visual comparativo (barras + pizza) dos estudos da semana.
    """
    today = date.today()
    # Pega o início da semana atual (segunda-feira) até hoje
    start_of_week = today - timedelta(days=today.weekday())

    wait_msg = await message.answer("📊 *Gerando o relatório visual da semana...*", parse_mode="Markdown")

    async with async_session() as session:
        weekly_data = await crud.get_weekly_stats(
            session=session,
            start_date=start_of_week,
            end_date=today
        )

    # Gera a imagem na thread assíncrona
    chart_buffer = await generate_weekly_report_chart(weekly_data)

    # Monta legenda com texto explicativo
    caption_lines = [
        "🏆 *Ranking Semanal do Casal*",
        f"📅 Período: {start_of_week.strftime('%d/%m')} a {today.strftime('%d/%m')}\n"
    ]

    users = weekly_data.get("users", [])
    if users:
        sorted_users = sorted(users, key=lambda x: x["minutes"], reverse=True)
        for idx, u in enumerate(sorted_users, 1):
            h = u["minutes"] // 60
            m = u["minutes"] % 60
            tempo_str = f"{h}h {m}m" if m else f"{h}h"
            medal = "🥇" if idx == 1 else "🥈"
            caption_lines.append(f"{medal} *{u['name']}*: {tempo_str} estudadas")
    else:
        caption_lines.append("Nenhum estudo registrado ainda esta semana!\nUsem `/estudar` para começar a pontuar.")

    caption_text = "\n".join(caption_lines)

    photo_file = BufferedInputFile(
        file=chart_buffer.getvalue(),
        filename=f"ranking_{today.isoformat()}.png"
    )

    await message.answer_photo(photo=photo_file, caption=caption_text, parse_mode="Markdown")
    await wait_msg.delete()


@router.message(Command("hoje"))
async def cmd_hoje(message: Message):
    """
    Verifica o placar e status de estudo do dia de hoje.
    """
    today = date.today()
    async with async_session() as session:
        status = await crud.get_today_study_status(session, target_date=today)

    if not status:
        await message.answer(
            "Nenhum estudante registrado ainda! Usem `/estudar` para registrar a primeira sessão.",
            parse_mode="Markdown"
        )
        return

    lines = [f"📅 *Status de Estudos de Hoje ({today.strftime('%d/%m/%Y')})*\n"]
    for user_id, data in status.items():
        user = data["user"]
        total_min = data["total_minutes"]
        h = total_min // 60
        m = total_min % 60
        tempo_str = f"{h}h {m}m" if m else f"{h}h"

        if data["studied_today"]:
            lines.append(f"✅ *{user.first_name}*: {tempo_str} estudados | 🔥 Ofensiva: {user.streak_count} dias")
        else:
            lines.append(f"⏳ *{user.first_name}*: Ainda não estudou hoje | 🔥 Ofensiva: {user.streak_count} dias")

    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(Command("ofensiva"))
async def cmd_ofensiva(message: Message):
    """
    Exibe os streaks e histórico de consistência dos dois.
    """
    async with async_session() as session:
        users = await crud.get_all_users(session)

    if not users:
        await message.answer("Nenhum usuário cadastrado ainda. Use `/estudar` para começar!")
        return

    lines = ["🔥 *Painel de Ofensivas (Streaks Consecutivos)*\n"]
    for u in users:
        last = u.last_study_date.strftime("%d/%m/%Y") if u.last_study_date else "Nunca"
        lines.append(f"👤 *{u.first_name}*: {u.streak_count} dia(s) seguidos | Último registro: {last}")

    lines.append("\n_Dica: Estude ao menos 30 minutos todos os dias para não deixar o fogo apagar!_")
    await message.answer("\n".join(lines), parse_mode="Markdown")
