from aiogram import Router
from aiogram.types import Message, CallbackQuery
from app.bot.keyboards.sources_menu import get_sources_keyboard
from app.bot.utils import send_digest
from app.skills.news_by_sources_skill import NewsBySourcesSkill

router = Router()


def setup_source_news_handler(
    skill: NewsBySourcesSkill,
) -> Router:

    @router.message(lambda m: m.text == "📡 News by Sources")
    async def source_news_handler(message: Message):
        user_id = message.from_user.id

        try:
            text, source_pairs = await skill.execute_menu(
                user_id
            )

            # Немає sources — показуємо підказку
            if source_pairs is None:
                await message.answer(
                    text,
                    parse_mode="Markdown",
                )
                return

            # Є sources — показуємо inline клавіатуру
            await message.answer(
                text,
                parse_mode="Markdown",
                reply_markup=get_sources_keyboard(source_pairs),
            )

        except Exception as e:
            await message.answer(
                "😔 Something went wrong. "
                "Please try again in a minute."
            )
            print(f"[SourceNewsHandler] Menu error: {e}")
            import traceback
            traceback.print_exc()

    @router.callback_query(
        lambda c: c.data and c.data.startswith("source:")
    )
    async def source_selected_callback(
        callback: CallbackQuery,
    ):
        user_id = callback.from_user.id
        source_value = callback.data.split(":", 1)[1]

        # Знаходимо display_name з тексту натиснутої кнопки
        source_display = source_value  # fallback — slug
        if callback.message.reply_markup:
            for row in callback.message.reply_markup.inline_keyboard:
                for button in row:
                    if button.callback_data == callback.data:
                        source_display = button.text
                        break

        # Прибираємо клавіатуру одразу
        await callback.message.edit_reply_markup(
            reply_markup=None
        )
        await callback.answer()

        # All режим
        if source_value == "__all__":
            wait_msg = await callback.message.answer(
                "⏳ Gathering news from all your sources, "
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
                    f"[SourceNewsHandler] execute_all error: {e}"
                )
                import traceback
                traceback.print_exc()
            return

        # Конкретний source
        wait_msg = await callback.message.answer(
            f"⏳ Gathering news from *{source_display}*, "
            f"please wait...",
            parse_mode="Markdown",
        )
        deleted = False
        try:
            header, blocks = await skill.execute_source(
                user_id, source_value
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
                f"[SourceNewsHandler] execute_source error: {e}"
            )
            import traceback
            traceback.print_exc()

    return router
