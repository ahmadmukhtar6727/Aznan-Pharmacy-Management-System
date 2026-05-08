from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.utils import timezone
from django.db.models import Sum, F
from .models import Medicine, Sale, SaleItem, Expense, Debt, Category
import json
from datetime import timedelta
from django.contrib.auth.models import User

@login_required
def dashboard(request):
    today = timezone.now().date()
    next_month = today + timedelta(days=30)
    
    # Financials for Today
    sales_today = Sale.objects.filter(transaction_date__date=today)
    revenue = sales_today.aggregate(total=Sum('total_after_discount'))['total'] or 0
    expenses = Expense.objects.filter(date=today).aggregate(total=Sum('amount'))['total'] or 0

    # FIXED DEBT CALCULATION
    # This calculates the actual remaining balance across ALL credit sales
    debt_totals = Sale.objects.filter(payment_status='Credit').aggregate(
        total_billed=Sum('total_after_discount'),
        total_paid=Sum('amount_paid')
    )
    
    billed = debt_totals['total_billed'] or 0
    paid_so_far = debt_totals['total_paid'] or 0
    # Debt is only the part that hasn't been paid yet
    actual_debt = float(billed) - float(paid_so_far)
    
    # Profit Calculation
    daily_items = SaleItem.objects.filter(sale__transaction_date__date=today)
    
    # Use float conversion to ensure math stability
    gross_profit = sum((float(item.unit_price) - float(item.buying_price_at_sale)) * item.quantity for item in daily_items)
    total_discounts = sales_today.aggregate(total=Sum('discount'))['total'] or 0
    net_profit = float(gross_profit) - float(total_discounts) - float(expenses)

    # Alerts
    out_of_stock = Medicine.objects.filter(quantity__lte=5)
    near_expiry = Medicine.objects.filter(expiry_date__lte=next_month, expiry_date__gte=today)

    context = {
        'revenue': revenue, 
        'net_profit': net_profit, 
        'gross_profit': gross_profit,
        'expenses': expenses, 
        'debt': actual_debt, 
        'out_of_stock': out_of_stock,
        'near_expiry': near_expiry, 
        'today': today
    }
    return render(request, 'inventory/dashboard.html', context)
@login_required
def add_stock(request):
    if request.method == "POST":
        category_id = request.POST.get('category')
        name = request.POST.get('name').strip() # Get the name and remove extra spaces
        
        if not category_id:
            messages.error(request, "Please select a valid category.")
            return redirect('add_stock')

        try:
            category = Category.objects.get(id=category_id)
            new_qty = int(request.POST.get('quantity', 0))

            # 1. Search for existing medicine by name (case-insensitive)
            # 2. If found, update the fields. If not found, create it.
            medicine, created = Medicine.objects.update_or_create(
                name__iexact=name, # Searches for the name ignoring capital letters
                defaults={
                    'category': category,
                    'buying_price': request.POST.get('buying_price', 0),
                    'wholesale_price': request.POST.get('wholesale_price', 0),
                    'retail_price': request.POST.get('retail_price', 0),
                    'expiry_date': request.POST.get('expiry_date'),
                    'description': request.POST.get('description', '')
                }
            )

            # If it already existed, we ADD the new quantity to the old quantity
            if not created:
                medicine.quantity += new_qty
                medicine.save()
                messages.success(request, f"Updated {name} stock. New total: {medicine.quantity}")
            else:
                # If it's brand new, just set the quantity
                medicine.quantity = new_qty
                medicine.save()
                messages.success(request, f"Added new medicine: {name}")

            return redirect('inventory_list')
            
        except Category.DoesNotExist:
            messages.error(request, "Category not found.")
            
    categories = Category.objects.all()
    return render(request, 'inventory/add_stock.html', {'categories': categories})
@login_required
def reports_view(request):
    # Get dates as strings from the GET request
    from_date = request.GET.get('from_date')
    to_date = request.GET.get('to_date')
    
    # If no date is selected, default to today's date as a string
    if not from_date:
        from_date = timezone.now().date().isoformat()
    if not to_date:
        to_date = timezone.now().date().isoformat()
    
    report_data = Sale.objects.filter(transaction_date__date__range=[from_date, to_date])
    
    revenue = report_data.aggregate(Sum('total_before_discount'))['total_before_discount__sum'] or 0
    discounts = report_data.aggregate(Sum('discount'))['discount__sum'] or 0

    return render(request, 'inventory/reports.html', {
        'report_data': report_data,
        'report_revenue': revenue,
        'report_discounts': discounts,
        'report_net_sales': float(revenue) - float(discounts),
        'from_date': from_date,
        'to_date': to_date
    })

