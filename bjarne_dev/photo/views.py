from django.db.models import F
from django.shortcuts import get_object_or_404, render

from .models import Collection


def index(request):
    # only surface collections that have something to show...
    collections = [c for c in Collection.objects.all() if c.cover_photo()]
    return render(request, 'photo_index.html', {'collections': collections})


def collection(request, slug):
    col = get_object_or_404(Collection, slug=slug)
    photos = col.photographs.filter(published=True).order_by(
        F('display_order').asc(nulls_last=True), '-capture_date', '-upload_date')
    return render(request, 'photo_collection.html',
                  {'collection': col, 'photos': photos})
