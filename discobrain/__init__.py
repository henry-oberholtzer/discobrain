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

from . import auth, mb_auth
from .batch_store import (
    DEFAULT_BATCH_ID,
    BatchItemRecord,
    BatchStatus,
    BatchStore,
)
from .parser import parse_discogs_ids
from .pipeline import (
    build_converter,
    get_musicbrainz_lookup,
    process_batch,
    reevaluate_pending_items,
)
from .release_converter.musicbrainz import MusicBrainzLookUp

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("DISCOBRAIN_SECRET_KEY", "dev-secret-key-change-me")
app.register_blueprint(auth.bp)
app.register_blueprint(mb_auth.bp)


def get_db_path() -> str:
    db_path = app.config.get("DISCOBRAIN_DB") or os.getenv("DISCOBRAIN_DB")
    if not db_path:
        os.makedirs(app.instance_path, exist_ok=True)
        db_path = os.path.join(app.instance_path, "discobrain.db")
    return db_path


def get_batch_store() -> BatchStore:
    return BatchStore(get_db_path())


def get_lookup() -> MusicBrainzLookUp:
    return get_musicbrainz_lookup(get_db_path())


@app.context_processor
def inject_app_context():
    store = get_batch_store()
    active_batch = store.get_or_create_batch()
    lookup = get_lookup()
    cache_count = lookup.get_cache_count()
    return {
        "active_batch": active_batch,
        "cache_count": cache_count,
    }


class AppUser(TypedDict):
    authenticated: bool
    username: str | None
    rate_limit: int


class MusicBrainzUser(TypedDict):
    authenticated: bool
    username: str | None


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
    elif session.get("discogs_user_token"):
        user["authenticated"] = True
        user["username"] = session.get("discogs_username") or "Token User"
        user["rate_limit"] = 60
    elif os.getenv("DISCOGS_USER_TOKEN") or os.getenv("DISCOGS_API_KEY"):
        user["authenticated"] = True
        user["username"] = "API Token User"
        user["rate_limit"] = 60
    g.user = user

    mb_user: MusicBrainzUser = {
        "authenticated": False,
        "username": None,
    }
    if session.get("musicbrainz_oauth_token"):
        mb_user["authenticated"] = True
        mb_user["username"] = session.get("musicbrainz_username") or "MusicBrainz User"
    g.musicbrainz = mb_user


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
    batch = store.get_or_create_batch()
    batch_id = batch.id

    existing_items = store.get_items(batch_id)
    existing_discogs_ids = {item.discogs_id for item in existing_items}

    added_count = 0
    for d_id in discogs_ids:
        if d_id not in existing_discogs_ids:
            store.add_item(batch_id, discogs_id=d_id)
            existing_discogs_ids.add(d_id)
            added_count += 1

    lookup = get_lookup()
    converter = build_converter(lookup=lookup, session_data=dict(session))
    base_url = request.host_url

    errors = process_batch(
        batch_id=batch_id,
        batch_store=store,
        lookup=lookup,
        converter=converter,
        base_url=base_url,
    )

    for err in errors or []:
        flash(err, "error")

    successful_count = added_count - len(errors or [])
    if successful_count > 0:
        flash(f"Processed {successful_count} release(s).", "success")
    elif added_count == 0:
        flash("Submitted release(s) are already in your batch.", "info")

    batch_record = store.get_batch(batch_id)
    if batch_record and batch_record.total_items == 0:
        return redirect(url_for("index"))
    return redirect(url_for("submissions_view", batch_id=batch_id))


@app.route("/submissions", methods=["GET"])
@app.route("/submissions/<batch_id>", methods=["GET"])
def submissions_view(batch_id: str | None = None):
    store = get_batch_store()
    b_id = batch_id or DEFAULT_BATCH_ID
    batch = store.get_batch(b_id)
    if not batch:
        if batch_id and batch_id != DEFAULT_BATCH_ID:
            flash(f"Batch '{batch_id}' not found.", "error")
            return redirect(url_for("index"))
        batch = store.get_or_create_batch()

    items = store.get_items(batch.id)
    return render_template("submissions.html", batch=batch, items=items)


