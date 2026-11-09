import os

import requests
from flask import Blueprint, redirect, request, session, url_for
from oauthlib.oauth1 import OAuth1Error
from requests_oauthlib import OAuth1Session

DISCOGS_REQUEST_TOKEN_URL = "https://api.discogs.com/oauth/request_token"
DISCOGS_AUTHORIZE_URL = "https://discogs.com/oauth/authorize"
DISCOGS_ACCESS_TOKEN_URL = "https://api.discogs.com/oauth/access_token"
DISCOGS_IDENTITY_URL = "https://api.discogs.com/oauth/identity"

USER_AGENT = "Discobrain/0.0.1 ( henryoberholtzer@gmail.com )"

bp = Blueprint('discogs', __name__, url_prefix='/discogs')


def get_consumer_credentials() -> tuple[str, str]:
    consumer_key = os.getenv('DISCOGS_CONSUMER_KEY') or ""
    consumer_secret = os.getenv('DISCOGS_CONSUMER_SECRET') or ""
    return consumer_key, consumer_secret


@bp.route('/', methods=['GET'])
def login():
    consumer_key, consumer_secret = get_consumer_credentials()
    access_token = session.get('discogs_access_token')
    access_token_secret = session.get('discogs_access_token_secret')

    if access_token and access_token_secret:
        discogs = OAuth1Session(
            client_key=consumer_key,
            client_secret=consumer_secret,
            resource_owner_key=access_token,
            resource_owner_secret=access_token_secret,
        )
        resp = discogs.get(DISCOGS_IDENTITY_URL, headers={'User-Agent': USER_AGENT})
        if resp.status_code == 200:
            user_data = resp.json()
            username = user_data.get('username', 'User')
            return f'Hello {username}'

    discogs = OAuth1Session(
        client_key=consumer_key,
        client_secret=consumer_secret,
        callback_uri=url_for('discogs.auth', _external=True),
    )
    try:
        req_token_dict = discogs.fetch_request_token(
            DISCOGS_REQUEST_TOKEN_URL,
            headers={'User-Agent': USER_AGENT},
        )
        session['discogs_req_token'] = req_token_dict.get('oauth_token')
        session['discogs_req_token_secret'] = req_token_dict.get('oauth_token_secret')
        auth_url = discogs.authorization_url(DISCOGS_AUTHORIZE_URL)
        return f'''
        <html>
            <a href="{auth_url}" target="_blank">Authorize</a>
        </html>
        '''
    except (OAuth1Error, requests.RequestException) as e:
        return f"Authentication error: {e}", 500


@bp.route("/auth", methods=['GET'])
def auth():
    consumer_key, consumer_secret = get_consumer_credentials()
    verifier = request.args.get('oauth_verifier')
    req_token = session.get('discogs_req_token')
    req_token_secret = session.get('discogs_req_token_secret')

    if not verifier or not req_token or not req_token_secret:
        return "Invalid OAuth verification flow.", 400

    discogs = OAuth1Session(
        client_key=consumer_key,
        client_secret=consumer_secret,
        resource_owner_key=req_token,
        resource_owner_secret=req_token_secret,
        verifier=verifier,
    )
    tokens = discogs.fetch_access_token(
        DISCOGS_ACCESS_TOKEN_URL,
        headers={'User-Agent': USER_AGENT},
    )
    session['discogs_access_token'] = tokens.get('oauth_token')
    session['discogs_access_token_secret'] = tokens.get('oauth_token_secret')
    return redirect(url_for('discogs.login'))


@bp.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('discogs_access_token', None)
    session.pop('discogs_access_token_secret', None)
    session.pop('discogs_req_token', None)
    session.pop('discogs_req_token_secret', None)
    session.pop('discogs_username', None)
    return redirect(url_for('index'))
