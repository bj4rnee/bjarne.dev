from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db import connection, connections
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.template import loader

from django import template
from datetime import datetime, timedelta, date

def uptime_view(request):
    # currently I just redirect the user to my uptimerobot page, where all important services are tracked
    return redirect('https://stats.uptimerobot.com/gOp8gcPYMl')