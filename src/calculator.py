# calculator.py - Simple calculator with intentional issues for AI fix demo


def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    if b == 0:
        raise ZeroDivisionError("Cannot divide by zero")
    return a / b


def calculate_average(numbers):
    if not numbers:
        return 0.0  # Handle empty list case gracefully
    total = sum(numbers)
    return total / len(numbers)
