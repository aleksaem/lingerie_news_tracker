import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from datetime import date
from app.db.test_session import (
    init_test_db, TestSessionLocal, drop_test_db
)
from app.db.models import SourceCatalog
from app.repositories.article_repository import ArticleRepository
from app.repositories.digest_repository import DigestRepository
from app.repositories.user_source_repository import (
    UserSourceRepository,
)
from app.services.deduplication_service import DeduplicationService
from app.services.source_digest_builder_service import (
    SourceDigestBuilderService,
)
from app.skills.news_by_sources_skill import NewsBySourcesSkill

USER_ID = 12345
CACHE_USER_ID = 54321
TODAY = date.today().isoformat()


def check_not_touching_prod_db():
    from app.db.test_session import TEST_DATABASE_URL
    assert "test.db" in TEST_DATABASE_URL, \
        f"НЕБЕЗПЕКА: {TEST_DATABASE_URL}"
    print(f"✓ Тестова БД: {TEST_DATABASE_URL}")


check_not_touching_prod_db()


async def seed_catalog(session) -> dict[str, SourceCatalog]:
    from sqlalchemy import select

    existing = await session.execute(select(SourceCatalog))
    existing_sources = existing.scalars().all()
    if existing_sources:
        return {s.slug: s for s in existing_sources}

    sources = [
        SourceCatalog(
            display_name="Business of Fashion",
            slug="business_of_fashion",
            domain="businessoffashion.com",
            is_active=True,
        ),
        SourceCatalog(
            display_name="Vogue Business",
            slug="vogue_business",
            domain="voguebusiness.com",
            is_active=True,
        ),
    ]
    for s in sources:
        session.add(s)
    await session.commit()
    return {s.slug: s for s in sources}


MOCK_ARTICLES = {
    "business_of_fashion": [
        {
            "title": "BoF: lingerie market Q1 2026",
            "url": "https://businessoffashion.com/lingerie-q1",
            "source": "Business of Fashion",
            "published_at": TODAY,
            "content": "BoF lingerie market analysis Q1.",
            "matched_source": "Business of Fashion",
            "matched_source_slug": "business_of_fashion",
            "search_scope": "sources",
        },
        {
            "title": "BoF: Skims European expansion",
            "url": "https://businessoffashion.com/skims-europe",
            "source": "Business of Fashion",
            "published_at": TODAY,
            "content": "Skims opens EU stores.",
            "matched_source": "Business of Fashion",
            "matched_source_slug": "business_of_fashion",
            "search_scope": "sources",
        },
    ],
    "vogue_business": [
        {
            "title": "Vogue: underwear trends 2026",
            "url": "https://voguebusiness.com/underwear-trends",
            "source": "Vogue Business",
            "published_at": TODAY,
            "content": "Vogue underwear trend report.",
            "matched_source": "Vogue Business",
            "matched_source_slug": "vogue_business",
            "search_scope": "sources",
        },
    ],
}

AI_RESPONSES = {
    "https://businessoffashion.com/lingerie-q1": {
        "include": True, "relevance": "HIGH",
        "priority": "HIGH", "article_type": "data",
        "matched_source": "Business of Fashion",
        "summary": "BoF Q1 lingerie market data.",
        "why_it_matters": "Key market sizing data.",
        "tags": ["market", "Q1"],
    },
    "https://businessoffashion.com/skims-europe": {
        "include": True, "relevance": "HIGH",
        "priority": "HIGH", "article_type": "brand_move",
        "matched_source": "Business of Fashion",
        "summary": "Skims EU retail expansion.",
        "why_it_matters": "Competitor market entry.",
        "tags": ["Skims", "Europe"],
    },
    "https://voguebusiness.com/underwear-trends": {
        "include": True, "relevance": "HIGH",
        "priority": "HIGH", "article_type": "trend",
        "matched_source": "Vogue Business",
        "summary": "2026 underwear trend forecast.",
        "why_it_matters": "Product direction intelligence.",
        "tags": ["trends", "2026"],
    },
}


