import os
from typing import TypedDict

from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from . import auth
from .batch_store import BatchStore
from .parser import parse_discogs_ids

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("DISCOBRAIN_SECRET_KEY", "dev-secret-key-change-me")
app.register_blueprint(auth.bp)


def get_batch_store() -> BatchStore:
    db_path = app.config.get("DISCOBRAIN_DB")
    if not db_path:
        os.makedirs(app.instance_path, exist_ok=True)
        db_path = os.path.join(app.instance_path, "discobrain.db")
    return BatchStore(db_path)


class AppUser(TypedDict):
    authenticated: bool
    username: str | None
    rate_limit: int


@app.before_request
def load_user():
    user: AppUser = {
        "authenticated": False,
        "username": None,
        "rate_limit": 25,
    }
    if session.get("discogs_access_token"):
        user["authenticated"] = True
        user["username"] = session.get("discogs_username") or "Discogs User"
        user["rate_limit"] = 60
    elif os.getenv("DISCOGS_USER_TOKEN") or os.getenv("DISCOGS_API_KEY"):
        user["authenticated"] = True
        user["username"] = "API Token User"
        user["rate_limit"] = 60
    g.user = user


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/parse", methods=["POST"])
def parse():
    raw_urls = request.form.get("raw_urls", "")
    file = request.files.get("file")

    file_content = ""
    if file and file.filename:
        file_content = file.read().decode("utf-8", errors="replace")

    combined_input = f"{raw_urls}\n{file_content}"
    discogs_ids = parse_discogs_ids(combined_input)

    if not discogs_ids:
        flash("Please provide at least one valid Discogs release URL or ID.", "error")
        return redirect(url_for("index"))

    store = get_batch_store()
    batch_id = store.create_batch()
    for d_id in discogs_ids:
        store.add_item(batch_id, discogs_id=d_id)

    flash(f"Parsed {len(discogs_ids)} release ID(s).", "success")
    return redirect(url_for("submissions_view", batch_id=batch_id))


@app.route("/submissions/<batch_id>")
def submissions_view(batch_id: str):
    store = get_batch_store()
    batch = store.get_batch(batch_id)
    if not batch:
        flash(f"Batch '{batch_id}' not found.", "error")
        return redirect(url_for("index"))

    items = store.get_items(batch_id)
    return render_template("submissions.html", batch=batch, items=items)
