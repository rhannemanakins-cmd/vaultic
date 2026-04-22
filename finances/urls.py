from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/add/', views.add_transaction, name='add_transaction'),
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
]
