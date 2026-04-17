import asyncio
from app.db.test_session import init_test_db, TestSessionLocal, drop_test_db
from app.repositories.article_repository import ArticleRepository


async def test():
    await init_test_db()

    async with TestSessionLocal() as session:
        repo = ArticleRepository(session)

        articles = [
            {
                "title": "Skims opens store in London",
                "url": "https://example.com/skims-london",
                "source": "WWD",
                "published_at": "2026-04-16",
                "content": "Some content here",
                "include": True,
                "include_in_digest": None,
                "relevance": "HIGH",
                "priority": "HIGH",
                "article_type": "retail",
                "competitor": "Skims",
                "summary": "Skims expands retail footprint.",
                "why_it_matters": "Direct competitor expansion.",
                "tags": ["Skims", "retail", "expansion"],
            },
            {
                "title": "EU textile regulation update",
                "url": "https://example.com/eu-regulation",
                "source": "Reuters",
                "published_at": "2026-04-16",
                "content": "EU regulation content",
                "include": True,
                "relevance": "HIGH",
                "priority": "MEDIUM",
                "article_type": "regulation",
                "competitor": None,
                "summary": "EU requires digital passports.",
                "why_it_matters": "Affects EU market brands.",
                "tags": '["EU", "regulation", "sustainability"]',
            },
            {
                "title": "Victoria Secret launches spring collection",
                "url": "https://example.com/vs-spring",
                "source": "Vogue",
                "published_at": "2026-04-16",
                "content": "VS content",
                "include": True,
                "relevance": "MEDIUM",
                "priority": "MEDIUM",
                "article_type": "competitor_news",
                "competitor": "Victoria's Secret",
                "summary": "VS launches spring collection.",
                "why_it_matters": "Competitor product launch.",
                "tags": None,
            },
            {
                "title": "Lingerie market analysis 2025",
                "url": "https://example.com/market-analysis",
                "source": "Business of Fashion",
                "published_at": "2026-04-16",
                "content": "Market content",
                "include": True,
                "relevance": "HIGH",
                "priority": "HIGH",
                "article_type": "trend",
                "competitor": None,
                "summary": "Market growing 8% YoY.",
                "why_it_matters": "Strategic planning data.",
                "tags": ["market", "analysis"],
                "unknown_field_from_ai": "should be ignored",
                "another_unknown": 12345,
            },
        ]

        saved = await repo.save_many(articles)
        print(f"✓ Збережено статей: {saved}")
        assert saved == 4, f"Очікували 4, отримали {saved}"

        saved_again = await repo.save_many(articles)
        print(f"✓ Повторне збереження (має бути 0): {saved_again}")
        assert saved_again == 0, f"Очікували 0, отримали {saved_again}"

        from sqlalchemy import select
        from app.db.models import Article

        result = await session.execute(
            select(Article).where(Article.url == "https://example.com/eu-regulation")
        )
        eu_article = result.scalar_one()
        print(f"✓ tags для EU article: {eu_article.tags}")
        assert isinstance(eu_article.tags, list), "tags має бути list"
        assert "EU" in eu_article.tags, "EU має бути в tags"

        result = await session.execute(
            select(Article).where(Article.url == "https://example.com/skims-london")
        )
        skims_article = result.scalar_one()
        print(f"✓ include_in_digest для Skims: {skims_article.include_in_digest}")
        assert skims_article.include_in_digest == True

        result = await session.execute(
            select(Article).where(Article.url == "https://example.com/market-analysis")
        )
        market_article = result.scalar_one()
        print(f"✓ Стаття з невідомими полями збережена: {market_article.title[:40]}")

    await drop_test_db()
    print("✓ Тестова БД очищена")
    print("\n✅ Всі перевірки пройдені")


asyncio.run(test())
