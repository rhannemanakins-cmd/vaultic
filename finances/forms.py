from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import Transaction, TransactionLineItem, Budget, Debt, SavingsGoal

# ==========================================
# TRANSACTION FORMS
# ==========================================
class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        # These stay here! This is where your dropdowns live now.
        fields = ['date', 'vendor', 'total_amount', 'transaction_type', 'linked_debt', 'linked_savings', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['linked_debt'].queryset = Debt.objects.filter(user=user)
            self.fields['linked_savings'].queryset = SavingsGoal.objects.filter(user=user)

class TransactionLineItemForm(forms.ModelForm):
    class Meta:
        model = TransactionLineItem
        # REMOVED linked_debt and linked_savings from here to fix the crash
        fields = ['category', 'amount']

# This links Transaction to Line Items
TransactionLineItemFormSet = inlineformset_factory(
    Transaction, 
    TransactionLineItem, 
    fields=['category', 'amount'], # Fixed: No more "Unknown Field" error
    extra=1, 
    can_delete=True 
)

# ==========================================
# BUDGET, DEBT, & SAVINGS FORMS
# ==========================================
class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ['budget_type', 'category', 'amount', 'start_date', 'end_date', 'vendor']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

class DebtForm(forms.ModelForm):
    class Meta:
        model = Debt
        fields = ['name', 'vendor', 'principal_balance', 'interest_rate', 'monthly_payment', 'due_date', 'start_date', 'expected_maturity_date']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'expected_maturity_date': forms.DateInput(attrs={'type': 'date'}),
        }

class SavingsGoalForm(forms.ModelForm):
    class Meta:
        model = SavingsGoal
        fields = ['name', 'target_amount', 'target_date', 'interest_rate']
        widgets = {
            'target_date': forms.DateInput(attrs={'type': 'date'}),
        }

# ==========================================
# CUSTOM REGISTRATION FORM
# ==========================================
class ExtendedRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    preferred_name = forms.CharField(max_length=50, required=True, help_text="What should we call you?")
    phone_number = forms.CharField(max_length=20, required=True, help_text="For account security.")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)