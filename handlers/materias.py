from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from database.models import async_session
from database import crud
from utils.teclados import RemoveSubjectCallback, get_remove_subjects_keyboard

router = Router(name="materias_router")


@router.message(Command("addmateria", "adicionarmateria", "novamateria"))
async def cmd_add_materia(message: Message):
    """
    Cadastra uma nova disciplina no banco de dados.
    Exemplo: /addmateria Economia
    """
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer(
            "⚠️ *Como adicionar uma disciplina:*\n\n"
            "Digite o comando seguido do nome da matéria.\n"
            "Exemplo: `/addmateria Economia` ou `/addmateria Direito Civil`",
            parse_mode="Markdown"
        )
        return

    materia_nome = parts[1].strip()
    if len(materia_nome) > 40:
        await message.answer("❌ O nome da disciplina deve ter no máximo 40 caracteres.")
        return

    async with async_session() as session:
        subj, created = await crud.add_subject(session, materia_nome)

    if created:
        await message.answer(
            f"✅ *Disciplina Cadastrada com Sucesso!*\n\n"
            f"📚 *{subj.name}* agora está disponível na lista de `/estudar`.",
            parse_mode="Markdown"
        )
    else:
        await message.answer(
            f"ℹ️ A disciplina *{subj.name}* já estava cadastrada anteriormente!",
            parse_mode="Markdown"
        )


@router.message(Command("removermateria", "delmateria", "excluirmateria"))
async def cmd_remover_materia(message: Message):
    """
    Apresenta um teclado com as disciplinas para exclusão rápida em 1 clique.
    """
    async with async_session() as session:
        subjects = await crud.get_all_subjects(session)

    if not subjects:
        await message.answer("Nenhuma disciplina cadastrada no momento.")
        return

    await message.answer(
        text="🗑️ *Selecione a disciplina que deseja remover:*",
        parse_mode="Markdown",
        reply_markup=get_remove_subjects_keyboard(subjects)
    )


@router.callback_query(RemoveSubjectCallback.filter())
async def process_remove_subject_chosen(callback: CallbackQuery, callback_data: RemoveSubjectCallback):
    """
    Executa a remoção da disciplina selecionada.
    """
    subject_id = callback_data.id

    async with async_session() as session:
        # Busca o nome antes de apagar
        subjects = await crud.get_all_subjects(session)
        target_name = next((s.name for s in subjects if s.id == subject_id), "Disciplina")
        removed = await crud.remove_subject(session, name_or_id=subject_id)

    if removed:
        await callback.message.edit_text(
            f"🗑️ Disciplina *{target_name}* removida com sucesso!\n"
            f"Ela não aparecerá mais no menu de `/estudar`.",
            parse_mode="Markdown"
        )
        await callback.answer(f"Removida: {target_name}")
    else:
        await callback.message.edit_text("❌ A disciplina não foi encontrada ou já havia sido removida.")
        await callback.answer()


@router.message(Command("materias", "disciplinas"))
async def cmd_listar_materias(message: Message):
    """
    Lista todas as disciplinas e a frequência de estudo de cada uma.
    """
    async with async_session() as session:
        subjects = await crud.get_all_subjects(session)

    if not subjects:
        await message.answer("Nenhuma disciplina cadastrada. Use `/addmateria Nome` para criar.")
        return

    lines = ["📚 *Disciplinas Cadastradas (Mais Frequentes Primeiro):*\n"]
    for idx, s in enumerate(subjects, 1):
        vezes_str = f"({s.use_count}x estudada)" if s.use_count > 0 else "(ainda não estudada)"
        destaque = "⭐" if idx <= 6 else "•"
        lines.append(f"{destaque} *{s.name}* {vezes_str}")

    lines.append("\n_As 6 primeiras com ⭐ são as que aparecem no menu principal do `/estudar`._")
    lines.append("Para adicionar: `/addmateria Nome` | Para remover: `/removermateria`")

    await message.answer("\n".join(lines), parse_mode="Markdown")
