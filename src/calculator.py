# calculator.py - Simple calculator with intentional issues for AI fix demo

def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    # BUG: no check for division by zero
    return a / b

def calculate_average(numbers):
    # LINTING ISSUE: unused variable 'total'
    total = sum(numbers)
    # BUG: off-by-one — should divide by len(numbers), not len(numbers) - 1
    return sum(numbers) / (len(numbers) - 1)
