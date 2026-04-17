from aiogram import Router
from aiogram.types import Message
from app.bot.utils import send_digest
from app.skills.competitors_skill import CompetitorsSkill

router = Router()


def setup_competitors_handler(skill: CompetitorsSkill) -> Router:
    @router.message(lambda m: m.text == "🏷 Competitors")
    async def competitors_handler(message: Message):
        wait_msg = await message.answer("⏳ Gathering competitor news, please wait...")
        try:
            header, blocks = await skill.execute(message.from_user.id)
            await wait_msg.delete()
            await send_digest(message, header, blocks)
        except Exception as e:
            await wait_msg.delete()
            await message.answer("😔 Something went wrong. Please try again in a minute.")
            print(f"[CompetitorsHandler] Error: {e}")

    return router
