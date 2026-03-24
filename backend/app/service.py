from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.auth.repository import AuthRepository
from app.users.repository import UserRepository
from app.tickets.repository import MessageRepository, TicketRepository


class UnitOfWork:
    def __init__(self, async_session_maker: async_sessionmaker[AsyncSession]):
        self._async_session_maker = async_session_maker
        self.session: AsyncSession | None = None
        self.user_repo: UserRepository | None = None
        self.auth_repo: AuthRepository | None = None
        self.ticket_repo: TicketRepository | None = None
        self.message_repo: MessageRepository | None = None

    async def __aenter__(self):
        self.session = self._async_session_maker()
        self.user_repo = UserRepository(self.session)
        self.auth_repo = AuthRepository(self.session)
        self.ticket_repo = TicketRepository(self.session)
        self.message_repo = MessageRepository(self.session)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type is not None and self.session is not None:
                await self.rollback()
            # else:
            #     await self.commit()
        finally:
            if self.session is not None:
                await self.session.close()
            self.session = None

    async def commit(self):
        if self.session is None:
            raise RuntimeError("Session is not initialized")
        try:
            await self.session.commit()
        except Exception:
            await self.rollback()
            raise

    async def rollback(self):
        if self.session is None:
            raise RuntimeError("Session is not initialized")
        await self.session.rollback()
