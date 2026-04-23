import json
import csv
import datetime
from decimal import Decimal

# Django Core & DB Imports
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.urls import reverse_lazy

# Database Aggregation
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncMonth

# Class-Based Views
from django.views.generic.edit import CreateView, UpdateView, DeleteView

# Local Models & Forms
from .models import Transaction, TransactionLineItem, Budget, Debt, SavingsGoal, UserProfile
from .forms import TransactionForm, BudgetForm, DebtForm, SavingsGoalForm, ExtendedRegistrationForm

# ==========================================
# MAIN DASHBOARD ENGINE
# ==========================================
@login_required
def dashboard(request):
    today = timezone.now().date()
    # First day of current month
    start_date = today.replace(day=1)
    
    # Last day of current month
    import calendar
    last_day = calendar.monthrange(today.year, today.month)[1]
    end_date = today.replace(day=last_day)

    # ... (Keep your income/expense calculation logic here) ...

    context = {
        'total_balance': total_balance,
        'monthly_income': monthly_income,
        'monthly_expenses': monthly_expenses,
        'recent_transactions': recent_transactions,
        'start_date': start_date, # MUST HAVE THIS
        'end_date': end_date,     # MUST HAVE THIS
    }
    return render(request, 'finances/dashboard.html', context)

# ==========================================
# TRANSACTION MANAGEMENT
# ==========================================
class TransactionCreateView(CreateView):
    model = Transaction
    form_class = TransactionForm
    template_name = 'finances/transaction_form.html'
    success_url = reverse_lazy('transaction_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user # Passes the user to the form so dropdowns only show YOUR loans
        return kwargs

    def form_valid(self, form):
        form.instance.user = self.request.user
        return super().form_valid(form)

@login_required
def transaction_list(request):
    all_transactions = Transaction.objects.filter(user=request.user).order_by('-date', '-id')
    paginator = Paginator(all_transactions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'finances/transaction_list.html', {'page_obj': page_obj})

@login_required
def update_transaction(request, pk):
    txn = get_object_or_404(Transaction, pk=pk, user=request.user)
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=txn, user=request.user)
        if form.is_valid():
            form.save()
            return redirect('dashboard')
    else:
        form = TransactionForm(instance=txn, user=request.user)
    return render(request, 'finances/transaction_form.html', {'form': form, 'is_edit': True})

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

        # Updated to use the new relation name: transaction_payments
        payments = debt.transaction_payments.order_by('date')

        for payment in payments:
            days_passed = (payment.date - last_date).days
            if days_passed > 0:
                interest = current_balance * daily_rate * Decimal(days_passed)
                total_interest_accrued += interest
                current_balance += interest

            total_paid += payment.total_amount
            current_balance -= payment.total_amount
            last_date = payment.date

        days_since_last = (today - last_date).days
        if days_since_last > 0:
            interest = current_balance * daily_rate * Decimal(days_since_last)
            total_interest_accrued += interest
            current_balance += interest

        if current_balance < 0:
            current_balance = Decimal('0.00')

        total_owed_to_date = debt.principal_balance + total_interest_accrued
        percent_paid = min(int((total_paid / total_owed_to_date) * 100), 100) if total_owed_to_date > 0 else 0

        debt_data.append({
            'id': debt.id,
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

class DebtUpdateView(UpdateView):
    model = Debt
    fields = ['name', 'vendor', 'principal_balance', 'interest_rate', 'monthly_payment', 'due_date', 'expected_maturity_date']
    template_name = 'finances/debt_form.html'
    success_url = reverse_lazy('debts')

class DebtDeleteView(DeleteView):
    model = Debt
    template_name = 'finances/debt_confirm_delete.html'
    success_url = reverse_lazy('debts')

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
        daily_rate = (goal.interest_rate / Decimal('100')) / Decimal('365') if goal.interest_rate else Decimal('0.00')

        # Updated to use the new relation name: transaction_contributions
        contributions = goal.transaction_contributions.order_by('date')
        
        if contributions.exists():
            last_date = contributions.first().date
            for contrib in contributions:
                days_passed = (contrib.date - last_date).days
                if days_passed > 0 and current_balance > 0:
                    interest = current_balance * daily_rate * Decimal(days_passed)
                    total_interest_earned += interest
                    current_balance += interest
                
                total_contributed += contrib.total_amount
                current_balance += contrib.total_amount
                last_date = contrib.date

            days_since_last = (today - last_date).days
            if days_since_last > 0 and current_balance > 0:
                interest = current_balance * daily_rate * Decimal(days_since_last)
                total_interest_earned += interest
                current_balance += interest

        remaining = goal.target_amount - current_balance
        percent_saved = min(int((current_balance / goal.target_amount) * 100), 100) if goal.target_amount > 0 else 0

        savings_data.append({
            'id': goal.id,
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

class SavingsUpdateView(UpdateView):
    model = SavingsGoal
    fields = ['name', 'target_amount', 'current_balance', 'interest_rate', 'target_date', 'monthly_contribution_requirement']
    template_name = 'finances/savings_form.html'
    success_url = reverse_lazy('savings')

class SavingsDeleteView(DeleteView):
    model = SavingsGoal
    template_name = 'finances/savings_confirm_delete.html'
    success_url = reverse_lazy('savings')

# ==========================================
# ANALYTICS (EXPENSE & INCOME)
# ==========================================
@login_required
def expense_analytics(request):
    all_expenses = Transaction.objects.filter(user=request.user, transaction_type='EXPENSE')
    stats = all_expenses.aggregate(
        total_spent=Sum('total_amount'),
        avg_transaction=Avg('total_amount'),
        total_swipes=Count('id')
    )
    top_vendors_by_amount = all_expenses.exclude(vendor='').values('vendor').annotate(total=Sum('total_amount')).order_by('-total')[:5]
    top_vendors_by_frequency = all_expenses.exclude(vendor='').values('vendor').annotate(visits=Count('id')).order_by('-visits')[:5]
    recent_expenses = all_expenses.order_by('-date')[:10]

    vendor_labels = [v['vendor'] for v in top_vendors_by_amount]
    vendor_data = [float(v['total']) for v in top_vendors_by_amount]

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

@login_required
def income_analytics(request):
    # Truncated for space, assume unchanged from your original working code
    pass # Kept your original logic here in practice, just stripped to save prompt length if it hasn't changed.
    # (If you need me to re-paste the full 100-line virtual interest block, let me know, but it is safe!)

# ==========================================
# USER AUTHENTICATION & EXPORTS
# ==========================================
def register(request):
    if request.method == 'POST':
        form = ExtendedRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(
                user=user,
                preferred_name=form.cleaned_data.get('preferred_name'),
                phone_number=form.cleaned_data.get('phone_number')
            )
            login(request, user)
            return redirect('dashboard')
    else:
        form = ExtendedRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def export_transactions_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="tilly_budget_ledger.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Vendor', 'Transaction Type', 'Total Amount'])
    transactions = Transaction.objects.filter(user=request.user).order_by('-date')
    for txn in transactions:
        writer.writerow([txn.date, txn.vendor, txn.transaction_type, txn.total_amount])
    return response
@login_required
@login_required
def budget_dashboard(request):
    # 1. Setup timeframe
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    
    # 2. Get all budgets for this user
    budgets = Budget.objects.filter(user=request.user)
    budget_data = []
    
    for budget in budgets:
        # 3. Calculate "Spent" using the NEW relational link
        # We look for Transactions linked specifically to this Budget ID
        spent_agg = Transaction.objects.filter(
            user=request.user,
            date__gte=start_of_month,
            linked_budget=budget,
            transaction_type='EXPENSE' # Only count expenses toward budget limits
        ).aggregate(total=Sum('total_amount'))
        
        spent = spent_agg['total'] or Decimal('0.00')
        remaining = budget.amount - spent
        
        # 4. Calculate progress percentage
        if budget.amount > 0:
            # We use float() here to ensure the math doesn't crash if Types mismatch
            percent = min(int((float(spent) / float(budget.amount)) * 100), 100)
        else:
            percent = 0
            
        # 5. Determine UI Status Color (OG Vaultic Logic)
        if percent >= 90:
            status_color = '#ef4444' # Danger Red
        elif percent >= 75:
            status_color = '#f59e0b' # Warning Orange
        else:
            status_color = '#10b981' # Success Green

        # 6. Build the data package for the HTML
        budget_data.append({
            'id': budget.id,
            'category': budget.category,
            'limit': budget.amount,
            'spent': spent,
            'remaining': remaining,
            'percent': percent,
            'status_color': status_color,
            'over_budget': abs(remaining) if remaining < 0 else 0
        })
        
    return render(request, 'finances/budgets.html', {'budget_data': budget_data})
# --- Add these to your budget_dashboard and dashboard logic ---

@login_required
def budget_dashboard(request):
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    
    budgets = Budget.objects.filter(user=request.user)
    budget_data = []
    
    for budget in budgets:
        # Spending calculation based on the transaction's link to this specific budget
        spent_agg = Transaction.objects.filter(
            user=request.user,
            date__gte=start_of_month,
            linked_budget=budget,
            transaction_type='EXPENSE'
        ).aggregate(total=Sum('total_amount'))
        
        spent = spent_agg['total'] or Decimal('0.00')
        remaining = budget.amount - spent
        percent = min(int((float(spent) / float(budget.amount)) * 100), 100) if budget.amount > 0 else 0
            
        budget_data.append({
            'id': budget.id,
            'category': budget.category,
            'limit': budget.amount,
            'spent': spent,
            'remaining': remaining,
            'percent': percent,
            'start_date': budget.start_date, # From the model
            'end_date': budget.end_date,     # From the model
        })
        
    return render(request, 'finances/budgets.html', {'budget_data': budget_data})

# NEW: Budget CRUD Views
class BudgetUpdateView(UpdateView):
    model = Budget
    fields = ['budget_type', 'category', 'amount', 'start_date', 'end_date', 'vendor']
    template_name = 'finances/budget_form.html'
    success_url = reverse_lazy('budgets')

class BudgetDeleteView(DeleteView):
    model = Budget
    template_name = 'finances/budget_confirm_delete.html'
    success_url = reverse_lazy('budgets')