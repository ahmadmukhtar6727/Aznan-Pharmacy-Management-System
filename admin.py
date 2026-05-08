from django.contrib import admin
from .models import Category, Medicine

admin.site.site_header = "AZNAN PHARMACY MANAGEMENT"

class MedicineAdmin(admin.ModelAdmin):
    # This controls which columns show up in the table list
    list_display = ('name', 'category', 'quantity', 'buying_price', 'wholesale_price', 'retail_price', 'expiry_date')
    
    # This adds a search bar
    search_fields = ('name',)
    
    # This adds filters on the right side
    list_filter = ('category', 'expiry_date')

admin.site.register(Category)
admin.site.register(Medicine, MedicineAdmin)