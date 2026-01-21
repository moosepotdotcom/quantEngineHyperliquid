#!/usr/bin/env python3
"""Quick demo of the enhanced CLI menu"""

print("\n" + "="*70)
print("🚀 MANDALORIAN PHASE 3 - CONFIGURATION SELECTOR (ENHANCED)")
print("="*70)

print("\n📅 Select Backtest Period:\n")

print("  Individual Months (2025):")
months_2025 = [
    ("1", "January 2025", "Start of 2025"),
    ("2", "February 2025", "Q1 2025"),
    ("3", "March 2025", "Q1 2025"),
    ("4", "April 2025", "Q2 2025"),
    ("5", "May 2025", "Q2 2025"),
    ("6", "June 2025", "Q2 2025"),
    ("7", "July 2025", "Q3 2025"),
    ("8", "August 2025", "Q3 2025"),
    ("9", "September 2025", "Q3 Chop"),
    ("10", "October 2025", "Q4 Uptrend"),
    ("11", "November 2025", "Q4 Bull Run"),
    ("12", "December 2025", "Q4 Volatile")
]

for key, name, desc in months_2025:
    print(f"    [{key:>2s}] {name:20s} - {desc}")

print("\n  Recent (2026):")
print(f"    [13] {'January 2026':20s} - Recent (18 days)")

print("\n  Quarterly Aggregates:")
quarters = [
    ("q1", "Q1 2025 (Jan-Mar)", "3 months"),
    ("q2", "Q2 2025 (Apr-Jun)", "3 months"),
    ("q3", "Q3 2025 (Jul-Sep)", "3 months"),
    ("q4", "Q4 2025 (Oct-Dec)", "3 months")
]

for key, name, desc in quarters:
    print(f"    [{key:>2s}] {name:20s} - {desc}")

print("\n  Full Period Tests:")
full_tests = [
    ("2025", "Full Year 2025", "All 12 months"),
    ("all", "All Available Data", "13 months (Jan 2025 - Jan 2026)")
]

for key, name, desc in full_tests:
    print(f"    [{key:>4s}] {name:20s} - {desc}")

print("\n" + "="*70)
print("✅ ENHANCED FEATURES:")
print("="*70)
print("  • 13 individual months available (Jan 2025 - Jan 2026)")
print("  • 4 quarterly aggregates (Q1-Q4 2025)")
print("  • Full year 2025 test (12 months)")
print("  • All data test (13 months total)")
print("  • Automatic aggregate statistics for multi-month tests")
print("="*70)
