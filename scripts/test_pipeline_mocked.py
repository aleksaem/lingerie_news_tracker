import asyncio
import json
from unittest.mock import AsyncMock, MagicMock
from app.db.test_session import init_test_db, TestSessionLocal, drop_test_db
from app.repositories.article_repository import ArticleRepository
from app.repositories.digest_repository import DigestRepository
from app.services.search_service import SearchService
from app.services.deduplication_service import DeduplicationService
from app.services.article_filter_service import ArticleFilterService
from app.services.digest_builder_service import DigestBuilderService
from app.skills.top_news_skill import TopNewsSkill

MOCK_RAW_ARTICLES = [
    {
        "title": "Skims valued at $4 billion after new funding round",
        "url": "https://example.com/skims-funding",
        "source": "Business of Fashion",
        "published_at": "2026-04-16",
        "content": "Kim Kardashian shapewear brand raises funding at $4B valuation.",
    },
    {
        "title": "EU textile sustainability labeling requirements 2026",
        "url": "https://example.com/eu-regulation",
        "source": "Reuters",
        "published_at": "2026-04-16",
        "content": "EU requires digital product passports for textile brands by 2026.",
    },
    {
        "title": "Victoria Secret launches spring collection",
        "url": "https://example.com/vs-spring",
        "source": "Vogue",
        "published_at": "2026-04-16",
        "content": "Victoria Secret announces new spring intimate apparel line.",
    },
    {
        "title": "Local weather forecast New York this weekend",
        "url": "https://example.com/weather",
        "source": "NY Times",
        "published_at": "2026-04-16",
        "content": "Temperatures expected to reach 72 degrees in Manhattan.",
    },
    {
        "title": "Skims valued at $4 billion after new funding round",
        "url": "https://example.com/skims-funding",
        "source": "WWD",
        "published_at": "2026-04-16",
        "content": "Duplicate article about Skims funding.",
    },
    {
        "title": "Skims valued at $4 billion in new funding round",
        "url": "https://example.com/skims-funding-2",
        "source": "Forbes",
        "published_at": "2026-04-16",
        "content": "Skims funding round details from Forbes perspective.",
    },
]

# keyed by title substring present in the rendered prompt
MOCK_AI_RESPONSES = {
    "Skims valued at $4 billion": {
        "include": True,
        "relevance": "HIGH",
        "priority": "HIGH",
        "article_type": "funding",
        "competitor": "Skims",
        "summary": "Skims raised funding at $4B valuation.",
        "why_it_matters": "Direct competitor milestone worth tracking.",
        "tags": ["Skims", "funding", "valuation"],
    },
    "EU textile sustainability": {
        "include": True,
        "relevance": "HIGH",
        "priority": "HIGH",
        "article_type": "regulation",
        "competitor": None,
        "summary": "EU requires digital product passports by 2026.",
        "why_it_matters": "Affects all brands selling in EU markets.",
        "tags": ["EU", "regulation", "sustainability"],
    },
    "Victoria Secret launches spring": {
        "include": True,
        "relevance": "MEDIUM",
        "priority": "MEDIUM",
        "article_type": "competitor_news",
        "competitor": "Victoria's Secret",
        "summary": "VS launches spring intimate apparel collection.",
        "why_it_matters": "Competitor product launch signals market direction.",
        "tags": ["Victoria's Secret", "collection", "spring"],
    },
    "Local weather forecast": {
        "include": False,
        "relevance": "LOW",
        "priority": "LOW",
        "article_type": "other",
        "competitor": None,
        "summary": "Weather forecast unrelated to fashion.",
        "why_it_matters": None,
        "tags": [],
    },
}


def make_mock_news_client(articles: list) -> MagicMock:
    client = MagicMock()
    client.search = AsyncMock(return_value=articles)
    return client


def make_mock_llm_client(ai_responses: dict) -> MagicMock:
    client = MagicMock()

    async def mock_complete(prompt: str) -> str:
        for url, response in ai_responses.items():
            if url in prompt:
                return json.dumps(response)
        return json.dumps({
            "include": False,
            "relevance": "LOW",
            "priority": "LOW",
            "article_type": "other",
            "competitor": None,
            "summary": "Not relevant.",
            "why_it_matters": None,
            "tags": [],
        })

    client.complete = mock_complete
    return client


async def test_deduplication():
    print("\n=== TEST: DeduplicationService ===")

    mock_repo = AsyncMock()
    mock_repo.filter_new_urls = AsyncMock(side_effect=lambda urls: urls)

    service = DeduplicationService(mock_repo)
    result = await service.remove_duplicates(MOCK_RAW_ARTICLES)

    print(f"✓ Початково: {len(MOCK_RAW_ARTICLES)}, після дедупу: {len(result)}")

    urls = [a["url"] for a in result]
    assert urls.count("https://example.com/skims-funding") == 1, \
        "Дублікат по URL не прибраний"
    print("✓ Дублікат по URL прибраний")

    skims_articles = [a for a in result if "Skims" in a["title"]]
    assert len(skims_articles) == 1, \
        f"Семантичний дублікат не прибраний, знайдено: {len(skims_articles)}"
    print("✓ Семантичний дублікат по title прибраний")

    print("✅ DeduplicationService OK")
    return result


