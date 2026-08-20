from django.http import HttpResponse

from . import button


def webring_gif(request):
    """88x31 webring button, recoloured per request."""
    response = HttpResponse(button.render(button.roll_colors()),
                            content_type='image/gif')
    # fresh gif per view is the point, try to stop caching
    response['Cache-Control'] = 'no-store, max-age=0'
    response['Referrer-Policy'] = 'no-referrer'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
