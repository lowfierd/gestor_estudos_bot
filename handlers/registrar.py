from datetime import datetime
import logging
from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

import config
from database.models import async_session
from database import crud
from utils.teclados import (
    SubjectCallback,
    DurationCallback,
    get_subjects_keyboard,
    get_durations_keyboard,
    get_photo_prompt_keyboard
)

logger = logging.getLogger("RegistrarHandler")
router = Router(name="registrar_router")


class StudyRegistrationFSM(StatesGroup):
    choosing_subject = State()
    choosing_duration = State()
    waiting_photo = State()


def format_duration(minutes: int) -> str:
    h = minutes // 60
    m = minutes % 60
    if h > 0 and m > 0:
        return f"{h}h {m}m"
    elif h > 0:
        return f"{h}h"
    return f"{minutes} minutos"


async def forward_to_evidence_channel(
    bot: Bot,
    user_name: str,
    subject: str,
    minutes: int,
    streak: int,
    photo_file_id: str | None = None,
    notes: str | None = None
) -> None:
    """
    Encaminha o comprovante da sessão de estudos (com foto ou texto) para o canal oficial do casal.
    """
    targets = []
    if config.CHANNEL_ID:
        targets.append((config.CHANNEL_ID, None))

    async with async_session() as session:
        channels_db = await crud.get_registered_channels(session)
        for ch in channels_db:
            targets.append((ch.channel_id, ch.message_thread_id))

    if not targets:
        logger.info("Nenhum canal ou tópico de comprovantes configurado para encaminhar.")
        return

    duration_str = format_duration(minutes)
    now_str = datetime.now().strftime("%d/%m/%Y às %H:%M")

    caption_lines = [
        "📸 *NOVO REGISTRO DE ESTUDO CONFIRMADO!*",
        "━━━━━━━━━━━━━━━━━━━━",
        f"👤 *Estudante:* {user_name}",
        f"📚 *Disciplina:* {subject}",
        f"⏱️ *Duração:* {duration_str}",
        f"🔥 *Ofensiva:* {streak} dia(s) consecutivos",
        f"📅 *Data:* {now_str}",
    ]

    if notes:
        caption_lines.append(f"📝 *Anotações:* _{notes}_")

    caption_lines.append("━━━━━━━━━━━━━━━━━━━━")
    caption_lines.append("🎯 _Consistência diária do casal!_")

    message_text = "\n".join(caption_lines)

    for channel_id, thread_id in targets:
        try:
            if photo_file_id:
                await bot.send_photo(
                    chat_id=channel_id,
                    message_thread_id=thread_id,
                    photo=photo_file_id,
                    caption=message_text,
                    parse_mode="Markdown"
                )
            else:
                await bot.send_message(
                    chat_id=channel_id,
                    message_thread_id=thread_id,
                    text=message_text,
                    parse_mode="Markdown"
                )
            logger.info(f"Comprovante encaminhado com sucesso para {channel_id} (tópico: {thread_id})")
        except Exception as e:
            logger.error(f"Erro ao encaminhar comprovante para {channel_id} (tópico: {thread_id}): {e}")


@router.message(Command("estudar"))
async def cmd_estudar(message: Message, state: FSMContext):
    """
    Inicia o fluxo de registro de estudo via teclado inline.
    Exibe as 6 disciplinas mais usadas, com botão de ver mais caso haja outras.
    """
    await state.clear()
    await state.set_state(StudyRegistrationFSM.choosing_subject)

    async with async_session() as session:
        top_names, all_names = await crud.get_top_and_all_subjects(session, top_limit=6)

    has_more = len(all_names) > len(top_names)

    await message.answer(
        text="📖 *Hora de registrar seu progresso!*\n\n"
             "Selecione abaixo a *disciplina* que você estudou:",
        parse_mode="Markdown",
        reply_markup=get_subjects_keyboard(subjects=top_names, has_more=has_more, show_all=False)
    )


