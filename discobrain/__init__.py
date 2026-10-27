from dotenv import load_dotenv
from flask import Flask

from .mb_release import MBRelease

USER_AGENT = "DiscogsToMB/0.0.1 ( henryoberholtzer@gmail.com )"

load_dotenv()

app = Flask(__name__)

@app.route("/")
def index():
    return "Hello!"

@app.route("/submit")
def form():
    release = MBRelease(name="Unique Release Title", comment="comment")
    inputs = [f"<input hidden name='{pair[0]}' value='{pair[1]}'>\r" for pair in release.flatten().items()]
    html = f"""
    <html>
        <form id="form" action="https://musicbrainz.org/release/add" method="post" target="_blank">
            {"".join(inputs)}
            <input type="submit" value="Submit to MusicBrainz">
        </form>
        <button
    </html>
    """
    return html
