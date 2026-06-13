import uvicorn

from pagedoctor.config import load_settings


def main() -> None:
    # Dev runner: host/port come from the same Settings the app validates, so a
    # local run honors APP_HOST/APP_PORT instead of uvicorn's CLI defaults.
    settings = load_settings()
    uvicorn.run(
        "pagedoctor.app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=True,
    )


if __name__ == "__main__":
    main()
