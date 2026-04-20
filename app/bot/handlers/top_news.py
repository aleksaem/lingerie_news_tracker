from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from app.bot.keyboards.main_menu import get_main_keyboard
from app.bot.utils import send_digest
from app.skills.top_news_skill import TopNewsSkill

router = Router()


def setup_handlers(skill: TopNewsSkill) -> Router:
    @router.message(Command("start"))
    async def start_handler(message: Message):
        await message.answer(
            "👋 Hi! I track fashion and lingerie industry news.\n"
            "Tap a button below to get started.",
            reply_markup=get_main_keyboard(),
        )

    @router.message(lambda m: m.text == "📰 Top News")
    async def top_news_handler(message: Message):
        wait_msg = await message.answer("⏳ Gathering news, please wait...")
        deleted = False
        try:
            result = await skill.execute()
            header, blocks = result if isinstance(result, tuple) \
                else (result, None)
            await send_digest(message, header, blocks)
            try:
                await wait_msg.delete()
                deleted = True
            except Exception:
                pass
        except Exception as e:
            if not deleted:
                try:
                    await wait_msg.delete()
                except Exception:
                    pass
            await message.answer(
                "😔 Something went wrong. "
                "Please try again in a minute."
            )
            print(f"[TopNewsHandler] Error: {e}")
            import traceback
            traceback.print_exc()

    return router
