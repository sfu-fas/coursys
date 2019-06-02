import oauth2 as oauth
import requests
import urllib.parse

ACCESS_TOKEN_URL = 'http://localhost:8000/api/oauth/access_token/'

def get_access_token(oauth_token, oauth_secret, oauth_verifier):
    consumer = oauth.Consumer(key='9fdce0e111a1489eb5a42eab7a84306b', secret='liqutXmqJpKmetfs')
    token = oauth.Token(oauth_token, oauth_secret)
    token.set_verifier(oauth_verifier)
    oauth_request = oauth.Request.from_consumer_and_token(consumer, token, http_url=ACCESS_TOKEN_URL)
    oauth_request.sign_request(oauth.SignatureMethod_HMAC_SHA1(), consumer, token)
    response = requests.get(ACCESS_TOKEN_URL, headers=oauth_request.to_header())
    access_token = dict(urllib.parse.parse_qsl(response.content))

    return access_token


import sys
oauth_token = sys.argv[1]
oauth_secret = sys.argv[2]
oauth_verifier = sys.argv[3]
t = get_access_token(oauth_token, oauth_secret, oauth_verifier)
print("Here are your access token and secret:")
print(t['oauth_token'], t['oauth_token_secret'])
