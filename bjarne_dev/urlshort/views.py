from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

import random
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
            paragraph = "the URL is invalid :("

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
    
    for _ in range(250):
        # create random 5 letter ascii string (916132832 possible combinations)
        random_hash = ''.join(random.choices(string.ascii_letters + string.digits, k=5))
        if not Shorted_url.objects.filter(hash=random_hash).exists():
            mapping = Shorted_url(original_url=url, hash=random_hash, creation_date=timezone.now())
            mapping.save()
            return random_hash

    # as fallback overwrite the oldest record
    oldest = Shorted_url.objects.order_by('creation_date').first()
    if oldest:
        oldest.original_url = url
        oldest.creation_date = timezone.now()
        oldest.save()
        return oldest.hash
    else:
        raise Exception("[Error]: No available hashes and database is empty.")
