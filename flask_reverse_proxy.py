from urllib.parse import urlparse, urlunparse
from flask import Flask, request
import requests

UPSTREAM_HOST = 'example.com'
app = Flask(__name__)

@app.errorhandler(404)
def page_not_found(e):
    parsed = urlparse(request.url)
    replaced = parsed._replace(netloc=UPSTREAM_HOST)
    url = urlunparse(replaced)
    return requests.get(url).text
