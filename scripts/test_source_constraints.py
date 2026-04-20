import asyncio
from datetime import date
from sqlalchemy import select, func
from app.db.test_session import (
    init_test_db, TestSessionLocal, drop_test_db
)
from app.db.models import Digest
from app.repositories.digest_repository import DigestRepository

TODAY = date.today().isoformat()
USER_1 = 111111
USER_2 = 222222


def check_not_touching_prod_db():
    from app.db.test_session import TEST_DATABASE_URL
    assert "test.db" in TEST_DATABASE_URL, \
        f"НЕБЕЗПЕКА: тест використовує не тестову БД! {TEST_DATABASE_URL}"
    print(f"✓ Використовується тестова БД: {TEST_DATABASE_URL}")


check_not_touching_prod_db()


async def test():
    await init_test_db()

    async with TestSessionLocal() as session:
        repo = DigestRepository(session)

        # ============================================================
        # Блок 1 — всі дозволені комбінації за один день
        # ============================================================
        print("\n=== Блок 1: дозволені комбінації ===")

        combos = [
            # (digest_type, user_id, filter_value, опис)
            ("top_news",    None,   None,
             "глобальний top_news"),
            ("competitors", USER_1, None,
             "competitors user_1"),
            ("competitors", USER_2, None,
             "competitors user_2"),
            ("topic_news",  USER_1, "Pricing",
             "topic Pricing user_1"),
            ("topic_news",  USER_1, "Sustainability",
             "topic Sustainability user_1"),
            ("topic_news",  USER_2, "Pricing",
             "topic Pricing user_2"),
            ("source_news", USER_1, "business_of_fashion",
             "source BoF user_1"),
            ("source_news", USER_1, "vogue_business",
             "source Vogue user_1"),
            ("source_news", USER_2, "business_of_fashion",
             "source BoF user_2"),
            ("source_news", USER_2, "wwd",
             "source WWD user_2"),
        ]

        for digest_type, user_id, filter_value, desc in combos:
            try:
                saved = await repo.save(
                    TODAY,
                    f"Content: {desc}",
                    digest_type=digest_type,
                    user_id=user_id,
                    filter_value=filter_value,
                )
                assert saved.id is not None
                print(f"  ✓ {desc}")
            except Exception as e:
                print(f"  ✗ ПОМИЛКА для '{desc}': {e}")
                raise

        result = await session.execute(
            select(func.count()).select_from(Digest)
            .where(Digest.digest_date == TODAY)
        )
        total = result.scalar()
        assert total == len(combos), \
            f"Очікували {len(combos)}, отримали {total}"
        print(f"\n✓ В БД рівно {total} записів за {TODAY}")

        # ============================================================
        # Блок 2 — дублікати оновлюються, не падають
        # ============================================================
        print("\n=== Блок 2: повторний save оновлює запис ===")

        duplicates = [
            ("top_news",    None,   None,
             "дублікат top_news"),
            ("source_news", USER_1, "business_of_fashion",
             "дублікат BoF user_1"),
            ("source_news", USER_2, "business_of_fashion",
             "дублікат BoF user_2"),
            ("topic_news",  USER_1, "Pricing",
             "дублікат Pricing user_1"),
        ]

        for digest_type, user_id, filter_value, desc in duplicates:
            try:
                updated = await repo.save(
                    TODAY,
                    f"UPDATED: {desc}",
                    digest_type=digest_type,
                    user_id=user_id,
                    filter_value=filter_value,
                )
                assert "UPDATED" in updated.content
                print(f"  ✓ {desc}")
            except Exception as e:
                print(f"  ✗ ПОМИЛКА при оновленні '{desc}': {e}")
                raise

        result = await session.execute(
            select(func.count()).select_from(Digest)
            .where(Digest.digest_date == TODAY)
        )
        still_same = result.scalar()
        assert still_same == len(combos), \
            f"Після оновлень має бути {len(combos)}, " \
            f"отримали {still_same}"
        print(f"\n✓ Кількість записів не змінилась: {still_same}")

        # ============================================================
        # Блок 3 — get_by_date_and_type повертає правильний запис
        # ============================================================
        print("\n=== Блок 3: читання по всіх параметрах ===")

        reads = [
            ("top_news",    None,   None,
             "top_news"),
            ("competitors", USER_1, None,
             "competitors user_1"),
            ("topic_news",  USER_1, "Pricing",
             "Pricing user_1"),
            ("source_news", USER_1, "business_of_fashion",
             "BoF user_1"),
            ("source_news", USER_1, "vogue_business",
             "Vogue user_1"),
            ("source_news", USER_2, "business_of_fashion",
             "BoF user_2"),
        ]

        for digest_type, user_id, filter_value, desc in reads:
            found = await repo.get_by_date_and_type(
                TODAY, digest_type, user_id, filter_value
            )
            assert found is not None, \
                f"Не знайдено для: {desc}"
            assert found.digest_type == digest_type
            assert found.user_id == user_id
            assert found.filter_value == filter_value
            print(f"  ✓ {desc}")

        # Чужий user не бачить чужий source digest
        wrong = await repo.get_by_date_and_type(
            TODAY, "source_news", 999999, "business_of_fashion"
        )
        assert wrong is None
        print("  ✓ Чужий user отримує None для source digest")

        # Неіснуючий source slug — None
        bad_slug = await repo.get_by_date_and_type(
            TODAY, "source_news", USER_1, "nonexistent_source"
        )
        assert bad_slug is None
        print("  ✓ Неіснуючий slug повертає None")

        # get_by_date (legacy) повертає top_news
        legacy = await repo.get_by_date(TODAY)
        assert legacy is not None
        assert legacy.digest_type == "top_news"
        assert legacy.filter_value is None
        print("  ✓ get_by_date (legacy) повертає top_news")

        # ============================================================
        # Блок 4 — invalidate видаляє тільки потрібний запис
        # ============================================================
        print("\n=== Блок 4: invalidate ===")

        # Видаляємо конкретний source digest
        deleted = await repo.invalidate(
            TODAY, "source_news", USER_1, "business_of_fashion"
        )
        assert deleted == True
        gone = await repo.get_by_date_and_type(
            TODAY, "source_news", USER_1, "business_of_fashion"
        )
        assert gone is None
        print("  ✓ invalidate BoF user_1: видалено")

        # Vogue user_1 не постраждав
        vogue_still = await repo.get_by_date_and_type(
            TODAY, "source_news", USER_1, "vogue_business"
        )
        assert vogue_still is not None
        print("  ✓ Vogue user_1 не постраждав")

        # BoF user_2 не постраждав
        bof_user2 = await repo.get_by_date_and_type(
            TODAY, "source_news", USER_2, "business_of_fashion"
        )
        assert bof_user2 is not None
        print("  ✓ BoF user_2 не постраждав")

        # top_news і competitors не постраждали
        top = await repo.get_by_date(TODAY)
        assert top is not None
        comp = await repo.get_by_date_and_type(
            TODAY, "competitors", USER_1, None
        )
        assert comp is not None
        print("  ✓ top_news і competitors не постраждали")

        # ============================================================
        # Блок 5 — invalidate_by_type видаляє всі source_news
        # ============================================================
        print("\n=== Блок 5: invalidate_by_type ===")

        count_before = await session.execute(
            select(func.count()).select_from(Digest).where(
                Digest.digest_type == "source_news",
                Digest.user_id == USER_1,
            )
        )
        source_count = count_before.scalar()
        print(
            f"  source_news digest-ів user_1: {source_count}"
        )

        deleted_count = await repo.invalidate_by_type(
            TODAY, "source_news", USER_1
        )
        assert deleted_count == source_count, \
            f"Очікували {source_count}, видалено {deleted_count}"
        print(
            f"  ✓ invalidate_by_type: видалено {deleted_count}"
        )

        # USER_2 source_news не постраждали
        user2_sources = await session.execute(
            select(func.count()).select_from(Digest).where(
                Digest.digest_type == "source_news",
                Digest.user_id == USER_2,
            )
        )
        assert user2_sources.scalar() > 0
        print("  ✓ source_news user_2 не постраждав")

        # topic_news не постраждав
        topic_count = await session.execute(
            select(func.count()).select_from(Digest).where(
                Digest.digest_type == "topic_news",
            )
        )
        assert topic_count.scalar() > 0
        print("  ✓ topic_news не постраждав")

        # ============================================================
        # Блок 6 — source і topic не конфліктують з однаковим
        #           filter_value
        # ============================================================
        print("\n=== Блок 6: topic і source з однаковим filter ===")

        # Можна мати topic_news і source_news з однаковим
        # filter_value — це різні типи
        await repo.save(
            TODAY, "topic content",
            digest_type="topic_news",
            user_id=USER_1,
            filter_value="retail",
        )
        await repo.save(
            TODAY, "source content",
            digest_type="source_news",
            user_id=USER_1,
            filter_value="retail",
        )

        topic_retail = await repo.get_by_date_and_type(
            TODAY, "topic_news", USER_1, "retail"
        )
        source_retail = await repo.get_by_date_and_type(
            TODAY, "source_news", USER_1, "retail"
        )
        assert topic_retail is not None
        assert source_retail is not None
        assert topic_retail.id != source_retail.id
        print(
            "  ✓ topic_news і source_news з filter='retail' "
            "незалежні"
        )

        # ============================================================
        # Блок 7 — різні дати не конфліктують
        # ============================================================
        print("\n=== Блок 7: різні дати ===")

        other_dates = ["2026-01-01", "2026-06-15", "2026-12-31"]
        for d in other_dates:
            await repo.save(
                d, f"Source content {d}",
                digest_type="source_news",
                user_id=USER_1,
                filter_value="business_of_fashion",
            )
            print(f"  ✓ source BoF user_1 за {d}")

        for d in other_dates:
            found = await repo.get_by_date_and_type(
                d, "source_news", USER_1,
                "business_of_fashion"
            )
            assert found is not None
            assert found.digest_date == d
        print("  ✓ Всі дати читаються незалежно")

    await drop_test_db()
    print("\n" + "="*50)
    print("✅ ВСІ ПЕРЕВІРКИ ПРОЙДЕНІ")
    print("БД підтримує всі комбінації:")
    print("  top_news / competitors / topic_news / source_news")
    print("  з різними user_id і filter_value")
    print("="*50)


asyncio.run(test())
