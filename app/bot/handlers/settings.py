from aiogram import Router
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from app.bot.keyboards.main_menu import get_main_keyboard
from app.bot.keyboards.settings_menu import (
    get_settings_keyboard,
    get_remove_brand_keyboard,
    get_remove_topic_keyboard,
)
from app.bot.states import SettingsStates
from app.skills.brand_settings_skill import BrandSettingsSkill
from app.skills.topic_settings_skill import TopicSettingsSkill

router = Router()

# Всі кнопки меню - для захисту FSM стану
MENU_BUTTONS = {
    "📰 Top News", "🏷 Competitors",
    "📋 News by Topics", "⚙️ Settings",
    "➕ Add Brand", "🗑 Remove Brand",
    "➕ Add Topic", "🗑 Remove Topic",
    "👁 View Settings", "⬅️ Back",
}


def setup_settings_handler(
    brand_skill: BrandSettingsSkill,
    topic_skill: TopicSettingsSkill,
) -> Router:

    # --- Вхід в Settings ---
    @router.message(lambda m: m.text == "⚙️ Settings")
    async def settings_handler(
        message: Message, state: FSMContext
    ):
        await state.clear()
        text = await brand_skill.get_settings_text(
            message.from_user.id
        )
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=get_settings_keyboard(),
        )

    # --- View Settings ---
    @router.message(lambda m: m.text == "👁 View Settings")
    async def view_settings_handler(message: Message):
        text = await brand_skill.get_settings_text(
            message.from_user.id
        )
        await message.answer(
            text,
            parse_mode="Markdown",
            reply_markup=get_settings_keyboard(),
        )

    # ==========================================
    # BRAND FLOW
    # ==========================================

    @router.message(lambda m: m.text == "➕ Add Brand")
    async def add_brand_start(
        message: Message, state: FSMContext
    ):
        await state.set_state(
            SettingsStates.waiting_for_brand_name
        )
        await message.answer(
            "✏️ Enter the brand name you want to track:\n\n"
            "For example: _Skims_, _Intimissimi_, "
            "_Victoria's Secret_",
            parse_mode="Markdown",
        )

    @router.message(SettingsStates.waiting_for_brand_name)
    async def add_brand_receive(
        message: Message, state: FSMContext
    ):
        await state.clear()
        brand_name = message.text.strip() if message.text else ""

        if brand_name in MENU_BUTTONS:
            await message.answer(
                "❌ That looks like a menu button. "
                "Please enter an actual brand name.",
                reply_markup=get_settings_keyboard(),
            )
            return

        result = await brand_skill.add_brand(
            message.from_user.id, brand_name
        )
        await message.answer(
            result,
            parse_mode="Markdown",
            reply_markup=get_settings_keyboard(),
        )

    @router.message(lambda m: m.text == "🗑 Remove Brand")
    async def remove_brand_start(message: Message):
        brands = await brand_skill.list_brands(
            message.from_user.id
        )
        if not brands:
            await message.answer(
                "ℹ️ You have no brands to remove.",
                reply_markup=get_settings_keyboard(),
            )
            return

        await message.answer(
            "Select a brand to remove:",
            reply_markup=get_remove_brand_keyboard(brands),
        )

    @router.callback_query(
        lambda c: c.data
        and c.data.startswith("remove_brand:")
    )
    async def remove_brand_callback(callback: CallbackQuery):
        brand_name = callback.data.split(":", 1)[1]

        if brand_name == "cancel":
            await callback.message.edit_text("Cancelled.")
            await callback.answer()
            return

        result = await brand_skill.remove_brand(
            callback.from_user.id, brand_name
        )

        remaining = await brand_skill.list_brands(
            callback.from_user.id
        )
        if remaining:
            await callback.message.edit_reply_markup(
                reply_markup=get_remove_brand_keyboard(remaining)
            )
        else:
            await callback.message.edit_text(
                "All brands removed."
            )

        await callback.answer(result, show_alert=False)

    # ==========================================
    # TOPIC FLOW
    # ==========================================

    @router.message(lambda m: m.text == "➕ Add Topic")
    async def add_topic_start(
        message: Message, state: FSMContext
    ):
        await state.set_state(
            SettingsStates.waiting_for_topic_name
        )
        await message.answer(
            "✏️ Enter the topic you want to track:\n\n"
            "For example: _Pricing_, _Sustainability_, "
            "_Retail_, _Campaigns_, _Partnerships_",
            parse_mode="Markdown",
        )

    @router.message(SettingsStates.waiting_for_topic_name)
    async def add_topic_receive(
        message: Message, state: FSMContext
    ):
        await state.clear()
        topic_name = message.text.strip() if message.text else ""

        if topic_name in MENU_BUTTONS:
            await message.answer(
                "❌ That looks like a menu button. "
                "Please enter an actual topic name.",
                reply_markup=get_settings_keyboard(),
            )
            return

        result = await topic_skill.add_topic(
            message.from_user.id, topic_name
        )
        await message.answer(
            result,
            parse_mode="Markdown",
            reply_markup=get_settings_keyboard(),
        )

    @router.message(lambda m: m.text == "🗑 Remove Topic")
    async def remove_topic_start(message: Message):
        topics = await topic_skill.list_topics(
            message.from_user.id
        )
        if not topics:
            await message.answer(
                "ℹ️ You have no topics to remove.",
                reply_markup=get_settings_keyboard(),
            )
            return

        await message.answer(
            "Select a topic to remove:",
            reply_markup=get_remove_topic_keyboard(topics),
        )

    @router.callback_query(
        lambda c: c.data
        and c.data.startswith("remove_topic:")
    )
    async def remove_topic_callback(callback: CallbackQuery):
        topic_name = callback.data.split(":", 1)[1]

        if topic_name == "cancel":
            await callback.message.edit_text("Cancelled.")
            await callback.answer()
            return

        result = await topic_skill.remove_topic(
            callback.from_user.id, topic_name
        )

        remaining = await topic_skill.list_topics(
            callback.from_user.id
        )
        if remaining:
            await callback.message.edit_reply_markup(
                reply_markup=get_remove_topic_keyboard(remaining)
            )
        else:
            await callback.message.edit_text(
                "All topics removed."
            )

        await callback.answer(result, show_alert=False)

    # --- Back ---
    @router.message(lambda m: m.text == "⬅️ Back")
    async def back_handler(
        message: Message, state: FSMContext
    ):
        await state.clear()
        await message.answer(
            "Main menu",
            reply_markup=get_main_keyboard(),
        )

    return router
