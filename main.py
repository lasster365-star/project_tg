"""
Точка входа ASGI для деплоя (Render/Fly/Railway и т.п.).
Импортирует приложение из webapp.app, чтобы удовлетворять дефолтному
`uvicorn main:app`, а также оставлена возможность `uvicorn webapp.app:app`.
"""
from webapp.app import app  # noqa: F401
