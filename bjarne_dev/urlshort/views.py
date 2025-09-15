from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

import random
import secrets
import string
from urllib.parse import urlparse
from django.utils import timezone

from .models import Shorted_url

# on get request
def url_short_view(request):
    hash = ""
    error = True
    paragraph = "no url entered..."
    url = request.GET.get('url', None)
    validator = URLValidator()

    # parse URL and if it has no scheme, assume https
    parsed = urlparse(url)
    if url and not parsed.scheme:
        url = "https://" + url
        parsed = urlparse(url)

    # validate if URL is real, 2048 max length allowed
    try:
        validator(url)
        hash = shorten(url)
        error = False
    except ValidationError:
        if url:
            paragraph = "The URL is invalid :("
    except ValueError as e:
        paragraph = str(e)
    except Exception as e:
            paragraph = "An unexpected error occurred. Please try again later -.-"
    
    context = {"hash": hash, "error": error, "paragraph": paragraph, "new_url": f"https://bjarne.dev/s/{hash}", "og_url": url}
    return render(request, "urlshort.html", context)

def url_short_get(request, url):
    print(url)
    redirect_hash(request, url)

# fetch URL-Model-Object from Database with hash and redirect
# if no hash is found, raise 404
def redirect_hash(request, url_hash):
    mapping = get_object_or_404(Shorted_url, hash=url_hash)
    return redirect(mapping.original_url)

def shorten(url):
    # check if  URL was already shortened
    existing = Shorted_url.objects.filter(original_url=url).first()
    if existing:
        return existing.hash
    
    hash_length = 5
    max_attempts = 250
    
    while hash_length <= 8:
        for _ in range(max_attempts):
            # create random 5 letter ascii string (916132832 possible combinations)
            random_hash = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(hash_length))
            if not Shorted_url.objects.filter(hash=random_hash).exists():
                mapping = Shorted_url(original_url=url, hash=random_hash, creation_date=timezone.now())
                mapping.save()
                return random_hash
        hash_length += 1  # increase length if max attempts reached. Waaay more possible combinations

    # all lengths fail (extremely unlikely), raise error
    raise ValueError("Unable to generate a unique short URL after maximum attempts :<")
