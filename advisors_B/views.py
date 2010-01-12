# Create your views here.
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import Context, loader
from advisors_B.models import *


def index(request):

    return render_to_response("index.html")


def search(request):
    return render_to_response("search.html")
                              
def add_note(request):
    return render_to_response("add.html")

def display_note(request):
    return render_to_response("display.html")
