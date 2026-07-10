from django.contrib import admin

from .models import Pharmacy
from .models import User

admin.site.register(Pharmacy)
admin.site.register(User)
