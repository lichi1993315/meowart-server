"""Main FastAPI application with CORS and Session middleware."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.image import router as image_router
from app.core.config import get_settings

settings = get_settings()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        description="Meowart API with hybrid authentication (Google OAuth + Email/Password)",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Session middleware for OAuth state management
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.SECRET_KEY,
        session_cookie=f"{settings.SESSION_COOKIE_NAME}_state",
        max_age=settings.SESSION_MAX_AGE,
        same_site=settings.SESSION_COOKIE_SAMESITE,
        https_only=settings.SESSION_COOKIE_SECURE,
    )

    # CORS middleware for cross-subdomain communication
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            settings.FRONTEND_URL,  # https://meowart.ai
            "https://api.meowart.ai",  # API domain
            "http://localhost:3000",  # Local frontend development
            "http://127.0.0.1:3000",  # Local frontend development
        ],
        allow_credentials=True,  # Required for cookies to work cross-origin
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Register routers
    app.include_router(auth_router)
    app.include_router(image_router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.get("/")
    async def root() -> dict[str, str]:
        """Root endpoint."""
        return {
            "message": "Welcome to Meowart API",
            "docs": "/docs",
            "health": "/health",
        }

    return app


# Create the application instance
app = create_app()
