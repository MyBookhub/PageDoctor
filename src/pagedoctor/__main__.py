import uvicorn

from pagedoctor.config import load_settings


def main() -> None:
    settings = load_settings()
    uvicorn.run(
        "pagedoctor.app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
