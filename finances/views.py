import json
import datetime
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncMonth
from django.utils import timezone
from django.contrib.auth import login
from .models import Transaction, TransactionLineItem, Budget, Debt, SavingsGoal, UserProfile
from .forms import TransactionForm, TransactionLineItemFormSet, BudgetForm, DebtForm, SavingsGoalForm, ExtendedRegistrationForm
from .models import Transaction, TransactionLineItem, Budget, Debt, SavingsGoal
from .forms import TransactionForm, TransactionLineItemFormSet, BudgetForm, DebtForm, SavingsGoalForm
from django.contrib.auth import login
from .models import Transaction, TransactionLineItem, Budget, Debt, SavingsGoal, UserProfile
from .forms import TransactionForm, TransactionLineItemFormSet, BudgetForm, DebtForm, SavingsGoalForm, ExtendedRegistrationForm
import csv
from django.http import HttpResponse
from django.core.paginator import Paginator

from django.db.models import Sum
from django.utils import timezone
import datetime

# ==========================================
# MAIN DASHBOARD ENGINE
# ==========================================
@login_required
def dashboard(request):
    # 1. Establish the timeframe (Current Month)
    today = timezone.now().date()
    first_of_month = today.replace(day=1)

    # 2. Calculate Total All-Time Balance (All Income - All Expenses)
    all_income = Transaction.objects.filter(user=request.user, transaction_type='INCOME').aggregate(total=Sum('total_amount'))['total'] or 0
    all_expenses = Transaction.objects.filter(user=request.user, transaction_type='EXPENSE').aggregate(total=Sum('total_amount'))['total'] or 0
    total_balance = all_income - all_expenses

    # 3. Calculate Monthly Cash Flow (Current Month Only)
    monthly_income = Transaction.objects.filter(
        user=request.user, 
        transaction_type='INCOME', 
        date__gte=first_of_month
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    monthly_expenses = Transaction.objects.filter(
        user=request.user, 
        transaction_type='EXPENSE', 
        date__gte=first_of_month
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # 4. Grab the 5 most recent transactions
    recent_transactions = Transaction.objects.filter(user=request.user).order_by('-date', '-id')[:5]

    # 5. Send it all to the frontend
    context = {
        'total_balance': total_balance,
        'monthly_income': monthly_income,
        'monthly_expenses': monthly_expenses,
        'recent_transactions': recent_transactions,
    }
    return render(request, 'finances/dashboard.html', context)

# ==========================================
# CREATE TRANSACTION
# ==========================================
@login_required
def add_transaction(request):
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            # commit=False means "wait, don't save to the vault just yet!"
            transaction = form.save(commit=False)
            # Stamp the transaction with the logged-in user
            transaction.user = request.user
            # Now save it permanently
            transaction.save()
            return redirect('dashboard')
    else:
        # If they just clicked the button, give them a blank form
        form = TransactionForm()
        
    return render(request, 'finances/transaction_form.html', {'form': form})
# ==========================================
# TRANSACTION LEDGER (WITH PAGINATION)
# ==========================================
@login_required
def transaction_list(request):
    # 1. Grab all transactions for this user
    all_transactions = Transaction.objects.filter(user=request.user).order_by('-date', '-id')
    
    # 2. Tell the Paginator to only allow 15 rows per page
    paginator = Paginator(all_transactions, 15)
    
    # 3. Look at the URL to see what page we are on (e.g., ?page=2)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # 4. Send the "page_obj" to the frontend instead of the full list
    return render(request, 'finances/transaction_list.html', {'page_obj': page_obj})
# ==========================================
# EDIT TRANSACTION
# ==========================================
@login_required
def update_transaction(request, pk):
    # SECURITY: This mathematically guarantees the logged-in user owns this row of data
    txn = get_object_or_404(Transaction, pk=pk, user=request.user)
    
    if request.method == 'POST':
        # "instance=txn" tells Django to OVERWRITE the existing data, not create new data
        form = TransactionForm(request.POST, instance=txn)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        # Pre-fill the form with the existing data
        form = TransactionForm(instance=txn)
        
    # We pass 'is_edit' so our HTML knows to change the title from "Add" to "Edit"
    return render(request, 'finances/transaction_form.html', {'form': form, 'is_edit': True})

# ==========================================
# DELETE TRANSACTION
# ==========================================
@login_required
def delete_transaction(request, pk):
    txn = get_object_or_404(Transaction, pk=pk, user=request.user)
    
    if request.method == 'POST':
        txn.delete()
        return redirect('dashboard')
        
    return render(request, 'finances/transaction_confirm_delete.html', {'transaction': txn})

# ==========================================
# BUDGETS
# ==========================================
@login_required
def budget_dashboard(request):
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    
    budgets = Budget.objects.filter(user=request.user)
    budget_data = []
    
    for budget in budgets:
        spent_agg = TransactionLineItem.objects.filter(
            transaction__user=request.user,
            transaction__date__gte=start_of_month,
            category=budget.category
        ).aggregate(Sum('amount'))
        
        spent = spent_agg['amount__sum'] or Decimal('0.00')
        remaining = budget.amount - spent
        
        if budget.amount > 0:
            percent = min(int((spent / budget.amount) * 100), 100)
        else:
            percent = 0
            
        if percent >= 90:
            status_color = '#e74c3c' 
        elif percent >= 75:
            status_color = '#f1c40f' 
        else:
            status_color = '#2ecc71' 

        budget_data.append({
            'category': budget.category,
            'limit': budget.amount,
            'spent': spent,
            'remaining': remaining,
            'percent': percent,
            'status_color': status_color,
            'over_budget': abs(remaining) if remaining < 0 else 0
        })
        
    return render(request, 'finances/budgets.html', {'budget_data': budget_data})

@login_required
def add_budget(request):
    if request.method == 'POST':
        form = BudgetForm(request.POST)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = request.user
            budget.save()
            return redirect('budgets')
    else:
        form = BudgetForm()

    return render(request, 'finances/budget_form.html', {'form': form})


# ==========================================
# DEBTS
# ==========================================
@login_required
def debt_dashboard(request):
    debts = Debt.objects.filter(user=request.user)
    debt_data = []
    today = timezone.now().date()

    for debt in debts:
        current_balance = debt.principal_balance
        total_interest_accrued = Decimal('0.00')
        total_paid = Decimal('0.00')
        last_date = debt.start_date
        
        daily_rate = (debt.interest_rate / Decimal('100')) / Decimal('365')

        payments = debt.payments.select_related('transaction').order_by('transaction__date')

        for payment in payments:
            days_passed = (payment.transaction.date - last_date).days
            
            if days_passed > 0:
                interest = current_balance * daily_rate * Decimal(days_passed)
                total_interest_accrued += interest
                current_balance += interest

            total_paid += payment.amount
            current_balance -= payment.amount
            last_date = payment.transaction.date

        days_since_last = (today - last_date).days
        if days_since_last > 0:
            interest = current_balance * daily_rate * Decimal(days_since_last)
            total_interest_accrued += interest
            current_balance += interest

        if current_balance < 0:
            current_balance = Decimal('0.00')

        total_owed_to_date = debt.principal_balance + total_interest_accrued
        if total_owed_to_date > 0:
            percent_paid = min(int((total_paid / total_owed_to_date) * 100), 100)
        else:
            percent_paid = 0

        debt_data.append({
            'name': debt.name,
            'vendor': debt.vendor,
            'principal_balance': debt.principal_balance,
            'interest_rate': debt.interest_rate,
            'monthly_payment': debt.monthly_payment,
            'due_date': debt.due_date,
            'total_paid': total_paid,
            'total_interest': total_interest_accrued,
            'current_balance': current_balance,
            'percent_paid': percent_paid,
        })

    return render(request, 'finances/debts.html', {'debt_data': debt_data})

@login_required
def add_debt(request):
    if request.method == 'POST':
        form = DebtForm(request.POST)
        if form.is_valid():
            debt = form.save(commit=False)
            debt.user = request.user
            debt.save()
            return redirect('debts')
    else:
        form = DebtForm()

    return render(request, 'finances/debt_form.html', {'form': form})


# ==========================================
# SAVINGS GOALS
# ==========================================
@login_required
def savings_dashboard(request):
    goals = SavingsGoal.objects.filter(user=request.user)
    savings_data = []
    today = timezone.now().date()

    for goal in goals:
        current_balance = Decimal('0.00')
        total_interest_earned = Decimal('0.00')
        total_contributed = Decimal('0.00')
        
        if goal.interest_rate:
            daily_rate = (goal.interest_rate / Decimal('100')) / Decimal('365')
        else:
            daily_rate = Decimal('0.00')

        contributions = goal.contributions.select_related('transaction').order_by('transaction__date')
        
        if contributions.exists():
            last_date = contributions.first().transaction.date

            for contrib in contributions:
                days_passed = (contrib.transaction.date - last_date).days
                
                if days_passed > 0 and current_balance > 0:
                    interest = current_balance * daily_rate * Decimal(days_passed)
                    total_interest_earned += interest
                    current_balance += interest
                
                total_contributed += contrib.amount
                current_balance += contrib.amount
                last_date = contrib.transaction.date

            days_since_last = (today - last_date).days
            if days_since_last > 0 and current_balance > 0:
                interest = current_balance * daily_rate * Decimal(days_since_last)
                total_interest_earned += interest
                current_balance += interest

        remaining = goal.target_amount - current_balance

        if goal.target_amount > 0:
            percent_saved = min(int((current_balance / goal.target_amount) * 100), 100)
        else:
            percent_saved = 0

        savings_data.append({
            'name': goal.name,
            'target_amount': goal.target_amount,
            'target_date': goal.target_date,
            'interest_rate': goal.interest_rate or 0,
            'total_contributed': total_contributed,
            'total_interest': total_interest_earned,
            'current_balance': current_balance,
            'remaining': remaining if remaining > 0 else Decimal('0.00'),
            'percent_saved': percent_saved,
        })

    return render(request, 'finances/savings.html', {'savings_data': savings_data})

@login_required
def add_savings_goal(request):
    if request.method == 'POST':
        form = SavingsGoalForm(request.POST)
        if form.is_valid():
            goal = form.save(commit=False)
            goal.user = request.user
            goal.save()
            return redirect('savings')
    else:
        form = SavingsGoalForm()

    return render(request, 'finances/savings_form.html', {'form': form})


# ==========================================
# EXPENSE ANALYTICS DEEP DIVE
# ==========================================
@login_required
def expense_analytics(request):
    all_expenses = Transaction.objects.filter(user=request.user, transaction_type='EXPENSE')

    stats = all_expenses.aggregate(
        total_spent=Sum('total_amount'),
        avg_transaction=Avg('total_amount'),
        total_swipes=Count('id')
    )

    top_vendors_by_amount = all_expenses.exclude(vendor='').values('vendor').annotate(
        total=Sum('total_amount')
    ).order_by('-total')[:5]

    top_vendors_by_frequency = all_expenses.exclude(vendor='').values('vendor').annotate(
        visits=Count('id')
    ).order_by('-visits')[:5]

    recent_expenses = all_expenses.order_by('-date')[:10]

    vendor_labels = []
    vendor_data = []
    for v in top_vendors_by_amount:
        vendor_labels.append(v['vendor'])
        vendor_data.append(float(v['total']))

    context = {
        'total_spent': stats['total_spent'] or Decimal('0.00'),
        'avg_transaction': stats['avg_transaction'] or Decimal('0.00'),
        'total_swipes': stats['total_swipes'] or 0,
        'top_vendors_freq': top_vendors_by_frequency,
        'recent_expenses': recent_expenses,
        'vendor_labels': json.dumps(vendor_labels),
        'vendor_data': json.dumps(vendor_data),
    }
    return render(request, 'finances/expenses.html', context)
# ==========================================
# INCOME ANALYTICS DEEP DIVE (WITH VIRTUAL INTEREST)
# ==========================================
@login_required
def income_analytics(request):
    today = timezone.now().date()
    
    # 1. Grab all physical Income transactions
    all_income = Transaction.objects.filter(user=request.user, transaction_type='INCOME')

    stats = all_income.aggregate(
        total_earned=Sum('total_amount'),
        avg_deposit=Avg('total_amount'),
        total_deposits=Count('id')
    )
    
    base_total_earned = stats['total_earned'] or Decimal('0.00')

    # ==========================================
    # 2. THE VIRTUAL INJECTION (Phantom Interest)
    # ==========================================
    total_phantom_interest = Decimal('0.00')
    goals = SavingsGoal.objects.filter(user=request.user)

    for goal in goals:
        current_balance = Decimal('0.00')
        if goal.interest_rate:
            daily_rate = (goal.interest_rate / Decimal('100')) / Decimal('365')
        else:
            daily_rate = Decimal('0.00')

        contributions = goal.contributions.select_related('transaction').order_by('transaction__date')
        
        if contributions.exists():
            last_date = contributions.first().transaction.date
            for contrib in contributions:
                days_passed = (contrib.transaction.date - last_date).days
                if days_passed > 0 and current_balance > 0:
                    interest = current_balance * daily_rate * Decimal(days_passed)
                    total_phantom_interest += interest
                    current_balance += interest
                
                current_balance += contrib.amount
                last_date = contrib.transaction.date

            days_since_last = (today - last_date).days
            if days_since_last > 0 and current_balance > 0:
                interest = current_balance * daily_rate * Decimal(days_since_last)
                total_phantom_interest += interest

    # Round it to 2 decimal places so it looks like money
    total_phantom_interest = round(total_phantom_interest, 2)

    # 3. Combine Physical Income + Virtual Interest
    grand_total_earned = base_total_earned + total_phantom_interest

    # ==========================================
    # 4. PREPARE THE CHARTS
    # ==========================================
    # Donut Chart: Physical Categories
    income_by_category = TransactionLineItem.objects.filter(
        transaction__user=request.user,
        transaction__transaction_type='INCOME'
    ).values('category').annotate(total=Sum('amount')).order_by('-total')

    category_labels = []
    category_data = []
    for item in income_by_category:
        category_labels.append(item['category'])
        category_data.append(float(item['total']))

    # Inject the Virtual Interest into the Donut Chart!
    if total_phantom_interest > 0:
        category_labels.append('Savings Yield (Virtual)')
        category_data.append(float(total_phantom_interest))

    # Line Chart: 6-Month Trend (Physical Cash Flow Only)
    six_months_ago = today - datetime.timedelta(days=180)
    monthly_trends = TransactionLineItem.objects.filter(
        transaction__user=request.user,
        transaction__transaction_type='INCOME',
        transaction__date__gte=six_months_ago
    ).annotate(
        month=TruncMonth('transaction__date')
    ).values('month').annotate(
        total=Sum('amount')
    ).order_by('month')

    trend_labels = []
    trend_data = []
    for item in monthly_trends:
        if item['month']:
            trend_labels.append(item['month'].strftime('%b %Y'))
            trend_data.append(float(item['total']))

    # Top Payers Leaderboard
    top_sources = list(all_income.exclude(vendor='').values('vendor').annotate(
        total=Sum('total_amount')
    ).order_by('-total')[:4]) # Grab top 4 physical

    # Inject your "Bank" into the leaderboard if interest is high enough!
    if total_phantom_interest > 0:
        top_sources.append({
            'vendor': 'Automated Bank Yield',
            'total': total_phantom_interest
        })
        # Re-sort it so the virtual bank slots into the correct place
        top_sources = sorted(top_sources, key=lambda k: k['total'], reverse=True)

    context = {
        # Pass the newly combined Grand Total to the screen
        'total_earned': grand_total_earned,
        'avg_deposit': stats['avg_deposit'] or Decimal('0.00'),
        'total_deposits': stats['total_deposits'] or 0,
        'top_sources': top_sources,
        
        'category_labels': json.dumps(category_labels),
        'category_data': json.dumps(category_data),
        'trend_labels': json.dumps(trend_labels),
        'trend_data': json.dumps(trend_data),
    }
    return render(request, 'finances/income.html', context)
# ==========================================
# USER AUTHENTICATION
# ==========================================
def register(request):
    if request.method == 'POST':
        form = ExtendedRegistrationForm(request.POST)
        if form.is_valid():
            # 1. Save the core Django User (Username, Password, Email)
            user = form.save()
            
            # 2. Extract our custom data
            pref_name = form.cleaned_data.get('preferred_name')
            phone = form.cleaned_data.get('phone_number')
            
            # 3. Create the linked Profile with the extra data
            UserProfile.objects.create(
                user=user,
                preferred_name=pref_name,
                phone_number=phone
            )
            
            # 4. Log them in and send them to the dashboard
            login(request, user)
            return redirect('dashboard')
    else:
        form = ExtendedRegistrationForm()
        
    return render(request, 'registration/register.html', {'form': form})
# ==========================================
# DATA EXPORT (CSV)
# ==========================================
@login_required
def export_transactions_csv(request):
    # 1. Create the response object and tell the browser it's a CSV file downloading
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tilly_budget_ledger.csv"'

    # 2. Set up the CSV writer
    writer = csv.writer(response)
    
    # 3. Write the Header Row
    writer.writerow(['Date', 'Vendor', 'Transaction Type', 'Total Amount'])

    # 4. Fetch the user's data and write each row
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    for txn in transactions:
        writer.writerow([txn.date, txn.vendor, txn.transaction_type, txn.total_amount])

    return response