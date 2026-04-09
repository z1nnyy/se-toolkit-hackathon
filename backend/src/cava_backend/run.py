import uvicorn

from cava_backend.settings import settings


def run_server() -> None:
    uvicorn.run(
        app="cava_backend.main:app",
        host=settings.address,
        port=settings.port,
        reload=settings.reload,
    )


if __name__ == "__main__":
    run_server()
