from django import forms
from django.forms import inlineformset_factory
from .models import Transaction, TransactionLineItem, Budget, Debt, SavingsGoal
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

# ALL MODELS IMPORTED HERE
from .models import Transaction, TransactionLineItem, Budget, Debt

class TransactionForm(forms.ModelForm):
    class Meta:
        model = Transaction
        fields = ['date', 'vendor', 'total_amount', 'transaction_type', 'notes']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 3}),
        }

# This links the parent (Transaction) to the child (TransactionLineItem)
TransactionLineItemFormSet = inlineformset_factory(
    Transaction, 
    TransactionLineItem, 
    fields=['category', 'amount', 'linked_debt', 'linked_savings'],
    extra=3, 
    can_delete=True 
)

class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        # Updated to match your new advanced Budget model
        fields = ['budget_type', 'category', 'amount', 'start_date', 'end_date', 'vendor']
        widgets = {
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
        }

class DebtForm(forms.ModelForm):
    class Meta:
        model = Debt
        # Updated to match your new advanced Debt model
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
    # We explicitly add the fields we want to collect on the screen
    email = forms.EmailField(required=True)
    preferred_name = forms.CharField(max_length=50, required=True, help_text="What should we call you?")
    phone_number = forms.CharField(max_length=20, required=True, help_text="For account security.")

    class Meta(UserCreationForm.Meta):
        model = User
        # We tell Django to use its normal fields (Username/Password), plus our Email
        fields = UserCreationForm.Meta.fields + ('email',)