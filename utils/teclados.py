from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# CallbackData tipados para aiogram 3.x
class SubjectCallback(CallbackData, prefix="subj"):
    name: str

class DurationCallback(CallbackData, prefix="dur"):
    minutes: int

# Lista padrão de matérias para estudos do casal
DEFAULT_SUBJECTS = [
    "Direito",
    "Programação",
    "Idiomas",
    "Concursos",
    "Leitura / Geral"
]

# Opções de tempo disponíveis para estudo
DURATION_OPTIONS = [
    ("⏱️ 30 min", 30),
    ("⏳ 1 hora", 60),
    ("⚡ 1h 30m", 90),
    ("🔥 2 horas", 120),
    ("🚀 3 horas", 180)
]


def get_subjects_keyboard(subjects: list[str] | None = None) -> InlineKeyboardMarkup:
    """
    Gera o teclado inline com as opções de matérias para início do registro.
    """
    if subjects is None:
        subjects = DEFAULT_SUBJECTS

    builder = InlineKeyboardBuilder()

    # Adiciona cada matéria em linhas individuais ou em pares para boa usabilidade
    for subject in subjects:
        builder.button(
            text=f"📚 {subject}",
            callback_data=SubjectCallback(name=subject).pack()
        )

    # 1 coluna para legibilidade em telas de celular
    builder.adjust(1)

    # Botão de cancelar
    builder.row(
        InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel_action")
    )

    return builder.as_markup()


def get_durations_keyboard(selected_subject: str) -> InlineKeyboardMarkup:
    """
    Gera o teclado inline com as opções de tempo de estudo após selecionar a matéria.
    """
    builder = InlineKeyboardBuilder()

    for label, minutes in DURATION_OPTIONS:
        builder.button(
            text=label,
            callback_data=DurationCallback(minutes=minutes).pack()
        )

    # Organiza os botões em 2 colunas para ficar visualmente compacto
    builder.adjust(2)

    # Botão para trocar matéria ou cancelar
    builder.row(
        InlineKeyboardButton(text="⬅️ Trocar Matéria", callback_data="back_to_subjects"),
        InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel_action")
    )

    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado simples apenas com botão de cancelar.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Cancelar", callback_data="cancel_action")
    return builder.as_markup()


def get_photo_prompt_keyboard() -> InlineKeyboardMarkup:
    """
    Teclado com opção de pular foto ou cancelar o registro.
    """
    builder = InlineKeyboardBuilder()
    builder.button(text="⏭️ Pular Foto (Salvar direto)", callback_data="skip_photo")
    builder.button(text="❌ Cancelar", callback_data="cancel_action")
    builder.adjust(1)
    return builder.as_markup()

