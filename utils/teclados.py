from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# CallbackData tipados para aiogram 3.x
class SubjectCallback(CallbackData, prefix="subj"):
    name: str

class RemoveSubjectCallback(CallbackData, prefix="delsubj"):
    id: int

class DurationCallback(CallbackData, prefix="dur"):
    minutes: int

# Opções de tempo disponíveis para estudo
DURATION_OPTIONS = [
    ("⏱️ 30 min", 30),
    ("⏳ 1 hora", 60),
    ("⚡ 1h 30m", 90),
    ("🔥 2 horas", 120),
    ("🚀 3 horas", 180)
]


def get_subjects_keyboard(
    subjects: list[str],
    has_more: bool = False,
    show_all: bool = False
) -> InlineKeyboardMarkup:
    """
    Gera o teclado inline com as opções de matérias.
    Exibe as 6 mais usadas com opção de expandir para ver as demais.
    """
    builder = InlineKeyboardBuilder()

    # Adiciona os botões das matérias (2 por linha para ficar compacto e bonito)
    for subject in subjects:
        builder.button(
            text=f"📚 {subject}",
            callback_data=SubjectCallback(name=subject).pack()
        )
    builder.adjust(2)

    # Botão de expansão / recolhimento
    if has_more and not show_all:
        builder.row(
            InlineKeyboardButton(text="📂 Ver mais disciplinas...", callback_data="show_more_subjects")
        )
    elif show_all:
        builder.row(
            InlineKeyboardButton(text="📁 Mostrar menos disciplinas", callback_data="show_top_subjects")
        )

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

    builder.adjust(2)

    # Botão para trocar matéria ou cancelar
    builder.row(
        InlineKeyboardButton(text="⬅️ Trocar Matéria", callback_data="back_to_subjects"),
        InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel_action")
    )

    return builder.as_markup()


def get_remove_subjects_keyboard(subjects_list: list) -> InlineKeyboardMarkup:
    """
    Gera teclado inline com a lista de disciplinas para remoção com 1 clique.
    """
    builder = InlineKeyboardBuilder()

    for subj in subjects_list:
        builder.button(
            text=f"🗑️ {subj.name}",
            callback_data=RemoveSubjectCallback(id=subj.id).pack()
        )

    builder.adjust(2)
    builder.row(
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