async def test_filter_service(unique_articles: list):
    print("\n=== TEST: ArticleFilterService ===")

    mock_llm = make_mock_llm_client(MOCK_AI_RESPONSES)
    service = ArticleFilterService(mock_llm)

    result = await service.process_articles(unique_articles)

    print(f"✓ Подано: {len(unique_articles)}, пройшло фільтр: {len(result)}")

    urls = [a["url"] for a in result]
    assert "https://example.com/weather" not in urls, \
        "Нерелевантна стаття не виключена"
    print("✓ Нерелевантна стаття виключена")

    assert "https://example.com/skims-funding" in urls, "Skims стаття не включена"
    assert "https://example.com/eu-regulation" in urls, "EU regulation не включена"
    print("✓ Релевантні статті включені")

    skims = next(a for a in result if "skims-funding" in a["url"])
    assert skims["priority"] == "HIGH"
    assert skims["competitor"] == "Skims"
    assert isinstance(skims["tags"], list)
    print("✓ AI поля збережені коректно")

    print("✅ ArticleFilterService OK")
    return result


async def test_digest_builder(filtered_articles: list):
    print("\n=== TEST: DigestBuilderService ===")

    builder = DigestBuilderService()
    header, blocks = builder.build(filtered_articles)
    full_text = header + "\n\n".join(blocks)

    print(f"✓ Digest сформовано, довжина: {len(full_text)} символів")
    print(f"✓ Превью:\n{full_text[:200]}...")

    assert "Top News" in header
    assert "Skims" in full_text
    assert "💡" in full_text
    assert len(full_text) > 100
    assert len(blocks) == len(filtered_articles)

    empty_header, empty_blocks = builder.build([])
    assert empty_header == "" and empty_blocks == []
    print("✓ Порожній список handled")

    print("✅ DigestBuilderService OK")
    return header, blocks


async def test_full_pipeline_no_cache():
    print("\n=== TEST: Full pipeline (no cache) ===")

    await init_test_db()

    async with TestSessionLocal() as session:
        article_repo = ArticleRepository(session)
        digest_repo = DigestRepository(session)

        mock_news = make_mock_news_client(MOCK_RAW_ARTICLES)
        mock_llm = make_mock_llm_client(MOCK_AI_RESPONSES)

        skill = TopNewsSkill(
            article_repo=article_repo,
            digest_repo=digest_repo,
            search_service=SearchService(mock_news),
            deduplication_service=DeduplicationService(article_repo),
            filter_service=ArticleFilterService(mock_llm),
            builder_service=DigestBuilderService(),
        )

        header, blocks = await skill.execute()
        full_text = header + "\n\n".join(blocks)

        print(f"✓ Digest отримано, довжина: {len(full_text)}")
        assert len(full_text) > 50
        assert "Top News" in header
        print("✓ Pipeline відпрацював повністю")

        from datetime import date
        today = date.today().isoformat()
        saved_digest = await digest_repo.get_by_date(today)
        assert saved_digest is not None, "Digest не збережено в БД"
        assert saved_digest.content == full_text
        print("✓ Digest збережено в БД")

    return full_text


async def test_full_pipeline_with_cache(expected_digest: str):
    print("\n=== TEST: Full pipeline (cache hit) ===")

    async with TestSessionLocal() as session:
        article_repo = ArticleRepository(session)
        digest_repo = DigestRepository(session)

        mock_news = MagicMock()
        mock_news.search = AsyncMock(side_effect=Exception(
            "NewsClient не має викликатись при cache hit!"
        ))
        mock_llm = MagicMock()
        mock_llm.complete = AsyncMock(side_effect=Exception(
            "LLMClient не має викликатись при cache hit!"
        ))

        skill = TopNewsSkill(
            article_repo=article_repo,
            digest_repo=digest_repo,
            search_service=SearchService(mock_news),
            deduplication_service=DeduplicationService(article_repo),
            filter_service=ArticleFilterService(mock_llm),
            builder_service=DigestBuilderService(),
        )

        cached_text, cached_blocks = await skill.execute()

        assert cached_blocks is None, "Cache hit має повертати blocks=None"
        assert cached_text == expected_digest, "Кеш повернув інший digest"
        print("✓ Digest повернуто з кешу")
        print("✓ NewsClient не викликався")
        print("✓ LLMClient не викликався")

    print("✅ Cache hit OK")


async def run_all():
    unique_articles = await test_deduplication()
    filtered_articles = await test_filter_service(unique_articles)
    await test_digest_builder(filtered_articles)

    digest = await test_full_pipeline_no_cache()
    await test_full_pipeline_with_cache(digest)

    await drop_test_db()
    print("✓ Тестова БД очищена")
    print("\n" + "=" * 50)
    print("✅ ВСІ ТЕСТИ ПРОЙДЕНІ")
    print("=" * 50)


asyncio.run(run_all())
