from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from database.models import async_session
from database import crud

router = Router(name="gamificacao_router")

# Definição das Conquistas (Badges)
BADGES = [
    {"name": "🌱 Primeiro Passo", "streak": 1, "desc": "Registrou o 1º dia de estudos"},
    {"name": "🔥 Em Chamas", "streak": 3, "desc": "3 dias consecutivos de foco"},
    {"name": "⚡ Foco Blindado", "streak": 7, "desc": "1 semana ininterrupta de ofensiva"},
    {"name": "💎 Hábito Inabalável", "streak": 14, "desc": "2 semanas consecutivas"},
    {"name": "👑 Mestre da Disciplina", "streak": 30, "desc": "1 mês inteiro sem faltar um único dia"},
]


@router.message(CommandStart())
async def cmd_start(message: Message):
    """
    Mensagem de boas-vindas e introdução ao bot do casal.
    Registra automaticamente o usuário e o grupo (caso enviado no grupo).
    """
    user = message.from_user
    async with async_session() as session:
        await crud.get_or_create_user(
            session=session,
            telegram_id=user.id,
            first_name=user.first_name,
            username=user.username
        )
        # Se o comando for executado dentro de um grupo, salva o grupo automaticamente!
        if message.chat.type in ["group", "supergroup"]:
            await crud.register_group(
                session=session,
                chat_id=message.chat.id,
                title=message.chat.title
            )

    texto = (
        f"👋 Olá, *{user.first_name}*! Bem-vindo(a) ao seu *Gestor de Estudos do Casal*! 🎯\n\n"
        "O objetivo deste bot é manter você e seu amor motivados, consistentes e com prestação de contas mútua.\n\n"
        "📌 *Comandos Rápidos:*\n"
        "• `/estudar` - Registra sua sessão de estudo em 2 cliques.\n"
        "• `/ranking` - Gera o gráfico comparativo semanal do casal.\n"
        "• `/hoje` - Mostra quem já estudou hoje e quem ainda está devendo.\n"
        "• `/ofensiva` - Placar de dias consecutivos (streaks).\n"
        "• `/badges` - Visualiza as medalhas e conquistas desbloqueadas.\n"
        "• `/ajuda` - Relembra as instruções de uso.\n\n"
        "⏰ *Lembrete:* Todos os dias às 20h haverá um cutucão caso um de vocês ainda não tenha estudado!"
    )
    await message.answer(texto, parse_mode="Markdown")


@router.message(Command("ajuda"))
async def cmd_ajuda(message: Message):
    """
    Manual de instruções simples e direto.
    """
    texto = (
        "📖 *Guia de Uso do Gestor de Estudos*\n\n"
        "1️⃣ Para registrar, envie `/estudar` no privado ou grupo, selecione a matéria, o tempo e anexe sua *foto comprovatória*!\n"
        "2️⃣ Os comprovantes com foto e anotações são encaminhados automaticamente para o canal do casal.\n"
        "3️⃣ Para definir o canal de comprovantes, adicione o bot como admin do canal e use `/setcanal @nomedocanal`.\n"
        "4️⃣ Não deixe passar das 20h para não levar cutucão do bot!\n"
        "5️⃣ Use `/ranking` para ver o gráfico comparativo da semana."
    )
    await message.answer(texto, parse_mode="Markdown")


@router.message(Command("setcanal"))
async def cmd_setcanal(message: Message):
    """
    Vincula um canal de comprovantes para o casal.
    Exemplo de uso: /setcanal @meu_canal_estudos
    """
    args = message.text.split(maxsplit=1)
    target_chat = None

    if len(args) > 1:
        target_chat = args[1].strip()
    elif message.chat.type == "channel":
        target_chat = message.chat.id

    if not target_chat:
        await message.answer(
            "⚠️ *Como vincular o canal de comprovantes:*\n\n"
            "1. Adicione o bot como *Administrador* do seu canal.\n"
            "2. Envie o comando informando o @ do canal ou o ID:\n"
            "Exemplo: `/setcanal @canal_estudos_casal`",
            parse_mode="Markdown"
        )
        return

    try:
        chat = await message.bot.get_chat(target_chat)
        async with async_session() as session:
            await crud.register_channel(
                session=session,
                channel_id=chat.id,
                title=chat.title,
                username=chat.username
            )

        await message.answer(
            f"✅ *Canal Vinculado com Sucesso!*\n\n"
            f"📢 Canal: *{chat.title}*\n"
            f"A partir de agora, todas as fotos e registros de estudos serão encaminhados para ele!",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(
            f"❌ Não foi possível acessar o canal `{target_chat}`.\n"
            f"Verifique se o bot foi adicionado como *Administrador* no canal com permissão para postar mensagens.\n"
            f"Detalhes: `{e}`",
            parse_mode="Markdown"
        )



@router.message(Command("badges"))
async def cmd_badges(message: Message):
    """
    Exibe a galeria de badges e o status de desbloqueio para cada usuário.
    """
    async with async_session() as session:
        users = await crud.get_all_users(session)

    if not users:
        await message.answer("Nenhum usuário registrado ainda. Digite `/estudar`!")
        return

    lines = ["🏅 *Galeria de Conquistas e Badges*\n"]
    for user in users:
        lines.append(f"👤 *{user.first_name}* (Ofensiva: {user.streak_count} dias)")
        for b in BADGES:
            unlocked = user.streak_count >= b["streak"]
            icon = "✅" if unlocked else "🔒"
            lines.append(f"  {icon} *{b['name']}* ({b['desc']})")
        lines.append("")

    await message.answer("\n".join(lines), parse_mode="Markdown")


@router.message(F.new_chat_members)
async def on_bot_added_to_group(message: Message):
    """
    Quando o bot é adicionado a um grupo do casal, ele se apresenta e
    salva o ID do grupo automaticamente no banco.
    """
    bot_user = await message.bot.get_me()
    added_bot = any(user.id == bot_user.id for user in message.new_chat_members)

    if added_bot:
        async with async_session() as session:
            await crud.register_group(
                session=session,
                chat_id=message.chat.id,
                title=message.chat.title
            )

        await message.answer(
            f"🎉 *Gestor de Estudos Ativado no Grupo!*\n\n"
            f"Grupo *'{message.chat.title}'* registrado com sucesso.\n"
            f"A partir de agora vocês podem:\n"
            f"• Usar `/estudar` para registrar as horas em 2 cliques.\n"
            f"• Usar `/ranking` para ver o gráfico comparativo da semana.\n"
            f"• Receber o cutucão automático às 20h00 se um de vocês ainda não tiver estudado!\n\n"
            f"Bons estudos ao casal! 📚❤️",
            parse_mode="Markdown"
        )

