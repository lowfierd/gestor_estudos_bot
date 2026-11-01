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
    TimerSubjectCallback,
    get_subjects_keyboard,
    get_durations_keyboard,
    get_photo_prompt_keyboard,
    get_study_mode_keyboard,
    get_timer_subjects_keyboard,
    get_active_timer_keyboard
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
    Ponto de entrada do registro de estudo:
    1. Se já tiver um cronômetro rodando, mostra o status dele e opção de concluir.
    2. Se não tiver, oferece escolher entre Cronômetro ao Vivo ou Registro Manual.
    """
    await state.clear()
    user = message.from_user

    async with async_session() as session:
        active = await crud.get_active_timer(session, user.id)

    if active:
        elapsed_seconds = (datetime.utcnow() - active.start_time).total_seconds()
        elapsed_m = max(1, int(round(elapsed_seconds / 60)))
        duration_str = format_duration(elapsed_m)
        await message.answer(
            text=(
                f"⏱️ *Você já está com um Cronômetro Ativo!*\n\n"
                f"📚 Disciplina: *{active.subject}*\n"
                f"⏳ Tempo em foco: *{duration_str}*\n"
                f"⚡ Status: 🟢 Em andamento...\n\n"
                f"Deseja concluir sua sessão agora?"
            ),
            parse_mode="Markdown",
            reply_markup=get_active_timer_keyboard()
        )
        return

    await message.answer(
        text=(
            f"📖 *Hora de registrar seu progresso, {user.first_name}!*\n\n"
            f"Como você deseja registrar seus estudos agora?"
        ),
        parse_mode="Markdown",
        reply_markup=get_study_mode_keyboard()
    )


@router.callback_query(F.data == "mode_manual")
async def process_mode_manual(callback: CallbackQuery, state: FSMContext):
    """
    Inicia o fluxo tradicional de escolha manual da matéria e duração.
    """
    await state.clear()
    await state.set_state(StudyRegistrationFSM.choosing_subject)

    async with async_session() as session:
        top_names, all_names = await crud.get_top_and_all_subjects(session, top_limit=6)

    has_more = len(all_names) > len(top_names)
    await callback.message.edit_text(
        text="📝 *Registro Manual*\n\n"
             "Selecione abaixo a *disciplina* que você estudou:",
        parse_mode="Markdown",
        reply_markup=get_subjects_keyboard(subjects=top_names, has_more=has_more, show_all=False)
    )
    await callback.answer()


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
        text="❌ Ação cancelada.",
        reply_markup=None
    )
    await callback.answer()


# =========================================================
# FLUXO DO CRONÔMETRO AO VIVO ("Começar agora" / "Terminar")
# =========================================================

@router.message(Command("foco", "timer", "cronometro"))
async def cmd_foco_timer(message: Message, state: FSMContext):
    """
    Comando direto para iniciar ou consultar o cronômetro ao vivo.
    """
    await state.clear()
    user = message.from_user

    async with async_session() as session:
        active = await crud.get_active_timer(session, user.id)

    if active:
        elapsed_seconds = (datetime.utcnow() - active.start_time).total_seconds()
        elapsed_m = max(1, int(round(elapsed_seconds / 60)))
        duration_str = format_duration(elapsed_m)
        await message.answer(
            text=(
                f"⏱️ *Cronômetro em Andamento!*\n\n"
                f"👤 Estudante: *{user.first_name}*\n"
                f"📚 Disciplina: *{active.subject}*\n"
                f"⏳ Tempo em foco até agora: *{duration_str}*\n"
                f"⚡ Status: 🟢 Modo Foco ativo!\n\n"
                f"Clique em *Concluir Estudo* quando terminar ou *Ver Tempo Decorrido* para atualizar:"
            ),
            parse_mode="Markdown",
            reply_markup=get_active_timer_keyboard()
        )
        return

    async with async_session() as session:
        top_names, all_names = await crud.get_top_and_all_subjects(session, top_limit=6)

    has_more = len(all_names) > len(top_names)
    await message.answer(
        text=(
            f"⏱️ *Iniciar Cronômetro de Foco*\n\n"
            f"👤 Estudante: *{user.first_name}*\n"
            f"Selecione abaixo a *disciplina* que você vai focar agora:"
        ),
        parse_mode="Markdown",
        reply_markup=get_timer_subjects_keyboard(subjects=top_names, has_more=has_more, show_all=False)
    )


@router.callback_query(F.data == "mode_timer")
async def process_mode_timer(callback: CallbackQuery, state: FSMContext):
    """
    Acionado a partir do menu do /estudar para abrir a seleção de matéria do cronômetro.
    """
    await state.clear()
    user = callback.from_user

    async with async_session() as session:
        active = await crud.get_active_timer(session, user.id)

    if active:
        elapsed_seconds = (datetime.utcnow() - active.start_time).total_seconds()
        elapsed_m = max(1, int(round(elapsed_seconds / 60)))
        duration_str = format_duration(elapsed_m)
        await callback.message.edit_text(
            text=(
                f"⏱️ *Cronômetro em Andamento!*\n\n"
                f"👤 Estudante: *{user.first_name}*\n"
                f"📚 Disciplina: *{active.subject}*\n"
                f"⏳ Tempo em foco: *{duration_str}*\n"
                f"⚡ Status: 🟢 Ativo!\n\n"
                f"Deseja finalizar ou atualizar?"
            ),
            parse_mode="Markdown",
            reply_markup=get_active_timer_keyboard()
        )
        await callback.answer()
        return

    async with async_session() as session:
        top_names, all_names = await crud.get_top_and_all_subjects(session, top_limit=6)

    has_more = len(all_names) > len(top_names)
    await callback.message.edit_text(
        text=(
            f"⏱️ *Iniciar Cronômetro de Foco*\n\n"
            f"Selecione a *disciplina* para começar:"
        ),
        parse_mode="Markdown",
        reply_markup=get_timer_subjects_keyboard(subjects=top_names, has_more=has_more, show_all=False)
    )
    await callback.answer()


@router.callback_query(F.data == "timer_more_subjects")
async def process_timer_more_subjects(callback: CallbackQuery):
    async with async_session() as session:
        top_names, all_names = await crud.get_top_and_all_subjects(session, top_limit=6)

    await callback.message.edit_text(
        text="⏱️ *Todas as Disciplinas para Foco:*\n\nSelecione a disciplina:",
        parse_mode="Markdown",
        reply_markup=get_timer_subjects_keyboard(subjects=all_names, has_more=False, show_all=True)
    )
    await callback.answer()


@router.callback_query(F.data == "timer_top_subjects")
async def process_timer_top_subjects(callback: CallbackQuery):
    async with async_session() as session:
        top_names, all_names = await crud.get_top_and_all_subjects(session, top_limit=6)

    has_more = len(all_names) > len(top_names)
    await callback.message.edit_text(
        text="⏱️ *Iniciar Cronômetro de Foco*\n\nSelecione a disciplina para começar:",
        parse_mode="Markdown",
        reply_markup=get_timer_subjects_keyboard(subjects=top_names, has_more=has_more, show_all=False)
    )
    await callback.answer()


@router.callback_query(TimerSubjectCallback.filter())
async def process_timer_subject_chosen(callback: CallbackQuery, callback_data: TimerSubjectCallback, state: FSMContext):
    """
    Inicia o cronômetro após a escolha da matéria e salva o estado persistente no banco de dados.
    """
    subject_name = callback_data.name
    user = callback.from_user

    async with async_session() as session:
        await crud.start_active_timer(
            session=session,
            user_id=user.id,
            subject=subject_name,
            chat_id=callback.message.chat.id,
            message_id=callback.message.message_id
        )

    now_str = datetime.now().strftime("%H:%M")

    # Se estiver num grupo compartilhado, envia um aviso motivacional
    if callback.message.chat.type in ["group", "supergroup"]:
        try:
            await callback.message.chat.send_message(
                f"🚀 *{user.first_name}* acabou de iniciar uma sessão de foco em *{subject_name}*! Força! 📚🔥",
                parse_mode="Markdown"
            )
        except Exception:
            pass

    await callback.message.edit_text(
        text=(
            f"⏱️ *Sessão de Foco Iniciada!* 🟢\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Estudante:* {user.first_name}\n"
            f"📚 *Disciplina:* {subject_name}\n"
            f"🕒 *Início:* {now_str}\n"
            f"⚡ *Status:* Concentração máxima ativada!\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"💡 _Deixe o celular de lado e bons estudos! Quando terminar, basta clicar em Concluir Estudo abaixo._"
        ),
        parse_mode="Markdown",
        reply_markup=get_active_timer_keyboard()
    )
    await callback.answer(f"Modo Foco iniciado em {subject_name}!", show_alert=False)


@router.callback_query(F.data == "refresh_timer")
async def process_refresh_timer(callback: CallbackQuery):
    """
    Atualiza o tempo decorrido do cronômetro.
    """
    user = callback.from_user
    async with async_session() as session:
        active = await crud.get_active_timer(session, user.id)

    if not active:
        await callback.answer("Nenhum cronômetro ativo no momento.", show_alert=True)
        return

    seconds = int((datetime.utcnow() - active.start_time).total_seconds())
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    if h > 0:
        time_text = f"{h}h {m}min {s}s"
    else:
        time_text = f"{m}min {s}s"

    await callback.answer(f"⏳ Tempo em foco: {time_text}!", show_alert=True)


@router.message(Command("parar", "concluir"))
async def cmd_parar(message: Message, state: FSMContext):
    """
    Comando para parar o cronômetro diretamente via texto.
    """
    user = message.from_user
    async with async_session() as session:
        timer_info, elapsed_minutes = await crud.stop_active_timer(session, user.id)

    if not timer_info:
        await message.answer("⚠️ Você não tem nenhum cronômetro de estudo ativo no momento. Use `/foco` para iniciar!")
        return

    await state.update_data(chosen_subject=timer_info.subject, chosen_duration=elapsed_minutes)
    await state.set_state(StudyRegistrationFSM.waiting_photo)

    duration_str = format_duration(elapsed_minutes)
    await message.answer(
        text=(
            f"🎉 *Sessão de Foco Concluída!* 🏁\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Estudante: *{user.first_name}*\n"
            f"📚 Disciplina: *{timer_info.subject}*\n"
            f"⏱️ Tempo total de foco: *{duration_str}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📸 *Comprovante de Estudos (Opcional):*\n"
            f"Envie uma *foto* agora para registrar seus estudos no canal oficial do casal, ou clique em *Pular Foto* abaixo:"
        ),
        parse_mode="Markdown",
        reply_markup=get_photo_prompt_keyboard()
    )


@router.callback_query(F.data == "stop_timer")
async def process_stop_timer(callback: CallbackQuery, state: FSMContext):
    """
    Encerra o cronômetro ao vivo pelo botão inline e direciona para comprovante ou salvar.
    """
    user = callback.from_user
    async with async_session() as session:
        timer_info, elapsed_minutes = await crud.stop_active_timer(session, user.id)

    if not timer_info:
        await callback.answer("Nenhum cronômetro ativo encontrado.", show_alert=True)
        return

    await state.update_data(chosen_subject=timer_info.subject, chosen_duration=elapsed_minutes)
    await state.set_state(StudyRegistrationFSM.waiting_photo)

    duration_str = format_duration(elapsed_minutes)
    await callback.message.edit_text(
        text=(
            f"🎉 *Sessão de Foco Concluída!* 🏁\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Estudante: *{user.first_name}*\n"
            f"📚 Disciplina: *{timer_info.subject}*\n"
            f"⏱️ Tempo total de foco: *{duration_str}*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📸 *Comprovante de Estudos (Opcional):*\n"
            f"Envie uma *foto* do que você estudou agora (com ou sem legenda) ou clique no botão abaixo para salvar direto:"
        ),
        parse_mode="Markdown",
        reply_markup=get_photo_prompt_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_timer")
async def process_cancel_timer(callback: CallbackQuery):
    """
    Cancela o cronômetro ativo sem salvar no banco de dados.
    """
    user = callback.from_user
    async with async_session() as session:
        cancelled = await crud.cancel_active_timer(session, user.id)

    if cancelled:
        await callback.message.edit_text(
            text="❌ *Cronômetro cancelado.* Nenhuma hora de estudo foi registrada.",
            reply_markup=None,
            parse_mode="Markdown"
        )
        await callback.answer("Cronômetro cancelado.")
    else:
        await callback.answer("Nenhum cronômetro ativo para cancelar.", show_alert=True)

