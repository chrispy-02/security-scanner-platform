#--------------------------------------------------
# Import Requirements
#--------------------------------------------------
import os
import secrets
from flask import Flask
from flask_failsafe import failsafe
from flask_app.scheduler import Scheduler


def _is_production():
    return os.getenv("FLASK_ENV", "production").lower() == "production"


#--------------------------------------------------
# Create a Failsafe Web Application
#--------------------------------------------------
@failsafe
def create_app(debug=None):
    app = Flask(__name__)

    app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0

    # Secret key: required in production, ephemeral fallback for local convenience.
    secret = os.getenv("FLASK_SECRET_KEY")
    if not secret:
        if _is_production():
            raise RuntimeError("FLASK_SECRET_KEY must be set in production.")
        secret = secrets.token_hex(32)
        app.logger.warning(
            "FLASK_SECRET_KEY not set; using an ephemeral dev key (sessions reset on restart)."
        )
    app.secret_key = secret

    # Debug is strictly off in production; otherwise controlled by FLASK_DEBUG.
    if debug is None:
        debug = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true") and not _is_production()
    app.debug = debug

    # Optional explicit host/domain for url_for(_external=True) (e.g. OAuth redirects).
    server_name = os.getenv("SERVER_NAME")
    if server_name:
        app.config["SERVER_NAME"] = server_name

    # Harden session cookies (Secure only over HTTPS in production).
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=_is_production(),
    )

    # Behind a TLS-terminating proxy (e.g. Render), trust forwarded headers so that
    # url_for(_external=True) builds correct https OAuth redirect URIs.
    if _is_production():
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
        app.config["PREFERRED_URL_SCHEME"] = "https"

    # makes the database and the scheduler accessible throughout the app
    from .utils.database.database import database
    db = database()
    app.db = db

    schedulerThread = Scheduler(app, app.db)
    schedulerThread.start_scheduler()
    app.scheduler = schedulerThread

    # Minimal security headers on every response.
    @app.after_request
    def set_security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return resp

    with app.app_context():
        from . import routes
        return app
