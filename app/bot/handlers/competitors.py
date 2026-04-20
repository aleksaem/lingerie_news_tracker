from aiogram import Router
from aiogram.types import Message, CallbackQuery
from app.bot.keyboards.competitors_menu import (
    get_competitors_keyboard,
)
from app.bot.utils import send_digest
from app.skills.competitors_skill import CompetitorsSkill

router = Router()


def setup_competitors_handler(
    skill: CompetitorsSkill,
) -> Router:

    @router.message(lambda m: m.text == "🏷 Competitors")
    async def competitors_handler(message: Message):
        user_id = message.from_user.id
        try:
            text, brands = await skill.execute_menu(user_id)

            if brands is None:
                await message.answer(
                    text, parse_mode="Markdown"
                )
                return

            await message.answer(
                text,
                parse_mode="Markdown",
                reply_markup=get_competitors_keyboard(brands),
            )
        except Exception as e:
            await message.answer(
                "😔 Something went wrong. "
                "Please try again in a minute."
            )
            print(f"[CompetitorsHandler] Menu error: {e}")
            import traceback
            traceback.print_exc()

    @router.callback_query(
        lambda c: c.data
        and c.data.startswith("competitor:")
    )
    async def competitor_selected_callback(
        callback: CallbackQuery,
    ):
        user_id = callback.from_user.id
        value = callback.data.split(":", 1)[1]

        # Конкретний бренд — витягуємо display name з кнопки
        brand_display = value
        if callback.message.reply_markup:
            for row in callback.message.reply_markup\
                    .inline_keyboard:
                for button in row:
                    if button.callback_data == callback.data:
                        brand_display = button.text
                        break

        await callback.message.edit_reply_markup(
            reply_markup=None
        )
        await callback.answer()

        if value == "__all__":
            wait_msg = await callback.message.answer(
                "⏳ Gathering news for all competitors, "
                "please wait..."
            )
            deleted = False
            try:
                header, blocks = await skill.execute_all(
                    user_id
                )
                await send_digest(
                    callback.message, header, blocks
                )
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
                await callback.message.answer(
                    "😔 Something went wrong. "
                    "Please try again in a minute."
                )
                print(
                    f"[CompetitorsHandler] All error: {e}"
                )
                import traceback
                traceback.print_exc()
            return

        wait_msg = await callback.message.answer(
            f"⏳ Gathering news about *{brand_display}*, "
            f"please wait...",
            parse_mode="Markdown",
        )
        deleted = False
        try:
            header, blocks = await skill.execute_brand(
                user_id, value
            )
            await send_digest(
                callback.message, header, blocks
            )
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
            await callback.message.answer(
                "😔 Something went wrong. "
                "Please try again in a minute."
            )
            print(
                f"[CompetitorsHandler] Brand error: {e}"
            )
            import traceback
            traceback.print_exc()

    return router
