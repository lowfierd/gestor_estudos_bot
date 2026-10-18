from datetime import date, timedelta
from typing import Any
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, StudySession, RegisteredGroup, RegisteredChannel, Subject


async def get_or_create_user(
    session: AsyncSession,
    telegram_id: int,
    first_name: str,
    username: str | None = None
) -> User:
    """
    Busca um usuário pelo telegram_id ou o cria caso não exista.
    Atualiza o first_name e username caso tenham mudado.
    """
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            telegram_id=telegram_id,
            first_name=first_name,
            username=username,
            streak_count=0,
            last_study_date=None
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
    else:
        # Atualiza dados cadastrais se mudaram no Telegram
        updated = False
        if user.first_name != first_name:
            user.first_name = first_name
            updated = True
        if user.username != username:
            user.username = username
            updated = True
        if updated:
            await session.commit()
            await session.refresh(user)

    return user


async def get_user(session: AsyncSession, telegram_id: int) -> User | None:
    """
    Retorna o usuário pelo telegram_id ou None.
    """
    stmt = select(User).where(User.telegram_id == telegram_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_all_users(session: AsyncSession) -> list[User]:
    """
    Retorna todos os usuários cadastrados.
    """
    stmt = select(User).order_by(User.first_name.asc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


def calculate_new_streak(current_streak: int, last_date: date | None, today: date) -> tuple[int, bool]:
    """
    Calcula o novo streak e informa se a ofensiva aumentou.
    Retorna: (novo_streak, aumentou_ofensiva)
    """
    if last_date is None:
        return 1, True

    if last_date == today:
        # Já estudou hoje, mantém a contagem atual
        return current_streak, False

    # Verificação de dia consecutivo de ontem
    if last_date == today - timedelta(days=1):
        return current_streak + 1, True

    # Se passou mais de 1 dia, quebrou a ofensiva e reinicia em 1
    return 1, True


async def add_study_session(
    session: AsyncSession,
    telegram_id: int,
    first_name: str,
    username: str | None,
    subject: str,
    duration_minutes: int,
    session_date: date | None = None,
    photo_file_id: str | None = None,
    notes: str | None = None
) -> tuple[StudySession, int, bool]:
    """
    Registra uma sessão de estudo, calcula e persiste a ofensiva (streak),
    com suporte a comprovante em foto e anotações.
    Retorna: (sessao_criada, streak_atual, streak_aumentou)
    """
    if session_date is None:
        session_date = date.today()

    user = await get_or_create_user(session, telegram_id, first_name, username)

    new_streak, streak_increased = calculate_new_streak(
        current_streak=user.streak_count,
        last_date=user.last_study_date,
        today=session_date
    )

    user.streak_count = new_streak
    user.last_study_date = session_date

    study_session = StudySession(
        user_id=telegram_id,
        subject=subject,
        duration_minutes=duration_minutes,
        session_date=session_date,
        photo_file_id=photo_file_id,
        notes=notes
    )
    session.add(study_session)

    # Atualiza a contagem de uso da disciplina
    subj_stmt = select(Subject).where(Subject.name == subject)
    subj_res = await session.execute(subj_stmt)
    subj_obj = subj_res.scalar_one_or_none()
    if subj_obj:
        subj_obj.use_count += 1
    else:
        session.add(Subject(name=subject, use_count=1))

    await session.commit()
    await session.refresh(study_session)
    await session.refresh(user)

    return study_session, user.streak_count, streak_increased


async def get_today_study_status(
    session: AsyncSession,
    target_date: date | None = None
) -> dict[int, dict[str, Any]]:
    """
    Verifica o status de estudo de todos os usuários para um determinado dia (útil para os Nudges às 20h).
    Retorna um dicionário:
    {
        telegram_id: {
            "user": User,
            "studied_today": bool,
            "total_minutes": int
        }
    }
    """
    if target_date is None:
        target_date = date.today()

    users = await get_all_users(session)

    stmt = (
        select(
            StudySession.user_id,
            func.coalesce(func.sum(StudySession.duration_minutes), 0).label("total_minutes")
        )
        .where(StudySession.session_date == target_date)
        .group_by(StudySession.user_id)
    )
    result = await session.execute(stmt)
    today_records = {row.user_id: row.total_minutes for row in result.all()}

    status: dict[int, dict[str, Any]] = {}
    for u in users:
        minutes = today_records.get(u.telegram_id, 0)
        status[u.telegram_id] = {
            "user": u,
            "studied_today": minutes > 0,
            "total_minutes": minutes
        }

    return status


async def get_weekly_stats(
    session: AsyncSession,
    start_date: date,
    end_date: date
) -> dict[str, Any]:
    """
    Compila as estatísticas da semana para alimentar o gerador de gráficos do Matplotlib.
    Retorna totais por usuário e divisão percentual de matérias.
    """
    # 1. Total de minutos por usuário na semana
    user_totals_stmt = (
        select(
            User.telegram_id,
            User.first_name,
            func.coalesce(func.sum(StudySession.duration_minutes), 0).label("total_minutes")
        )
        .join(StudySession, StudySession.user_id == User.telegram_id)
        .where(StudySession.session_date.between(start_date, end_date))
        .group_by(User.telegram_id, User.first_name)
    )
    user_results = await session.execute(user_totals_stmt)
    user_data = [
        {"telegram_id": row.telegram_id, "name": row.first_name, "minutes": row.total_minutes}
        for row in user_results.all()
    ]

    # 2. Total por disciplina (para gráfico de pizza geral do casal)
    subject_stmt = (
        select(
            StudySession.subject,
            func.sum(StudySession.duration_minutes).label("total_minutes")
        )
        .where(StudySession.session_date.between(start_date, end_date))
        .group_by(StudySession.subject)
        .order_by(func.sum(StudySession.duration_minutes).desc())
    )
    subject_results = await session.execute(subject_stmt)
    subject_data = [
        {"subject": row.subject, "minutes": row.total_minutes}
        for row in subject_results.all()
    ]

    return {
        "period": (start_date, end_date),
        "users": user_data,
        "subjects": subject_data
    }


async def register_group(session: AsyncSession, chat_id: int, title: str | None = None) -> RegisteredGroup:
    """
    Registra ou atualiza o grupo mútuo do casal automaticamente.
    """
    stmt = select(RegisteredGroup).where(RegisteredGroup.chat_id == chat_id)
    result = await session.execute(stmt)
    group = result.scalar_one_or_none()

    if not group:
        group = RegisteredGroup(chat_id=chat_id, title=title)
        session.add(group)
        await session.commit()
        await session.refresh(group)
    elif title and group.title != title:
        group.title = title
        await session.commit()
        await session.refresh(group)

    return group


async def get_registered_groups(session: AsyncSession) -> list[RegisteredGroup]:
    """
    Retorna os grupos registrados onde o bot está ativo.
    """
    stmt = select(RegisteredGroup)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def register_channel(
    session: AsyncSession,
    channel_id: int,
    title: str | None = None,
    username: str | None = None,
    message_thread_id: int | None = None
) -> RegisteredChannel:
    """
    Registra ou atualiza o destino oficial de comprovantes (canal ou tópico de grupo/fórum).
    """
    stmt = select(RegisteredChannel).where(RegisteredChannel.channel_id == channel_id)
    result = await session.execute(stmt)
    channel = result.scalar_one_or_none()

    if not channel:
        channel = RegisteredChannel(
            channel_id=channel_id,
            title=title,
            username=username,
            message_thread_id=message_thread_id
        )
        session.add(channel)
        await session.commit()
        await session.refresh(channel)
    else:
        updated = False
        if title and channel.title != title:
            channel.title = title
            updated = True
        if username and channel.username != username:
            channel.username = username
            updated = True
        if message_thread_id is not None and channel.message_thread_id != message_thread_id:
            channel.message_thread_id = message_thread_id
            updated = True
        if updated:
            await session.commit()
            await session.refresh(channel)

    return channel


async def get_registered_channels(session: AsyncSession) -> list[RegisteredChannel]:
    """
    Retorna os canais cadastrados para envio de comprovantes.
    """
    stmt = select(RegisteredChannel)
    result = await session.execute(stmt)
    return list(result.scalars().all())


# Matérias iniciais padrão caso o banco esteja novo
INITIAL_SUBJECTS = ["Direito", "Programação", "Idiomas", "Concursos", "Leitura / Geral", "Matemática"]


async def ensure_default_subjects(session: AsyncSession) -> None:
    """
    Garante que existam matérias padrão no banco caso a tabela esteja vazia.
    """
    stmt = select(func.count(Subject.id))
    result = await session.execute(stmt)
    count = result.scalar() or 0
    if count == 0:
        for name in INITIAL_SUBJECTS:
            session.add(Subject(name=name, use_count=0))
        await session.commit()


async def add_subject(session: AsyncSession, name: str) -> tuple[Subject, bool]:
    """
    Cadastra uma nova disciplina. Retorna (subject, criado_novo: bool).
    """
    clean_name = name.strip()
    stmt = select(Subject).where(func.lower(Subject.name) == func.lower(clean_name))
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        return existing, False

    subject = Subject(name=clean_name, use_count=0)
    session.add(subject)
    await session.commit()
    await session.refresh(subject)
    return subject, True


async def remove_subject(session: AsyncSession, name_or_id: str | int) -> bool:
    """
    Remove uma disciplina cadastrada pelo nome ou ID.
    """
    if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdigit()):
        stmt = delete(Subject).where(Subject.id == int(name_or_id))
    else:
        stmt = delete(Subject).where(func.lower(Subject.name) == func.lower(str(name_or_id).strip()))
    
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount > 0


async def get_all_subjects(session: AsyncSession) -> list[Subject]:
    """
    Retorna todas as disciplinas ordenadas pelas mais usadas (use_count desc).
    """
    await ensure_default_subjects(session)
    stmt = select(Subject).order_by(Subject.use_count.desc(), Subject.name.asc())
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_top_and_all_subjects(session: AsyncSession, top_limit: int = 6) -> tuple[list[str], list[str]]:
    """
    Retorna uma tupla: (top_6_materias, todas_as_materias) ordenadas por frequência.
    """
    subjects = await get_all_subjects(session)
    all_names = [s.name for s in subjects]
    top_names = all_names[:top_limit]
    return top_names, all_names



