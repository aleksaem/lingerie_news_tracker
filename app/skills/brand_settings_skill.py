from datetime import date
from typing import List, Optional
from app.repositories.user_brand_repository import UserBrandRepository
from app.repositories.user_topic_repository import UserTopicRepository
from app.repositories.digest_repository import DigestRepository

MAX_BRANDS = 10


class BrandSettingsSkill:

    def __init__(
        self,
        user_brand_repo: UserBrandRepository,
        digest_repo: DigestRepository,
        user_topic_repo: Optional[UserTopicRepository] = None,
    ):
        self.user_brand_repo = user_brand_repo
        self.digest_repo = digest_repo
        self.user_topic_repo = user_topic_repo or UserTopicRepository(
            user_brand_repo.session
        )

    async def add_brand(self, user_id: int, brand_name: str) -> str:
        brand_name = brand_name.strip()

        if not brand_name:
            return "⚠️ Brand name cannot be empty. Please try again."

        if len(brand_name) > 100:
            return "⚠️ Brand name is too long. Max 100 characters."

        brands = await self.user_brand_repo.list_brands(user_id)
        if len(brands) >= MAX_BRANDS:
            return (
                f"⚠️ You have reached the maximum of {MAX_BRANDS} brands.\n"
                f"Please remove one before adding a new one."
            )

        added = await self.user_brand_repo.add_brand(user_id, brand_name)

        if not added:
            return f"ℹ️ *{brand_name}* is already in your tracked brands."

        await self.digest_repo.invalidate(
            date.today().isoformat(),
            digest_type="competitors",
            user_id=user_id,
        )

        return (
            f"✅ *{brand_name}* added to your tracked brands.\n\n"
            f"Next time you tap 🏷 Competitors, "
            f"it will include news about this brand."
        )

    async def remove_brand(self, user_id: int, brand_name: str) -> str:
        removed = await self.user_brand_repo.remove_brand(user_id, brand_name)

        if not removed:
            return f"⚠️ *{brand_name}* not found in your tracked brands."

        await self.digest_repo.invalidate(
            date.today().isoformat(),
            digest_type="competitors",
            user_id=user_id,
        )

        return (
            f"🗑 *{brand_name}* removed from your tracked brands.\n\n"
            f"Your next Competitors digest will be updated."
        )

    async def get_settings_text(self, user_id: int) -> str:
        brands = await self.user_brand_repo.list_brands(user_id)
        topics = await self.user_topic_repo.list_topics(user_id)

        lines = ["⚙️ *Your personalized settings*\n"]

        lines.append("*Tracked competitor brands:*")
        if brands:
            for brand in brands:
                lines.append(f"• {brand}")
        else:
            lines.append("_None yet. Add brands via Settings._")

        lines.append("")

        lines.append("*Tracked topics:*")
        if topics:
            for topic in topics:
                lines.append(f"• {topic}")
        else:
            lines.append("_None yet. Add topics via Settings._")

        lines.append(
            f"\nBrands: {len(brands)} · Topics: {len(topics)}"
        )

        return "\n".join(lines)

    async def list_brands(self, user_id: int) -> List[str]:
        return await self.user_brand_repo.list_brands(user_id)
