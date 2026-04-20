import re
from typing import List, Optional
from aiogram.types import Message

TELEGRAM_LIMIT = 4096


def sanitize_text(text: str) -> str:
    """Прибирає все що може зламати Telegram."""
    if not text:
        return ""

    # Control characters
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    return text


def strip_markdown(text: str) -> str:
    """
    Повністю прибирає Markdown і проблемні символи.
    Результат — чистий plain text.
    """
    # Посилання [text](url) → просто text (url на новому рядку)
    text = re.sub(
        r'\[(.+?)\]\((.+?)\)',
        lambda m: f"{m.group(1)}\n{m.group(2)}",
        text
    )

    # Bold і italic
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\*(.+?)\*', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'_(.+?)_', r'\1', text, flags=re.DOTALL)

    # Залишкові * і _
    text = text.replace('*', '').replace('_', '')

    return text


async def safe_send(
    message: Message,
    text: str,
) -> None:
    if not text or not text.strip():
        return

    # Спроба 1 — Markdown
    try:
        await message.answer(
            text,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
        return
    except Exception as e:
        print(f"[Utils] Markdown failed: {e}")
        encoded = text.encode('utf-8', errors='replace')
        offset = 4109
        print(f"[Utils] Байти навколо offset {offset}:")
        print(repr(encoded[max(0, offset-20):offset+20]))

    # Спроба 2 — strip markdown, plain text
    try:
        plain = strip_markdown(sanitize_text(text))
        plain = plain[:TELEGRAM_LIMIT]
        await message.answer(
            plain,
            disable_web_page_preview=True,
        )
        return
    except Exception as e:
        print(f"[Utils] Plain text failed: {e}")

    # Спроба 3 — мінімальний текст, тільки перші 500 символів
    try:
        minimal = sanitize_text(text)
        minimal = re.sub(r'[^\w\s\.,!?:;()\-\n]', ' ', minimal)
        minimal = minimal[:500]
        await message.answer(minimal)
    except Exception as e:
        print(f"[Utils] Всі спроби провалились: {e}")


def split_digest_to_blocks(text: str) -> tuple[str, list[str]]:
    """
    Розбиває збережений digest текст назад на header і блоки.
    Блоки розділені подвійним переносом рядка \n\n
    і починаються з *1. або *Назва* (для All режимів).

    Використовується при cache hit щоб правильно
    розбити повідомлення між новинами а не посередині.
    """
    if not text:
        return text, []

    # Розбиваємо по подвійному переносу
    parts = text.split("\n\n")

    if len(parts) <= 1:
        return text, []

    # Перша частина завжди header
    header = parts[0]
    blocks = []
    current_block = ""
    found_block = False

    for part in parts[1:]:
        if not part.strip():
            continue

        # Нова новина починається з *1. або *2. і т.д.
        # або з назви бренду/топіка/сорса (*Назва*)
        is_new_block = bool(
            re.match(r'^\*\d+\.', part.strip()) or
            re.match(r'^\*[^*\n]+\*', part.strip()) or
            re.match(r'^📰|^🏷|^📋|^📡', part.strip())
        )

        if is_new_block and current_block:
            blocks.append(current_block.strip())
            current_block = part
            found_block = True
        elif is_new_block:
            current_block = part
            found_block = True
        elif not found_block:
            header = header + "\n\n" + part
        else:
            # Продовження поточного блоку
            current_block = current_block + "\n\n" + part \
                if current_block else part

    if current_block.strip():
        blocks.append(current_block.strip())

    # Якщо не вдалось розбити — повертаємо як один блок
    if not blocks:
        return text, []

    return header, blocks


async def send_digest(
    message: Message,
    header: str,
    blocks: Optional[List[str]],
) -> None:
    """
    Відправляє digest в Telegram.
    Розбиває на повідомлення між блоками.
    """
    if blocks is None:
        header, blocks = split_digest_to_blocks(header)

        # Якщо не вдалось розбити — відправляємо як є по лімітам
        if not blocks:
            text = header or ""
            chunks = [
                text[i:i+TELEGRAM_LIMIT]
                for i in range(0, max(len(text), 1), TELEGRAM_LIMIT)
            ]
            for chunk in chunks:
                if chunk.strip():
                    await safe_send(message, chunk)
            return

    # Блоки — розбиваємо між новинами
    current = header or ""
    for block in blocks:
        if not block:
            continue
        candidate = current + "\n\n" + block
        if len(candidate) <= TELEGRAM_LIMIT:
            current = candidate
        else:
            if current.strip():
                await safe_send(message, current.strip())
            current = block

    if current.strip():
        await safe_send(message, current.strip())
