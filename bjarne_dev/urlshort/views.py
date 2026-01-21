from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError
from django.http import JsonResponse

import secrets
import string
from urllib.parse import urlparse
from django.utils import timezone

from .models import Shorted_url

# validate URI, allow any scheme except unsafe ones
def is_valid_uri(uri):
    unsafe_schemes = {'javascript', 'data', 'vbscript'}
    try:
        parsed = urlparse(uri)
        scheme = parsed.scheme.lower()

        # block unsafe schemes
        if scheme in unsafe_schemes:
            return False, f"Unsupported scheme :<"
        
        # URI has a valid structure (at least scheme + some content)
        if scheme in {'http', 'https'}:
            validator = URLValidator()
            validator(uri)
            return True, ""
        
        # for mailto, netloc is optional, but path should contain an email-like string
        if scheme == 'mailto' and not parsed.path:
            return False, "'mailto' must include an email address"
        
        # max length check (2048 chars)
        if len(uri) > 2048:
            return False, "URL is too long o.o"
        
        return True, ""
    
    except (ValueError, ValidationError) as e:
        return False, "The URL is invalid :("

# on get request
def url_short_view(request):
    hash = ""
    error = True
    paragraph = "no url entered..."
    url = request.GET.get('url', None)
    json = request.GET.get('json', None)

    # trim whitespace
    if url:
        url = url.strip()

    # parse URL and if it has no scheme, assume https
    parsed = urlparse(url)
    if url and not parsed.scheme:
        url = "https://" + url
        parsed = urlparse(url)

    # validate if URL is real, 2048 max length allowed
    try:
        if url:
            is_valid, error_msg = is_valid_uri(url)
            if settings.DEBUG:
                print(f"Validating URL: {url} - Valid: {is_valid}, Error: {error_msg}")
            if is_valid:
                hash = shorten(url)
                error = False
            else:
                paragraph = error_msg
        else:
            paragraph = "No URL entered..."
    except ValueError as e:
        paragraph = str(e)
    except Exception as e:
        paragraph = "An unexpected error occurred. Please try again later -.-"
    
    context = {"hash": hash, "error": error, "paragraph": paragraph, "new_url": f"https://bjarne.dev/s/{hash}", "og_url": url}

    if json:
        return JsonResponse(context)
    
    return render(request, "urlshort.html", context)

# fetch URL-Model-Object from Database with hash and redirect
# if no hash is found, raise 404
def redirect_hash(request, url_hash):
    mapping = get_object_or_404(Shorted_url, hash=url_hash)
    original_url = mapping.original_url
    parsed = urlparse(original_url)

    # safe schemes redirect immediately
    safe_schemes = {'http', 'https', 'ftp'}
    if parsed.scheme.lower() in safe_schemes:
        return redirect(original_url)
    
    # non-standard schemes require confirmation
    return render(request, "confirm-redirect.html", {
        "original_url": original_url,
        "scheme": parsed.scheme.lower(),
        "short_url": f"https://bjarne.dev/s/{url_hash}"
    })


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
