import os

import discogs_client
from discogs_client.exceptions import HTTPError
from flask import Blueprint, redirect, request, url_for

USER_AGENT = "Discobrain/0.0.1 ( henryoberholtzer@gmail.com )"

bp = Blueprint('discogs', __name__, url_prefix='/discogs')

discogs = discogs_client.Client(
        USER_AGENT,
        consumer_key=os.getenv('DISCOGS_CONSUMER_KEY'),
        consumer_secret=os.getenv('DISCOGS_CONSUMER_SECRET'),
)

@bp.route('/', methods=['GET'])
def login():
    try:
        user = discogs.identity()
        return f'Hello {user.username}'
    except HTTPError as e:
        print(e)
        _, _, url = discogs.get_authorize_url(url_for('discogs.auth', _external=True))
        return f'''
        <html>
            <a href={url} target="_blank">Authorize</a>
        </html>
        '''

@bp.route("/auth", methods=['GET'])
def auth():
    verifier = request.args.get('oauth_verifier')
    discogs.get_access_token(verifier)
    return redirect(url_for('discogs.login'))
