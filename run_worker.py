
from app import create_app
from app.worker import run_worker


if __name__ == "__main__":
    app = create_app()

    run_worker(
        database_path=app.config["DATABASE"],
        poll_interval=1,
    )
