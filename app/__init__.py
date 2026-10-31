
from pathlib import Path

from flask import Flask

from app.database import init_db


def create_app(test_config=None):
    app = Flask(__name__)

    app.config.from_mapping(
        DATABASE=str(
            Path(app.instance_path) / "events.db"
        ),
    )

    if test_config is not None:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(
        parents=True,
        exist_ok=True,
    )

    init_db(app.config["DATABASE"])

    from app.routes import main_bp

    app.register_blueprint(main_bp)

    return app