def make_mock_llm(responses: dict) -> MagicMock:
    client = MagicMock()

    async def mock_complete(prompt: str) -> str:
        for url, resp in responses.items():
            if url in prompt:
                return json.dumps(resp)
        if "BoF: lingerie market Q1 2026" in prompt:
            return json.dumps(
                responses["https://businessoffashion.com/lingerie-q1"]
            )
        if "BoF: Skims European expansion" in prompt:
            return json.dumps(
                responses["https://businessoffashion.com/skims-europe"]
            )
        if "Vogue: underwear trends 2026" in prompt:
            return json.dumps(
                responses["https://voguebusiness.com/underwear-trends"]
            )
        return json.dumps({
            "include": False, "relevance": "LOW",
            "priority": "LOW", "article_type": "other",
            "matched_source": "", "summary": "Not relevant.",
            "why_it_matters": None, "tags": [],
        })

    client.complete = mock_complete
    return client


def make_mock_search(articles_by_slug: dict) -> MagicMock:
    search = MagicMock()

    async def mock_fetch_single(source) -> list[dict]:
        return articles_by_slug.get(source.slug, [])

    search.fetch_for_single_source = mock_fetch_single
    return search


async def build_skill(session, slug_to_source):
    article_repo = ArticleRepository(session)

    catalog_repo = MagicMock()
    catalog_repo.find_by_slug = AsyncMock(
        side_effect=lambda slug: slug_to_source.get(slug)
    )

    return (
        NewsBySourcesSkill(
            user_source_repo=UserSourceRepository(session),
            source_catalog_repo=catalog_repo,
            article_repo=article_repo,
            digest_repo=DigestRepository(session),
            search_service=make_mock_search(MOCK_ARTICLES),
            deduplication_service=DeduplicationService(
                article_repo
            ),
            llm_client=make_mock_llm(AI_RESPONSES),
            builder_service=SourceDigestBuilderService(),
        ),
        UserSourceRepository(session),
        DigestRepository(session),
    )


