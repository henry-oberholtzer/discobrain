import os

from dotenv import load_dotenv
from flask import Flask

from . import auth

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("DISCOBRAIN_SECRET_KEY")
app.register_blueprint(auth.bp)

@app.route("/")
def index():
    return "Hello"


@app.route("/submit")
def form():
    html = """
    <html>
        <form id="form" action="https://musicbrainz.org/release/add" method="post" target="_blank">
            <input type="submit" value="Submit to MusicBrainz">
        </form>
        <button
    </html>
    """
    return html
