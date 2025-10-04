from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render, redirect
from django.core.cache import cache
from datetime import datetime, timedelta, date
import secrets
from .models import VisitCounter
from django.db.models import F

# some cool hsl colors;
# hsl(138,92%,55%);
# hsl(219,53%,69%);
# hsl(252,82%,56%);
# hsl(230,91%,69%);
def index_view(request):
    # unique token for this visit
    token = secrets.token_urlsafe(16)
    cache.set(token, 1, timeout=300)  # 5-minute TTL
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
    if cache.get(token):
        # atomic increment in DB
        updated = VisitCounter.objects.filter(pk=1).update(count=F('count') + 1)
        if updated == 0:
            # create with count=1 if it didnt exist
            VisitCounter.objects.create(pk=1, count=1)
        cache.delete(f'visit_token_{token}')
        return JsonResponse({'status': 'ok'})
    return JsonResponse({'status': 'invalid'}, status=400)
