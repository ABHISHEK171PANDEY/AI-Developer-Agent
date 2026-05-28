import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from calculator import add, subtract, multiply, divide, calculate_average


def test_add():
    assert add(2, 3) == 5
    assert add(-1, 1) == 0
    assert add(0, 0) == 0


def test_subtract():
    assert subtract(10, 4) == 6
    assert subtract(0, 5) == -5


def test_multiply():
    assert multiply(3, 4) == 12
    assert multiply(0, 100) == 0


def test_divide():
    assert divide(10, 2) == 5.0
    assert divide(7, 2) == 3.5
    # This will raise ZeroDivisionError due to the bug in calculator.py
    with pytest.raises(ZeroDivisionError):
        divide(5, 0)


def test_calculate_average():
    # This test will FAIL because of the off-by-one bug
    assert calculate_average([10, 20, 30]) == 20.0
    assert calculate_average([5, 5, 5, 5]) == 5.0
