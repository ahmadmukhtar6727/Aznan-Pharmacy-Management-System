from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

# 1. CATEGORY must come first because Medicine depends on it
class Category(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

# 2. MEDICINE comes second
class Medicine(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField(default=0)
    buying_price = models.DecimalField(max_digits=10, decimal_places=2)
    wholesale_price = models.DecimalField(max_digits=10, decimal_places=2)
    retail_price = models.DecimalField(max_digits=10, decimal_places=2)
    expiry_date = models.DateField()
    date_added = models.DateTimeField(auto_now_add=True)

    def is_near_expiry(self):
        # Checks if medicine expires within the next 30 days
        return self.expiry_date <= timezone.now().date() + timedelta(days=30)

    def __str__(self):
        return self.name

# 3. SALE comes third
class Sale(models.Model):
    PAYMENT_CHOICES = [('Paid', 'Paid'), ('Credit', 'Credit')]
    cashier = models.ForeignKey(User, on_delete=models.CASCADE)
    customer_name = models.CharField(max_length=200, default="Walking Customer")
    transaction_date = models.DateTimeField(auto_now_add=True)
    total_before_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_after_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='Paid')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Sale {self.id} - {self.customer_name}"

# 4. SALEITEM must come after both Sale and Medicine
class SaleItem(models.Model):
    sale = models.ForeignKey(Sale, related_name='items', on_delete=models.CASCADE)
    medicine = models.ForeignKey(Medicine, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    price_type = models.CharField(max_length=20) # e.g., 'Wholesale' or 'Retail'
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    buying_price_at_sale = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.medicine.name} x {self.quantity}"

# 5. EXPENSE can go anywhere
class Expense(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(default=timezone.now)

    def __str__(self):
        return self.title

# 6. DEBT can go anywhere
class Debt(models.Model):
    customer_name = models.CharField(max_length=200)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    remaining_balance = models.DecimalField(max_digits=10, decimal_places=2)
    date_created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer_name} - {self.remaining_balance}"