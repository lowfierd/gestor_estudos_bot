from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from database.models import async_session
from database import crud
from utils.teclados import (
    SubjectCallback,
    DurationCallback,
    get_subjects_keyboard,
    get_durations_keyboard
)

router = Router(name="registrar_router")


class StudyRegistrationFSM(StatesGroup):
    choosing_subject = State()
    choosing_duration = State()


@router.message(Command("estudar"))
async def cmd_estudar(message: Message, state: FSMContext):
    """
    Inicia o fluxo de registro de estudo via teclado inline.
    """
    await state.clear()
    await state.set_state(StudyRegistrationFSM.choosing_subject)

    await message.answer(
        text="📖 *Hora de registrar seu progresso!*\n\n"
             "Selecione abaixo a *disciplina* que você estudou:",
        parse_mode="Markdown",
        reply_markup=get_subjects_keyboard()
    )


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
    await callback.message.edit_text(
        text="📖 *Hora de registrar seu progresso!*\n\n"
             "Selecione abaixo a *disciplina* que você estudou:",
        parse_mode="Markdown",
        reply_markup=get_subjects_keyboard()
    )
    await callback.answer()


@router.callback_query(DurationCallback.filter(), StudyRegistrationFSM.choosing_duration)
async def process_duration_chosen(callback: CallbackQuery, callback_data: DurationCallback, state: FSMContext):
    """
    Recebe a duração, salva os dados no banco, atualiza a ofensiva (streak) e finaliza o estado.
    """
    minutes = callback_data.minutes
    data = await state.get_data()
    subject_name = data.get("chosen_subject", "Estudo Geral")

    user = callback.from_user
    hours_formatted = f"{minutes // 60}h {minutes % 60}m" if minutes % 60 else f"{minutes // 60}h"
    if minutes < 60:
        hours_formatted = f"{minutes} minutos"

    async with async_session() as session:
        session_obj, current_streak, streak_increased = await crud.add_study_session(
            session=session,
            telegram_id=user.id,
            first_name=user.first_name,
            username=user.username,
            subject=subject_name,
            duration_minutes=minutes
        )

    # Mensagem de gamificação com ofensiva (streak)
    streak_msg = f"🔥 *Ofensiva:* {current_streak} dia(s) consecutivo(s)!"
    if streak_increased and current_streak > 1:
        streak_msg += " 📈 _Você manteve o fogo aceso hoje!_"
    elif current_streak == 1:
        streak_msg += " ✨ _Primeiro dia do ciclo! Continue firme amanhã!_"

    await callback.message.edit_text(
        text=(
            f"✅ *Sessão de Estudo Registrada com Sucesso!*\n\n"
            f"👤 Estudante: *{user.first_name}*\n"
            f"📚 Disciplina: *{subject_name}*\n"
            f"⏱️ Tempo: *{hours_formatted}*\n\n"
            f"{streak_msg}\n\n"
            f"🏆 _Seu parceiro(a) foi avisado(a) ou verá seu avanço no ranking!_"
        ),
        parse_mode="Markdown"
    )
    await callback.answer(text=f"Registrado: +{minutes}m de {subject_name}!", show_alert=False)
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
