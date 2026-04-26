import json
import csv
import datetime
import calendar
from decimal import Decimal
from .models import UserProfile, SavingsGoal, Debt, Budget, Transaction, TransactionLineItem
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.utils import timezone
from django.urls import reverse_lazy
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncMonth
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from .models import Transaction, TransactionLineItem, Budget, Debt, SavingsGoal, UserProfile
from .forms import TransactionForm, BudgetForm, DebtForm, SavingsGoalForm, ExtendedRegistrationForm

# ==========================================
# MAIN DASHBOARD
# ==========================================
@login_required
def dashboard(request):
    # 1. Capture requested month/year from URL, default to NOW
    now = timezone.now().date()
    month = int(request.GET.get('month', now.month))
    year = int(request.GET.get('year', now.year))

    # 2. Calculate the Fluid Date Range
    start_date = datetime.date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = datetime.date(year, month, last_day)

    # 3. Handle Navigation Logic (Previous/Next Month)
    prev_month = start_date - datetime.timedelta(days=1)
    next_month = end_date + datetime.timedelta(days=1)

    # 4. Filter Transactions ACCURATELY to this period
    monthly_income = Transaction.objects.filter(
        user=request.user, 
        transaction_type='INCOME', 
        date__range=[start_date, end_date] # Accuracy fix
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    monthly_expenses = Transaction.objects.filter(
        user=request.user, 
        transaction_type='EXPENSE', 
        date__range=[start_date, end_date]
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    # Total Balance remains "All Time" for accounting accuracy
    all_income = Transaction.objects.filter(user=request.user, transaction_type='INCOME').aggregate(total=Sum('total_amount'))['total'] or 0
    all_expenses = Transaction.objects.filter(user=request.user, transaction_type='EXPENSE').aggregate(total=Sum('total_amount'))['total'] or 0
    total_balance = all_income - all_expenses

    recent_transactions = Transaction.objects.filter(user=request.user).order_by('-date', '-id')[:5]

    context = {
        'total_balance': total_balance,
        'monthly_income': monthly_income,
        'monthly_expenses': monthly_expenses,
        'recent_transactions': recent_transactions,
        'start_date': start_date,
        'end_date': end_date,
        'prev_month': prev_month,
        'next_month': next_month,
    }
    return render(request, 'finances/dashboard.html', context)

@login_required
def budget_dashboard(request):
    # Same Fluid Logic for Budgets
    now = timezone.now().date()
    month = int(request.GET.get('month', now.month))
    year = int(request.GET.get('year', now.year))
    start_date = datetime.date(year, month, 1)
    last_day = calendar.monthrange(year, month)[1]
    end_date = datetime.date(year, month, last_day)

    prev_month = start_date - datetime.timedelta(days=1)
    next_month = end_date + datetime.timedelta(days=1)

    budgets = Budget.objects.filter(user=request.user)
    budget_data = []
    
    for budget in budgets:
        # We only count transactions that fall within the SELECTED month
        spent_agg = Transaction.objects.filter(
            user=request.user,
            date__range=[start_date, end_date],
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
            'status_color': '#ef4444' if percent >= 90 else '#f59e0b' if percent >= 75 else '#10b981',
            'start_date': budget.start_date,
            'end_date': budget.end_date,
        })
        
    return render(request, 'finances/budgets.html', {
        'budget_data': budget_data,
        'current_period': start_date,
        'prev_month': prev_month,
        'next_month': next_month,
    })

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
        kwargs['user'] = self.request.user 
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
# BUDGET DASHBOARD
# ==========================================
@login_required
def budget_dashboard(request):
    today = timezone.now().date()
    start_of_month = today.replace(day=1)
    budgets = Budget.objects.filter(user=request.user)
    budget_data = []
    
    for budget in budgets:
        spent_agg = Transaction.objects.filter(
            user=request.user,
            date__gte=start_of_month,
            linked_budget=budget,
            transaction_type='EXPENSE'
        ).aggregate(total=Sum('total_amount'))
        
        spent = spent_agg['total'] or Decimal('0.00')
        remaining = budget.amount - spent
        percent = min(int((float(spent) / float(budget.amount)) * 100), 100) if budget.amount > 0 else 0
            
        if percent >= 90: status_color = '#ef4444' 
        elif percent >= 75: status_color = '#f59e0b' 
        else: status_color = '#10b981' 

        budget_data.append({
            'id': budget.id,
            'category': budget.category,
            'limit': budget.amount,
            'spent': spent,
            'remaining': remaining,
            'percent': percent,
            'status_color': status_color,
            'start_date': budget.start_date,
            'end_date': budget.end_date,
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

class BudgetUpdateView(UpdateView):
    model = Budget
    fields = ['budget_type', 'category', 'amount', 'start_date', 'end_date', 'vendor']
    template_name = 'finances/budget_form.html'
    success_url = reverse_lazy('budgets')

class BudgetDeleteView(DeleteView):
    model = Budget
    template_name = 'finances/budget_confirm_delete.html'
    success_url = reverse_lazy('budgets')

# ==========================================
# DEBTS & SAVINGS
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
        if current_balance < 0: current_balance = Decimal('0.00')
        total_owed_to_date = debt.principal_balance + total_interest_accrued
        percent_paid = min(int((total_paid / total_owed_to_date) * 100), 100) if total_owed_to_date > 0 else 0
        debt_data.append({
            'id': debt.id, 'name': debt.name, 'vendor': debt.vendor,
            'principal_balance': debt.principal_balance, 'interest_rate': debt.interest_rate,
            'total_paid': total_paid, 'total_interest': total_interest_accrued,
            'current_balance': current_balance, 'percent_paid': percent_paid,
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
            'id': goal.id, 'name': goal.name, 'target_amount': goal.target_amount,
            'total_contributed': total_contributed, 'total_interest': total_interest_earned,
            'current_balance': current_balance, 'remaining': remaining if remaining > 0 else 0,
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
# ANALYTICS (INCOME & EXPENSE)
# ==========================================
@login_required
def income_analytics(request):
    today = timezone.now().date()
    all_income = Transaction.objects.filter(user=request.user, transaction_type='INCOME')
    stats = all_income.aggregate(total_earned=Sum('total_amount'), avg_deposit=Avg('total_amount'), total_deposits=Count('id'))
    base_total_earned = stats['total_earned'] or Decimal('0.00')

    # Virtual Interest Calculation
    total_phantom_interest = Decimal('0.00')
    goals = SavingsGoal.objects.filter(user=request.user)
    for goal in goals:
        current_balance = Decimal('0.00')
        daily_rate = (goal.interest_rate / Decimal('100')) / Decimal('365') if goal.interest_rate else Decimal('0.00')
        contributions = goal.transaction_contributions.order_by('date')
        if contributions.exists():
            last_date = contributions.first().date
            for contrib in contributions:
                days_passed = (contrib.date - last_date).days
                if days_passed > 0 and current_balance > 0:
                    total_phantom_interest += current_balance * daily_rate * Decimal(days_passed)
                    current_balance += current_balance * daily_rate * Decimal(days_passed)
                current_balance += contrib.total_amount
                last_date = contrib.date
            days_since_last = (today - last_date).days
            if days_since_last > 0 and current_balance > 0:
                total_phantom_interest += current_balance * daily_rate * Decimal(days_since_last)

    grand_total_earned = base_total_earned + round(total_phantom_interest, 2)

    # Charts
    income_by_category = Transaction.objects.filter(user=request.user, transaction_type='INCOME').values('linked_budget__category').annotate(total=Sum('total_amount')).order_by('-total')
    category_labels = [item['linked_budget__category'] or "Uncategorized" for item in income_by_category]
    category_data = [float(item['total']) for item in income_by_category]
    if total_phantom_interest > 0:
        category_labels.append('Savings Yield (Virtual)')
        category_data.append(float(total_phantom_interest))

    context = {
        'total_earned': grand_total_earned,
        'avg_deposit': stats['avg_deposit'] or 0,
        'total_deposits': stats['total_deposits'] or 0,
        'category_labels': json.dumps(category_labels),
        'category_data': json.dumps(category_data),
    }
    return render(request, 'finances/income.html', context)

@login_required
def expense_analytics(request):
    all_expenses = Transaction.objects.filter(user=request.user, transaction_type='EXPENSE')
    stats = all_expenses.aggregate(total_spent=Sum('total_amount'), avg_transaction=Avg('total_amount'), total_swipes=Count('id'))
    top_vendors = all_expenses.exclude(vendor='').values('vendor').annotate(total=Sum('total_amount')).order_by('-total')[:5]
    
    vendor_labels = [v['vendor'] for v in top_vendors]
    vendor_data = [float(v['total']) for v in top_vendors]

    context = {
        'total_spent': stats['total_spent'] or 0,
        'avg_transaction': stats['avg_transaction'] or 0,
        'total_swipes': stats['total_swipes'] or 0,
        'vendor_labels': json.dumps(vendor_labels),
        'vendor_data': json.dumps(vendor_data),
        'recent_expenses': all_expenses.order_by('-date')[:10],
    }
    return render(request, 'finances/expenses.html', context)

# ==========================================
# AUTH & EXPORT
# ==========================================
def register(request):
    if request.method == 'POST':
        form = ExtendedRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(user=user, preferred_name=form.cleaned_data.get('preferred_name'))
            login(request, user)
            return redirect('dashboard')
    else: form = ExtendedRegistrationForm()
    return render(request, 'registration/register.html', {'form': form})

@login_required
def export_transactions_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="ledger.csv"'
    writer = csv.writer(response)
    writer.writerow(['Date', 'Vendor', 'Type', 'Amount'])
    for txn in Transaction.objects.filter(user=request.user).order_by('-date'):
        writer.writerow([txn.date, txn.vendor, txn.transaction_type, txn.total_amount])
    return response

# --- Add these imports at the very top of your views.py file ---
import json
from django.http import JsonResponse
from django.conf import settings
from google import genai
from google.genai import types

# ==========================================
# AI ADVISOR ENDPOINT
# ==========================================
@login_required
def ai_advisor_chat(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '')
            chat_history = data.get('history', [])

            # 1. Build the memory transcript (Last 6 messages)
            transcript = "\n--- RECENT CONVERSATION HISTORY ---\n"
            for msg in chat_history[-6:]:
                role = "User" if msg.get('isUser') else "TillyBot"
                transcript += f"{role}: {msg.get('text')}\n"
            transcript += "-----------------------------------\n"

            # 2. Gather the User's FULL Live Context Based on Actual Models
            
            # --- Profile ---
            profile = UserProfile.objects.filter(user=request.user).first()
            user_name = profile.preferred_name if profile else "the user"
            profile_context = f"The user's preferred name is {user_name}.\n"

            # --- A. SAVINGS GOALS ---
            savings = SavingsGoal.objects.filter(user=request.user)
            savings_context = "\nSavings Goals:\n"
            for s in savings:
                savings_context += f"- {s.name}: ${s.current_balance} saved out of a ${s.target_amount} target.\n"

            # --- B. INCOME & EXPENSE BUDGETS ---
            budgets = Budget.objects.filter(user=request.user)
            income_context = "\nExpected Income:\n"
            expense_context = "\nExpense Budgets:\n"
            for b in budgets:
                if b.budget_type == 'INCOME':
                    income_context += f"- {b.category}: ${b.amount} expected.\n"
                else:
                    expense_context += f"- {b.category}: ${b.amount} limit.\n"

            # --- C. DEBTS ---
            debts = Debt.objects.filter(user=request.user)
            debt_context = "\nCurrent Debts/Liabilities:\n"
            for d in debts:
                debt_context += f"- {d.name} ({d.vendor}): ${d.principal_balance} balance at {d.interest_rate}% interest. Monthly payment is ${d.monthly_payment}, due on day {d.due_date} of the month.\n"

            # --- D. RECENT TRANSACTIONS ---
            transactions = Transaction.objects.filter(user=request.user).order_by('-date')[:10]
            transaction_context = "\nLast 10 Transactions:\n"
            for t in transactions:
                transaction_context += f"- {t.date}: {t.transaction_type} of ${t.total_amount} at {t.vendor}.\n"

            # 3. Build the Master System Instruction
            system_prompt = f"""
            You are TillyBot, a professional and helpful financial advisor for the Tilly Budget app.
            You have access to the user's complete financial profile. Do not give generic advice. Use the exact data provided below to answer their questions.
            If they ask a 'what-if' math question, calculate the impact based on their actual income, savings, debts, and budgets. Address the user by their preferred name occasionally.
            
            --- USER FINANCIAL DATA ---
            {profile_context}
            {savings_context}
            {income_context}
            {expense_context}
            {debt_context}
            {transaction_context}
            ---------------------------
            
            {transcript}
            
            Keep your answers concise, formatting with short paragraphs or bullet points. Do not use complex markdown that a standard chat window can't render.
            """

            # 4. Call the Gemini API
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.2, 
                )
            )

            # 5. Send the answer back to the chat window
            return JsonResponse({'status': 'success', 'response': response.text})

        except Exception as e:
            print(f"AI Error: {e}") 
            return JsonResponse({'status': 'error', 'message': 'The AI is currently taking a coffee break. Try again in a minute!'}, status=500)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)