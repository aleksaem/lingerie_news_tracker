from aiogram import Router
from aiogram.types import CallbackQuery, Message

from app.bot.keyboards.topics_menu import get_topics_keyboard
from app.bot.utils import send_digest
from app.skills.news_by_topics_skill import NewsByTopicsSkill

router = Router()


def setup_topic_news_handler(skill: NewsByTopicsSkill) -> Router:

    @router.message(lambda m: m.text == "📋 News by Topics")
    async def topic_news_handler(message: Message):
        user_id = message.from_user.id

        try:
            text, topics = await skill.execute_menu(user_id)

            if topics is None:
                await message.answer(
                    text,
                    parse_mode="Markdown",
                )
                return

            await message.answer(
                text,
                parse_mode="Markdown",
                reply_markup=get_topics_keyboard(topics),
            )

        except Exception as e:
            await message.answer(
                "😔 Something went wrong. "
                "Please try again in a minute."
            )
            print(f"[TopicNewsHandler] Error in menu: {e}")
            import traceback
            traceback.print_exc()

    @router.callback_query(
        lambda c: c.data and c.data.startswith("topic:")
    )
    async def topic_selected_callback(callback: CallbackQuery):
        user_id = callback.from_user.id
        topic_value = callback.data.split(":", 1)[1]

        await callback.message.edit_reply_markup(
            reply_markup=None
        )
        await callback.answer()

        if topic_value == "__all__":
            wait_msg = await callback.message.answer(
                "⏳ Gathering news for all your topics, "
                "please wait..."
            )
            try:
                header, blocks = await skill.execute_all(user_id)
                await wait_msg.delete()
                await send_digest(
                    callback.message, header, blocks
                )
            except Exception as e:
                await wait_msg.delete()
                await callback.message.answer(
                    "😔 Something went wrong. "
                    "Please try again in a minute."
                )
                print(
                    f"[TopicNewsHandler] Error in execute_all: {e}"
                )
                import traceback
                traceback.print_exc()
            return

        wait_msg = await callback.message.answer(
            f"⏳ Gathering news about *{topic_value}*, "
            f"please wait...",
            parse_mode="Markdown",
        )
        try:
            header, blocks = await skill.execute_topic(
                user_id, topic_value
            )
            await wait_msg.delete()
            await send_digest(
                callback.message, header, blocks
            )
        except Exception as e:
            await wait_msg.delete()
            await callback.message.answer(
                "😔 Something went wrong. "
                "Please try again in a minute."
            )
            print(
                f"[TopicNewsHandler] Error in execute_topic: {e}"
            )
            import traceback
            traceback.print_exc()

    return router