@router.callback_query(F.data == "show_more_subjects", StudyRegistrationFSM.choosing_subject)
async def process_show_more_subjects(callback: CallbackQuery):
    """
    Expande a lista para exibir todas as matérias cadastradas.
    """
    async with async_session() as session:
        top_names, all_names = await crud.get_top_and_all_subjects(session, top_limit=6)

    await callback.message.edit_text(
        text="📖 *Todas as Disciplinas Cadastradas:*\n\n"
             "Selecione a disciplina que você estudou:",
        parse_mode="Markdown",
        reply_markup=get_subjects_keyboard(subjects=all_names, has_more=False, show_all=True)
    )
    await callback.answer()


@router.callback_query(F.data == "show_top_subjects", StudyRegistrationFSM.choosing_subject)
async def process_show_top_subjects(callback: CallbackQuery):
    """
    Recolhe a lista para exibir apenas as 6 mais usadas.
    """
    async with async_session() as session:
        top_names, all_names = await crud.get_top_and_all_subjects(session, top_limit=6)

    has_more = len(all_names) > len(top_names)
    await callback.message.edit_text(
        text="📖 *Hora de registrar seu progresso!*\n\n"
             "Selecione abaixo a *disciplina* que você estudou:",
        parse_mode="Markdown",
        reply_markup=get_subjects_keyboard(subjects=top_names, has_more=has_more, show_all=False)
    )
    await callback.answer()


