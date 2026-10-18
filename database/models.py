from datetime import datetime, date
from sqlalchemy import BigInteger, String, Integer, Date, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, create_async_engine, async_sessionmaker, AsyncSession

try:
    from config import DATABASE_URL
except ImportError:
    DATABASE_URL = "sqlite+aiosqlite:///gestor_estudos.db"

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    """
    Representa os usuários do bot (o casal de estudantes).
    Mantém o histórico de ofensiva (streak) e perfil básico do Telegram.
    """
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    first_name: Mapped[str] = mapped_column(String(120), nullable=False)
    username: Mapped[str | None] = mapped_column(String(120), nullable=True)
    streak_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_study_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relacionamento com as sessões de estudo
    sessions: Mapped[list["StudySession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        order_by="desc(StudySession.created_at)"
    )

    def __repr__(self) -> str:
        return f"<User telegram_id={self.telegram_id} name='{self.first_name}' streak={self.streak_count}>"


class StudySession(Base):
    """
    Registros de cada sessão de estudo realizada por um usuário.
    """
    __tablename__ = "study_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.telegram_id", ondelete="CASCADE"), nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    session_date: Mapped[date] = mapped_column(Date, default=date.today, nullable=False, index=True)
    photo_file_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relacionamento de volta com o usuário
    user: Mapped["User"] = relationship(back_populates="sessions")

    def __repr__(self) -> str:
        return f"<StudySession id={self.id} user_id={self.user_id} subject='{self.subject}' duration={self.duration_minutes}m>"


class RegisteredGroup(Base):
    """
    Armazena o ID dos grupos onde o bot foi adicionado para envio automático de avisos.
    """
    __tablename__ = "registered_groups"

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<RegisteredGroup chat_id={self.chat_id} title='{self.title}'>"


class RegisteredChannel(Base):
    """
    Armazena o canal oficial para onde o bot encaminha os comprovantes com foto e relatório de estudos.
    """
    __tablename__ = "registered_channels"

    channel_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<RegisteredChannel channel_id={self.channel_id} title='{self.title}'>"


async def init_db() -> None:
    """
    Cria as tabelas no banco de dados caso ainda não existam.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
