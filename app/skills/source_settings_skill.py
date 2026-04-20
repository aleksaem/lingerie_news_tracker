from app.db.models import SourceCatalog
from app.repositories.source_catalog_repository import (
    SourceCatalogRepository,
)
from app.repositories.user_source_repository import (
    UserSourceRepository,
)

MAX_SOURCES = 8


class SourceSettingsSkill:

    def __init__(
        self,
        user_source_repo: UserSourceRepository,
        source_catalog_repo: SourceCatalogRepository,
    ):
        self.user_source_repo = user_source_repo
        self.source_catalog_repo = source_catalog_repo

    async def add_source(
        self, user_id: int, source_name: str
    ) -> str:
        """
        Валідує проти каталогу і додає source.
        Нечутливий до регістру пошук в каталозі.
        Повертає текст підтвердження для Telegram.
        """
        source_name = source_name.strip()
        if not source_name:
            return "⚠️ Source name cannot be empty."

        source = await self.source_catalog_repo.find_by_name(
            source_name
        )

        if not source:
            available = await self.source_catalog_repo.get_available_names()
            available_text = "\n".join(
                f"• {name}" for name in available
            )
            return (
                f"⚠️ *{source_name}* is not in the supported "
                f"sources catalog.\n\n"
                f"Available sources:\n{available_text}"
            )

        current = await self.user_source_repo.list_sources(
            user_id
        )
        if len(current) >= MAX_SOURCES:
            return (
                f"⚠️ You have reached the maximum of "
                f"{MAX_SOURCES} sources.\n"
                f"Please remove one before adding a new one."
            )

        added = await self.user_source_repo.add_source(
            user_id, source.id
        )

        if not added:
            return (
                f"ℹ️ *{source.display_name}* is already "
                f"in your tracked sources."
            )

        await self.user_source_repo.invalidate_source_digests(
            user_id
        )

        return (
            f"✅ *{source.display_name}* added to your "
            f"tracked sources.\n\n"
            f"Next time you tap 📡 News by Sources, "
            f"it will include articles from this publication."
        )

    async def remove_source(
        self, user_id: int, source_id: int
    ) -> str:
        """
        Видаляє source по source_id.
        Повертає текст підтвердження для Telegram.
        """
        source = await self.source_catalog_repo.find_by_id(
            source_id
        )
        display_name = (
            source.display_name if source else f"#{source_id}"
        )

        removed = await self.user_source_repo.remove_source(
            user_id, source_id
        )

        if not removed:
            return (
                f"⚠️ *{display_name}* not found "
                f"in your tracked sources."
            )

        await self.user_source_repo.invalidate_source_digests(
            user_id
        )

        return (
            f"🗑 *{display_name}* removed from your "
            f"tracked sources.\n\n"
            f"Your next News by Sources digest will be updated."
        )

    async def list_sources(
        self, user_id: int
    ) -> list[SourceCatalog]:
        """
        Повертає список SourceCatalog для inline клавіатури.
        """
        return await self.user_source_repo.list_sources(user_id)

    async def get_available_sources_text(self) -> str:
        """
        Повертає відформатований список доступних джерел.
        Використовується в hint повідомленні.
        """
        available = await self.source_catalog_repo.get_available_names()
        return "\n".join(f"• {name}" for name in available)
