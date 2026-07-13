from django.shortcuts import render

from django.http import HttpResponse
from .models import Medicine


# Create your views here.
def medicine_list(request):
    medicines = Medicine.objects.all()

    return render(
        request,
        "inventory/medicine_list.html",
        {
            "medicines": medicines,
        },
    )