@app.route("/submissions/items/<int:item_id>/mark-submitted", methods=["POST"])
@app.route("/submissions/<batch_id>/items/<int:item_id>/mark-submitted", methods=["POST"])
def mark_submitted(item_id: int, batch_id: str | None = None):
    store = get_batch_store()
    store.complete_item(item_id)
    b_id = batch_id or DEFAULT_BATCH_ID
    batch = store.get_batch(b_id)
    if batch and batch.pending_count == 0:
        store.update_batch_status(b_id, BatchStatus.COMPLETED.value)
    flash("Release marked as submitted.", "success")
    return redirect(url_for("submissions_view", batch_id=b_id))


@app.route("/submissions/next", methods=["GET"])
@app.route("/submissions/<batch_id>/next", methods=["GET"])
def submissions_next(batch_id: str | None = None):
    store = get_batch_store()
    b_id = batch_id or DEFAULT_BATCH_ID
    batch = store.get_batch(b_id)
    if not batch:
        flash(f"Batch '{b_id}' not found.", "error")
        return redirect(url_for("index"))

    next_item = store.get_next_pending_item(b_id)
    if not next_item:
        store.update_batch_status(b_id, BatchStatus.COMPLETED.value)
        flash("All releases in this batch have been submitted!", "success")
        return redirect(url_for("submissions_view", batch_id=b_id))

    mode = request.args.get("mode")
    if mode == "sequential":
        payload = dict(next_item.payload)
        if "redirect_uri" in payload and "mode=sequential" not in payload["redirect_uri"]:
            sep = "&" if "?" in payload["redirect_uri"] else "?"
            payload["redirect_uri"] = f"{payload['redirect_uri']}{sep}mode=sequential"
            next_item.payload = payload

    return render_template("seed_redirect.html", item=next_item, batch=batch, mode=mode)


@app.route("/callback", methods=["GET"])
def callback():
    batch_id = request.args.get("batch_id")
    discogs_id_raw = request.args.get("discogs_id")
    release_mbid = request.args.get("release_mbid")
    mode = request.args.get("mode")

    if not batch_id:
        flash("Missing batch ID in callback parameter.", "warning")
        return redirect(url_for("index"))

    store = get_batch_store()
    batch = store.get_batch(batch_id)
    if not batch:
        flash(f"Batch '{batch_id}' not found.", "error")
        return redirect(url_for("index"))

    discogs_id: int | None = None
    if discogs_id_raw:
        try:
            discogs_id = int(discogs_id_raw)
        except ValueError:
            discogs_id = None

    lookup = get_lookup()

    item: BatchItemRecord | None = None
    if discogs_id is not None:
        item = store.get_item_by_discogs_id(batch_id, discogs_id)

    if release_mbid:
        if discogs_id is not None:
            discogs_url = f"https://www.discogs.com/release/{discogs_id}"
            lookup.store(discogs_url, release_mbid, relationship="release")

        if item:
            store.complete_item(item.id)

    # Dynamic re-evaluation of remaining pending releases in this batch
    converter = build_converter(lookup=lookup, session_data=dict(session))
    base_url = request.host_url
    reevaluate_pending_items(
        batch_id=batch_id,
        batch_store=store,
        lookup=lookup,
        converter=converter,
        base_url=base_url,
    )

    if mode == "sequential":
        next_item = store.get_next_pending_item(batch_id)
        if next_item:
            return redirect(url_for("submissions_next", batch_id=batch_id, mode="sequential"))
        store.update_batch_status(batch_id, BatchStatus.COMPLETED.value)
        flash("All releases in this batch have been successfully submitted!", "success")
        return redirect(url_for("submissions_view", batch_id=batch_id))

    return render_template(
        "callback_success.html",
        batch=batch,
        item=item,
        discogs_id=discogs_id,
        release_mbid=release_mbid,
    )


@app.route("/batch/clear", methods=["POST"])
def clear_batch():
    store = get_batch_store()
    store.clear_batch()
    flash("Batch queue cleared successfully.", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/cache/clear", methods=["POST"])
def clear_cache():
    lookup = get_lookup()
    lookup.clear_cache()
    flash("MusicBrainz URL/MBID cache cleared successfully.", "success")
    return redirect(request.referrer or url_for("index"))
