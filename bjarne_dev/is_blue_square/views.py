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

def ibs_view(request):
    context = {}
    return render(request, "index.html", context)