@router.callback_query(SubjectCallback.filter(), StudyRegistrationFSM.choosing_subject)
async def process_subject_chosen(callback: CallbackQuery, callback_data: SubjectCallback, state: FSMContext):
    """
    Recebe a matéria escolhida e edita a mensagem para apresentar os botões de tempo.
    """
    subject_name = callback_data.name
    await state.update_data(chosen_subject=subject_name)
    await state.set_state(StudyRegistrationFSM.choosing_duration)

    await callback.message.edit_text(
        text=f"📚 Matéria selecionada: *{subject_name}*\n\n"
             f"Quanto tempo você dedicou a esta sessão?",
        parse_mode="Markdown",
        reply_markup=get_durations_keyboard(selected_subject=subject_name)
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_subjects", StudyRegistrationFSM.choosing_duration)
async def process_back_to_subjects(callback: CallbackQuery, state: FSMContext):
    """
    Permite voltar para a escolha da matéria sem perder o fluxo.
    """
    await state.set_state(StudyRegistrationFSM.choosing_subject)
    async with async_session() as session:
        top_names, all_names = await crud.get_top_and_all_subjects(session, top_limit=6)

    has_more = len(all_names) > len(top_names)
    await callback.message.edit_text(
        text="📖 *Hora de registrar seu progresso!*\n\n"
             "Selecione abaixo a *disciplina* que você estudou:",
        parse_mode="Markdown",
        reply_markup=get_subjects_keyboard(subjects=top_names, has_more=has_more, show_all=False)
    )
    await callback.answer()


@router.callback_query(DurationCallback.filter(), StudyRegistrationFSM.choosing_duration)
async def process_duration_chosen(callback: CallbackQuery, callback_data: DurationCallback, state: FSMContext):
    """
    Recebe a duração e solicita a foto como comprovante para o canal.
    """
    minutes = callback_data.minutes
    data = await state.get_data()
    subject_name = data.get("chosen_subject", "Estudo Geral")

    await state.update_data(chosen_duration=minutes)
    await state.set_state(StudyRegistrationFSM.waiting_photo)

    duration_str = format_duration(minutes)
    await callback.message.edit_text(
        text=(
            f"📚 *{subject_name}* — ⏱️ *{duration_str}*\n\n"
            f"📸 *Comprovante de Estudos (Opcional):*\n"
            f"Envie uma *foto* agora para registrar o que você estudou (você pode incluir uma legenda descrevendo o conteúdo).\n\n"
            f"_O comprovante será postado no canal do casal! Ou clique em Pular Foto abaixo:_"
        ),
        parse_mode="Markdown",
        reply_markup=get_photo_prompt_keyboard()
    )
    await callback.answer()


@router.message(F.photo, StudyRegistrationFSM.waiting_photo)
async def process_photo_received(message: Message, state: FSMContext):
    """
    Salva o registro com a foto anexada e a legenda como anotação.
    """
    data = await state.get_data()
    subject_name = data.get("chosen_subject", "Estudo Geral")
    minutes = data.get("chosen_duration", 30)

    photo_file_id = message.photo[-1].file_id
    notes = message.caption or None
    user = message.from_user

    async with async_session() as session:
        session_obj, current_streak, streak_increased = await crud.add_study_session(
            session=session,
            telegram_id=user.id,
            first_name=user.first_name,
            username=user.username,
            subject=subject_name,
            duration_minutes=minutes,
            photo_file_id=photo_file_id,
            notes=notes
        )

    # Encaminha o comprovante com a foto para o canal
    await forward_to_evidence_channel(
        bot=message.bot,
        user_name=user.first_name,
        subject=subject_name,
        minutes=minutes,
        streak=current_streak,
        photo_file_id=photo_file_id,
        notes=notes
    )

    duration_str = format_duration(minutes)
    streak_msg = f"🔥 *Ofensiva:* {current_streak} dia(s) consecutivo(s)!"
    if streak_increased and current_streak > 1:
        streak_msg += " 📈 _Ofensiva aumentada!_"

    await message.answer(
        text=(
            f"✅ *Estudo Comprovado e Registrado!*\n\n"
            f"👤 Estudante: *{user.first_name}*\n"
            f"📚 Disciplina: *{subject_name}*\n"
            f"⏱️ Tempo: *{duration_str}*\n"
            f"📸 *Foto:* Enviada com sucesso para o canal do casal!\n\n"
            f"{streak_msg}\n\n"
            f"🏆 _Parabéns pelo foco de hoje!_"
        ),
        parse_mode="Markdown"
    )
    await state.clear()


@router.callback_query(F.data == "skip_photo", StudyRegistrationFSM.waiting_photo)
async def process_skip_photo(callback: CallbackQuery, state: FSMContext):
    """
    Salva o registro sem foto quando o usuário prefere pular essa etapa.
    """
    data = await state.get_data()
    subject_name = data.get("chosen_subject", "Estudo Geral")
    minutes = data.get("chosen_duration", 30)
    user = callback.from_user

    async with async_session() as session:
        session_obj, current_streak, streak_increased = await crud.add_study_session(
            session=session,
            telegram_id=user.id,
            first_name=user.first_name,
            username=user.username,
            subject=subject_name,
            duration_minutes=minutes,
            photo_file_id=None,
            notes=None
        )

    # Encaminha o registro em texto para o canal
    await forward_to_evidence_channel(
        bot=callback.bot,
        user_name=user.first_name,
        subject=subject_name,
        minutes=minutes,
        streak=current_streak,
        photo_file_id=None,
        notes=None
    )

    duration_str = format_duration(minutes)
    streak_msg = f"🔥 *Ofensiva:* {current_streak} dia(s) consecutivo(s)!"
    if streak_increased and current_streak > 1:
        streak_msg += " 📈 _Ofensiva aumentada!_"

    await callback.message.edit_text(
        text=(
            f"✅ *Sessão Registrada com Sucesso!*\n\n"
            f"👤 Estudante: *{user.first_name}*\n"
            f"📚 Disciplina: *{subject_name}*\n"
            f"⏱️ Tempo: *{duration_str}*\n\n"
            f"{streak_msg}\n\n"
            f"📢 _Registro postado no canal do casal!_"
        ),
        parse_mode="Markdown"
    )
    await callback.answer(text=f"Registrado: +{duration_str} de {subject_name}!", show_alert=False)
    await state.clear()


@router.callback_query(F.data == "cancel_action")
async def process_cancel(callback: CallbackQuery, state: FSMContext):
    """
    Cancela o fluxo atual e limpa a FSM.
    """
    await state.clear()
    await callback.message.edit_text(
        text="❌ Registro de estudos cancelado.",
        reply_markup=None
    )
    await callback.answer()
