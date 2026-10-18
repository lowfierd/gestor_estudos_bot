from datetime import date, timedelta
from typing import Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, StudySession


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
    session_date: date | None = None
) -> tuple[StudySession, int, bool]:
    """
    Registra uma sessão de estudo, calcula e persiste a ofensiva (streak).
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
        session_date=session_date
    )
    session.add(study_session)

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