# ... keep the rest of your views (process_sale, etc.) as they were ...

@login_required
def expenses_monitoring(request):
    expenses_list = Expense.objects.all().order_by('-date')
    return render(request, 'inventory/expenses.html', {
        'expenses_list': expenses_list, 
        'today_date': timezone.now().date().isoformat()
    })

@login_required
def add_expense(request):
    if request.method == 'POST':
        Expense.objects.create(
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            amount=request.POST.get('amount'),
            date=request.POST.get('date') or timezone.now().date()
        )
        messages.success(request, "Expense added.")
    return redirect('expenses_monitoring')

@login_required
def delete_expense(request, pk):
    get_object_or_404(Expense, pk=pk).delete()
    return redirect('expenses_monitoring')

@login_required
def staff_management(request):
    staff_list = User.objects.all()
    return render(request, 'inventory/staff_management.html', {'staff_list': staff_list})

@login_required
def add_staff(request):
    if request.method == 'POST':
        user = User.objects.create_user(
            username=request.POST.get('username'),
            password=request.POST.get('password')
        )
        messages.success(request, f"Account for {user.username} created.")
    return redirect('staff_management')

@login_required
def delete_staff(request, pk):
    user = get_object_or_404(User, pk=pk)
    if not user.is_superuser:
        user.delete()
        messages.info(request, "Staff member removed.")
    return redirect('staff_management')

@login_required
def inventory_list(request):
    medicines = Medicine.objects.all().order_by('name')
    return render(request, 'inventory/inventory_list.html', {'medicines': medicines})

@login_required
def delete_medicine(request, pk):
    medicine = get_object_or_404(Medicine, pk=pk)
    medicine.delete()
    messages.info(request, "Medicine removed from inventory.")
    return redirect('inventory_list')

@login_required
def debt_tracker(request):
    # Calculate balance on the fly for the template
    debts = Sale.objects.filter(payment_status='Credit').annotate(
        remaining_balance=F('total_after_discount') - F('amount_paid')
    ).exclude(remaining_balance=0)
    return render(request, 'inventory/debt_tracker.html', {'debts': debts})

@login_required
def update_debt(request, pk):
    if request.method == 'POST':
        sale = get_object_or_404(Sale, pk=pk)
        try:
            payment = float(request.POST.get('payment_amount', 0))
            sale.amount_paid = float(sale.amount_paid) + payment
            
            # If the balance is cleared, change status
            if sale.amount_paid >= sale.total_after_discount:
                sale.payment_status = 'Paid'
                
            sale.save()
            messages.success(request, f"Received ₦{payment} from {sale.customer_name}.")
        except ValueError:
            messages.error(request, "Invalid payment amount.")
            
    return redirect('debt_tracker')
@login_required
def sale_outlet(request):
    medicines = Medicine.objects.filter(quantity__gt=0)
    return render(request, 'inventory/sale_outlet.html', {'medicines': medicines})

@login_required
def process_sale(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            sale = Sale.objects.create(
                cashier=request.user,
                customer_name=data.get('customer_name', 'Walking Customer'),
                payment_status=data.get('payment_status', 'Paid'),
                discount=float(data.get('discount', 0)),
            )
            
            total_before = 0
            for item in data.get('items', []):
                med = Medicine.objects.get(id=item['id'])
                qty = int(item['qty'])
                price = float(item['price'])
                subtotal = qty * price
                
                SaleItem.objects.create(
                    sale=sale, medicine=med, quantity=qty,
                    price_type=item['price_type'], unit_price=price,
                    buying_price_at_sale=med.buying_price, subtotal=subtotal
                )
                med.quantity -= qty
                med.save()
                total_before += subtotal
                
            sale.total_before_discount = total_before
            sale.total_after_discount = total_before - float(sale.discount)
            sale.save()
            
            return JsonResponse({'success': True, 'sale_id': sale.id})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False})

def print_receipt(request, sale_id):
    sale = get_object_or_404(Sale, id=sale_id)
    items = SaleItem.objects.filter(sale=sale)
    # This string "inventory/receipt.html" matches the folder path
    return render(request, 'inventory/receipt.html', {
        'sale': sale,
        'items': items,
    })