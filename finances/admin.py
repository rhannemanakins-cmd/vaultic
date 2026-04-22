from django.contrib import admin
from .models import UserProfile, Transaction, TransactionLineItem, Budget, Debt, SavingsGoal

# Registering all our models exactly once!
admin.site.register(UserProfile)
admin.site.register(Transaction)
admin.site.register(TransactionLineItem)
admin.site.register(Budget)
admin.site.register(Debt)
admin.site.register(SavingsGoal)