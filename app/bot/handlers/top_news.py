from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from app.bot.keyboards.main_menu import get_main_keyboard
from app.skills.top_news_skill import TopNewsSkill

router = Router()

LIMIT = 4096


def setup_handlers(skill: TopNewsSkill) -> Router:
    @router.message(Command("start"))
    async def start_handler(message: Message):
        await message.answer(
            "👋 Привіт! Я слідкую за fashion та lingerie новинами.\n"
            "Натисни кнопку нижче щоб отримати дайджест за сьогодні.",
            reply_markup=get_main_keyboard(),
        )

    @router.message(lambda m: m.text == "📰 Top News")
    async def top_news_handler(message: Message):
        wait_msg = await message.answer("⏳ Збираю новини, зачекай хвилинку...")

        try:
            header, blocks = await skill.execute()
            await wait_msg.delete()

            # cache hit or error string — blocks is None
            if blocks is None:
                text = header
                if len(text) <= LIMIT:
                    await message.answer(text, parse_mode="Markdown",
                                         disable_web_page_preview=True)
                else:
                    for i in range(0, len(text), LIMIT):
                        await message.answer(text[i:i + LIMIT], parse_mode="Markdown",
                                             disable_web_page_preview=True)
                return

            # new pipeline — split at article boundaries
            current = header
            for block in blocks:
                candidate = current + "\n\n" + block
                if len(candidate) <= LIMIT:
                    current = candidate
                else:
                    await message.answer(current.strip(), parse_mode="Markdown",
                                         disable_web_page_preview=True)
                    current = block

            if current.strip():
                await message.answer(current.strip(), parse_mode="Markdown",
                                     disable_web_page_preview=True)

        except Exception as e:
            await wait_msg.delete()
            await message.answer("😔 Щось пішло не так. Спробуй ще раз через хвилину.")
            print(f"[TopNewsHandler] Error: {e}")

    return router
