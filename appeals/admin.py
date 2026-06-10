from django.contrib import admin
from .models import Category, Status, Appeal, AppealHistory

admin.site.register(Category)
admin.site.register(Status)
admin.site.register(Appeal)
admin.site.register(AppealHistory)