async def test():
    await init_test_db()

    # === Сценарій A: немає sources ===
    print("\n=== A: немає sources ===")
    async with TestSessionLocal() as session:
        slug_to_source = await seed_catalog(session)
        skill, _, _ = await build_skill(
            session, slug_to_source
        )
        text, pairs = await skill.execute_menu(USER_ID)
        assert pairs is None
        assert "no sources" in text.lower()
        print(f"✓ execute_menu: підказка повернута")

    # === Сценарій B: execute_menu з sources ===
    print("\n=== B: execute_menu з sources ===")
    async with TestSessionLocal() as session:
        slug_to_source = await seed_catalog(session)
        skill, user_source_repo, _ = await build_skill(
            session, slug_to_source
        )
        bof = slug_to_source["business_of_fashion"]
        vogue = slug_to_source["vogue_business"]
        await user_source_repo.add_source(USER_ID, bof.id)
        await user_source_repo.add_source(USER_ID, vogue.id)

        text, pairs = await skill.execute_menu(USER_ID)
        assert pairs is not None
        assert len(pairs) == 2
        slugs = [p[1] for p in pairs]
        assert "business_of_fashion" in slugs
        assert "vogue_business" in slugs
        print(f"✓ execute_menu: {len(pairs)} source пари")

    # === Сценарій C: execute_source pipeline ===
    print("\n=== C: execute_source (pipeline) ===")
    async with TestSessionLocal() as session:
        slug_to_source = await seed_catalog(session)
        skill, user_source_repo, digest_repo = await build_skill(
            session, slug_to_source
        )
        bof = slug_to_source["business_of_fashion"]
        await user_source_repo.add_source(USER_ID, bof.id)

        header, blocks = await skill.execute_source(
            USER_ID, "business_of_fashion"
        )
        assert blocks is not None
        assert "Business of Fashion" in header
        assert len(blocks) <= 3
        print(
            f"✓ execute_source pipeline: "
            f"{len(blocks)} блоків"
        )

        # filter_value = slug в БД
        cached = await digest_repo.get_by_date_and_type(
            TODAY, "source_news", USER_ID,
            "business_of_fashion"
        )
        assert cached is not None
        assert cached.filter_value == "business_of_fashion"
        assert cached.digest_type == "source_news"
        print(
            f"✓ Digest збережено: "
            f"filter_value={cached.filter_value}"
        )

    # === Сценарій D: execute_source cache hit ===
    print("\n=== D: execute_source (cache hit) ===")
    async with TestSessionLocal() as session:
        slug_to_source = await seed_catalog(session)

        bad_search = MagicMock()
        bad_search.fetch_for_single_source = AsyncMock(
            side_effect=Exception(
                "Search не має викликатись при cache hit!"
            )
        )
        bad_llm = MagicMock()
        bad_llm.complete = AsyncMock(
            side_effect=Exception(
                "LLM не має викликатись при cache hit!"
            )
        )

        article_repo = ArticleRepository(session)
        catalog_repo = MagicMock()
        catalog_repo.find_by_slug = AsyncMock(
            side_effect=lambda slug: slug_to_source.get(slug)
        )

        skill = NewsBySourcesSkill(
            user_source_repo=UserSourceRepository(session),
            source_catalog_repo=catalog_repo,
            article_repo=article_repo,
            digest_repo=DigestRepository(session),
            search_service=bad_search,
            deduplication_service=DeduplicationService(
                article_repo
            ),
            llm_client=bad_llm,
            builder_service=SourceDigestBuilderService(),
        )

        user_source_repo = UserSourceRepository(session)
        bof = slug_to_source["business_of_fashion"]
        await user_source_repo.add_source(USER_ID, bof.id)

        result, blocks = await skill.execute_source(
            USER_ID, "business_of_fashion"
        )
        assert blocks is None
        assert "Business of Fashion" in result
        print("✓ Cache hit: Search і LLM не викликались")

    # === Сценарій E: execute_all ===
    print("\n=== E: execute_all ===")
    async with TestSessionLocal() as session:
        slug_to_source = await seed_catalog(session)
        skill, user_source_repo, digest_repo = await build_skill(
            session, slug_to_source
        )
        for slug, source in slug_to_source.items():
            await user_source_repo.add_source(
                USER_ID, source.id
            )

        header, blocks = await skill.execute_all(USER_ID)
        assert blocks is not None
        assert "News by Sources" in header
        assert len(blocks) == 2
        print(
            f"✓ execute_all: {len(blocks)} блоків "
            f"для 2 sources"
        )

        # Обидва sources в кеші після execute_all
        for slug in ["business_of_fashion", "vogue_business"]:
            cached = await digest_repo.get_by_date_and_type(
                TODAY, "source_news", USER_ID, slug
            )
            assert cached is not None, \
                f"Digest для '{slug}' не збережено"
            assert cached.filter_value == slug
        print("✓ Обидва sources збережено в кеш")

    # === Сценарій F: execute_all — кеш економія ===
    print("\n=== F: execute_all (кеш для одного source) ===")
    async with TestSessionLocal() as session:
        slug_to_source = await seed_catalog(session)

        call_count = {"count": 0}
        original_mock = make_mock_search(MOCK_ARTICLES)

        async def counting_fetch(source):
            call_count["count"] += 1
            return MOCK_ARTICLES.get(source.slug, [])

        original_mock.fetch_for_single_source = counting_fetch

        article_repo = ArticleRepository(session)
        catalog_repo = MagicMock()
        catalog_repo.find_by_slug = AsyncMock(
            side_effect=lambda slug: slug_to_source.get(slug)
        )

        skill = NewsBySourcesSkill(
            user_source_repo=UserSourceRepository(session),
            source_catalog_repo=catalog_repo,
            article_repo=article_repo,
            digest_repo=DigestRepository(session),
            search_service=original_mock,
            deduplication_service=DeduplicationService(
                article_repo
            ),
            llm_client=make_mock_llm(AI_RESPONSES),
            builder_service=SourceDigestBuilderService(),
        )

        user_source_repo = UserSourceRepository(session)
        bof = slug_to_source["business_of_fashion"]
        vogue = slug_to_source["vogue_business"]
        await user_source_repo.add_source(CACHE_USER_ID, bof.id)
        await user_source_repo.add_source(CACHE_USER_ID, vogue.id)

        # Перший execute_source для BoF — кешується
        await skill.execute_source(
            CACHE_USER_ID, "business_of_fashion"
        )
        calls_after_first = call_count["count"]
        print(
            f"  Після execute_source BoF: "
            f"{calls_after_first} search calls"
        )

        # execute_all — BoF з кешу, тільки Vogue через pipeline
        call_count["count"] = 0
        await skill.execute_all(CACHE_USER_ID)
        calls_in_all = call_count["count"]
        print(
            f"  execute_all: {calls_in_all} search calls "
            f"(BoF з кешу, тільки Vogue через pipeline)"
        )
        assert calls_in_all == 1, \
            f"Очікували 1 search call (тільки Vogue), " \
            f"отримали {calls_in_all}"
        print("✓ execute_all використовує кеш — економія!")

    await drop_test_db()
    print("\n" + "="*50)
    print("✅ ВСІ ТЕСТИ ПРОЙДЕНІ")
    print("="*50)


asyncio.run(test())
