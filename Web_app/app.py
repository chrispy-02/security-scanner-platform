import os
from flask_app import create_app

app = create_app()

if __name__ == "__main__":
    # Development server only. Production is served by gunicorn (see Dockerfile).
    # use_reloader=False so the background scan scheduler thread isn't duplicated.
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)), use_reloader=False)
