import oauth2 as oauth
import requests

# using the tokens in the fixture: python api/demo4_use_access_token.py 3e9be729117c4accab214037771c0f92 8r9KjHOuDiENhQH7

RESOURCE_URL = 'http://localhost:8000/api/1/offerings/'

def use_access_token(oauth_token, oauth_secret):
    consumer = oauth.Consumer(key='9fdce0e111a1489eb5a42eab7a84306b', secret='liqutXmqJpKmetfs')
    token = oauth.Token(oauth_token, oauth_secret)
    oauth_request = oauth.Request.from_consumer_and_token(consumer, http_url=RESOURCE_URL)
    oauth_request.sign_request(oauth.SignatureMethod_HMAC_SHA1(), consumer, token)

    # get the resource
    response = requests.get(RESOURCE_URL, headers=oauth_request.to_header())
    return response.text


import sys
oauth_token = sys.argv[1]
oauth_secret = sys.argv[2]
print(use_access_token(oauth_token, oauth_secret))