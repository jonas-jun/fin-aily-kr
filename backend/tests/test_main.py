from app.main import app, lifespan


async def test_lifespan_opens_and_closes_shared_http_client():
    async with lifespan(app):
        shared_client = app.state.http
        assert shared_client.is_closed is False

    assert shared_client.is_closed is True
