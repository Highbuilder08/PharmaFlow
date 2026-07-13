from django.shortcuts import redirect, render

from django.http import HttpResponse
from .forms import MedicineForm
from .models import Medicine


# Create your views here.
def medicine_list(request):
    medicines = Medicine.objects.all()

    return render(
        request,
        "inventory/medicine_list.html",
        { "medicines": medicines }
    )
    
def medicine_create(request):
    if request.method == "POST":
        form = MedicineForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("inventory:medicine_list")
    else:
        form = MedicineForm()

    return render(
        request,
        "inventory/medicine_form.html",
        { "form": form }
    )