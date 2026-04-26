from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transaction/add/', views.TransactionCreateView.as_view(), name='add_transaction'),
    path('transaction/<int:pk>/edit/', views.update_transaction, name='update_transaction'),
    path('transaction/<int:pk>/delete/', views.delete_transaction, name='delete_transaction'),
    path('budgets/', views.budget_dashboard, name='budgets'),
    path('budgets/add/', views.add_budget, name='add_budget'),
    path('debts/', views.debt_dashboard, name='debts'),
    path('debts/add/', views.add_debt, name='add_debt'),
    path('savings/', views.savings_dashboard, name='savings'),
    path('savings/add/', views.add_savings_goal, name='add_savings_goal'),
    path('expenses/', views.expense_analytics, name='expenses'),
    path('income/', views.income_analytics, name='income'),
    path('transaction/<int:pk>/edit/', views.update_transaction, name='update_transaction'),
    path('transaction/<int:pk>/delete/', views.delete_transaction, name='delete_transaction'),
    path('export/csv/', views.export_transactions_csv, name='export_transactions_csv'),
    # Budget Management
    path('budgets/<int:pk>/edit/', views.BudgetUpdateView.as_view(), name='edit_budget'),
    path('budgets/<int:pk>/delete/', views.BudgetDeleteView.as_view(), name='delete_budget'),
    # Debt Edit/Delete
    path('debts/<int:pk>/edit/', views.DebtUpdateView.as_view(), name='edit_debt'),
    path('debts/<int:pk>/delete/', views.DebtDeleteView.as_view(), name='delete_debt'),
    
    # Savings Edit/Delete
    path('savings/<int:pk>/edit/', views.SavingsUpdateView.as_view(), name='edit_saving'),
    path('savings/<int:pk>/delete/', views.SavingsDeleteView.as_view(), name='delete_saving'),

    # AI Chat API
path('api/chat/', views.ai_advisor_chat, name='ai_chat'),
]
