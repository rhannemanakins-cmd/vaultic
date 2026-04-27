from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date
from django.core.validators import MinValueValidator, MaxValueValidator

# ==========================================
# 1. USER PROFILES
# ==========================================
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferred_name = models.CharField(max_length=50)
    phone_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.preferred_name}'s Profile"

# ==========================================
# 2. SAVINGS GOALS
# ==========================================
class SavingsGoal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='savings_goals')
    name = models.CharField(max_length=100)
    target_amount = models.DecimalField(max_digits=10, decimal_places=2)
    current_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, help_text="Annual Interest Rate (%)")
    target_date = models.DateField(null=True, blank=True)
    monthly_contribution_requirement = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    @property
    def percent_reached(self):
        if self.target_amount > 0:
            return round((self.current_balance / self.target_amount) * 100, 2)
        return 0

    def __str__(self):
        return f"{self.name} - {self.percent_reached}%"

# ==========================================
# 3. DEBTS (LOANS)
# ==========================================
class Debt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='debts')
    name = models.CharField(max_length=100)
    vendor = models.CharField(max_length=100)
    principal_balance = models.DecimalField(max_digits=12, decimal_places=2)
    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, help_text="Annual Interest Rate (%)")
    monthly_payment = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(31)], 
        help_text="Day of the month the payment is due (1-31)"
    )
    start_date = models.DateField()
    expected_maturity_date = models.DateField()

    def __str__(self):
        return f"{self.name} ({self.vendor}) - ${self.principal_balance}"

# ==========================================
# 4. BUDGET CATEGORIES
# ==========================================
class Budget(models.Model):
    BUDGET_TYPES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='budgets')
    budget_type = models.CharField(max_length=10, choices=BUDGET_TYPES)
    category = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    start_date = models.DateField()
    end_date = models.DateField()
    vendor = models.CharField(max_length=100, null=True, blank=True)

    def __str__(self):
        return f"{self.category} Budget: ${self.amount}"

# ==========================================
# 5. THE MASTER TRANSACTION MODEL
# ==========================================
class Transaction(models.Model):
    TRANSACTION_TYPES = [
        ('INCOME', 'Income'),
        ('EXPENSE', 'Expense'),
        ('TRANSFER', 'Transfer'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    date = models.DateField(default=date.today) 
    vendor = models.CharField(max_length=100)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    notes = models.TextField(null=True, blank=True)
    
    # RELATIONAL LINKS
    linked_budget = models.ForeignKey(Budget, on_delete=models.SET_NULL, null=True, blank=True, related_name='budget_transactions')
    linked_debt = models.ForeignKey(Debt, on_delete=models.SET_NULL, null=True, blank=True, related_name='transaction_payments')
    linked_savings = models.ForeignKey(SavingsGoal, on_delete=models.SET_NULL, null=True, blank=True, related_name='transaction_contributions')

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # AUTOMATION: Update balances on save
        if is_new:
            if self.linked_debt:
                self.linked_debt.principal_balance -= self.total_amount
                self.linked_debt.save()
            if self.linked_savings:
                self.linked_savings.current_balance += self.total_amount
                self.linked_savings.save()

    def __str__(self):
        return f"{self.date} - {self.vendor} (${self.total_amount})"

# ==========================================
# 6. TRANSACTION LINE ITEMS (Optional Splits)
# ==========================================
class TransactionLineItem(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE, related_name='line_items')
    
    # REPLACED CharField WITH A RELATIONAL FOREIGN KEY
    linked_budget = models.ForeignKey(Budget, on_delete=models.SET_NULL, null=True, blank=True, related_name='split_transactions')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        budget_name = self.linked_budget.category if self.linked_budget else "Uncategorized"
        return f"{budget_name} - ${self.amount}"