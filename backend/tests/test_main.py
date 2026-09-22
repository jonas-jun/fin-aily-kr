from app.main import app, lifespan


async def test_lifespan_opens_and_closes_shared_http_client():
    async with lifespan(app):
        shared_client = app.state.http
        assert shared_client.is_closed is False
        # 레거시 경로 302 이관을 통과하려면 공용 클라이언트도 리다이렉트를 따라가야 한다.
        assert shared_client.follow_redirects is True

    assert shared_client.is_closed is True
