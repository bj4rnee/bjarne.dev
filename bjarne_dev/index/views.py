from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connection, connections
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.template import loader
from django.urls import reverse
from django.views.generic import ListView

from django import template
from datetime import datetime, timedelta, date

# some cool hsl colors;
# hsl(138,92%,55%);
# hsl(219,53%,69%);
# hsl(252,82%,56%);
# hsl(230,91%,69%);
def index_view(request):
    context = {'time': datetime.now().strftime('%H:%M:%S')}
    return render(request, "index.html", context)