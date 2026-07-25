from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.core.cache import cache
from datetime import datetime, timedelta, date
import secrets
from bjarne_dev import ratelimit
from .models import VisitCounter
from django.db.models import F


def index_view(request):
    # unique token for this visit
    token = secrets.token_urlsafe(16)
    key = f'visit-token:{token}'
    cache.set(key, 1, timeout=300)  # 5-minute TTL
    # get total visits from DB (no create if not exists)
    try:
        total_visits = VisitCounter.objects.get(pk=1).count
    except VisitCounter.DoesNotExist:
        total_visits = 0
    context = {
        'time': datetime.now().strftime('%H:%M:%S'),
        'visit_token': token,
        'total_visits': str(total_visits + 1).zfill(5),
    }
    return render(request, "index.html", context)

def track_visit(request):
    token = request.GET.get('token')
    key = f'visit-token:{token}'
    if cache.get(key):
        # only "real" page loads should reach here, so this bounds counter inflation
        if not ratelimit.allow(request, 'idx:visit',
                               per_ip=settings.INDEX_VISIT_IP_RATE,
                               global_=settings.INDEX_VISIT_RATE):
            return JsonResponse({'status': 'rate_limited'}, status=429)
        # atomic increment in DB
        updated = VisitCounter.objects.filter(pk=1).update(count=F('count') + 1)
        if updated == 0:
            # create with count=1 if it didnt exist
            VisitCounter.objects.create(pk=1, count=1)
        cache.delete(key)
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'invalid'}, status=400)

# custom csrf failure view to use 403.html
def csrf_failure(request, reason=""):
    return render(request, "403.html", {"reason": reason}, status=403)
