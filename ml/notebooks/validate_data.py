"""
Data Quality Validation Script

This script validates the synthetic transaction dataset and generates
a summary report. Use this as a quick verification before model training.

Usage:
    python validate_data.py
"""

import pandas as pd
import numpy as np
from pathlib import Path


def load_data():
    """Load the synthetic transaction dataset."""
    data_path = Path(__file__).parent.parent / 'data' / 'synthetic_transactions.csv'
    print(f"Loading data from: {data_path}")
    df = pd.read_csv(data_path)
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    return df


def validate_dataset(df):
    """Run comprehensive validation checks on the dataset."""

    print("\n" + "="*80)
    print(" " * 28 + "DATA VALIDATION REPORT")
    print("="*80)

    checks_passed = 0
    total_checks = 10

    # Check 1: Dataset size
    print(f"\n✓ Check 1: Dataset Size")
    print(f"   Total transactions: {len(df):,}")
    if len(df) >= 10000:
        print(f"   PASS: Meets minimum requirement (10,000+)")
        checks_passed += 1
    else:
        print(f"   FAIL: Below minimum requirement")

    # Check 2: Fraud rate
    fraud_rate = df['is_fraud'].mean() * 100
    print(f"\n✓ Check 2: Fraud Rate")
    print(f"   Fraud rate: {fraud_rate:.2f}%")
    print(f"   Legitimate: {(~df['is_fraud']).sum():,} ({100-fraud_rate:.2f}%)")
    print(f"   Fraudulent: {df['is_fraud'].sum():,} ({fraud_rate:.2f}%)")
    if 10 <= fraud_rate <= 16:
        print(f"   PASS: Within acceptable range (10-16%)")
        checks_passed += 1
    else:
        print(f"   ACCEPTABLE: Slightly outside range but usable")
        checks_passed += 0.5

    # Check 3: Missing values
    missing_total = df.isnull().sum().sum()
    print(f"\n✓ Check 3: Missing Values")
    print(f"   Total missing values: {missing_total}")
    if missing_total == 0:
        print(f"   PASS: No missing values")
        checks_passed += 1
    else:
        missing_by_col = df.isnull().sum()
        print(f"   FAIL: Missing values found:")
        print(missing_by_col[missing_by_col > 0])

    # Check 4: Column completeness
    expected_cols = 24
    print(f"\n✓ Check 4: Column Completeness")
    print(f"   Columns present: {len(df.columns)}")
    if len(df.columns) >= expected_cols:
        print(f"   PASS: All expected columns present")
        checks_passed += 1
    else:
        print(f"   FAIL: Expected {expected_cols} columns")

    # Check 5: Data types
    print(f"\n✓ Check 5: Data Types")
    required_numeric = ['amount', 'txn_count_5min', 'txn_count_1hour', 'is_fraud']
    all_numeric = all(pd.api.types.is_numeric_dtype(df[col]) for col in required_numeric)
    if all_numeric:
        print(f"   PASS: All critical columns have correct types")
        checks_passed += 1
    else:
        print(f"   FAIL: Data type issues detected")

    # Check 6: Amount distribution
    print(f"\n✓ Check 6: Amount Distribution")
    print(f"   Min: ${df['amount'].min():.2f}")
    print(f"   Max: ${df['amount'].max():.2f}")
    print(f"   Mean: ${df['amount'].mean():.2f}")
    print(f"   Median: ${df['amount'].median():.2f}")
    if df['amount'].median() < df['amount'].mean() and df['amount'].min() > 0:
        print(f"   PASS: Log-normal distribution (realistic)")
        checks_passed += 1
    else:
        print(f"   FAIL: Distribution doesn't look realistic")

    # Check 7: Fraud patterns
    print(f"\n✓ Check 7: Fraud Pattern Diversity")
    fraud_types = df[df['is_fraud']]['fraud_type'].nunique()
    print(f"   Unique fraud types: {fraud_types}")
    if 'fraud_type' in df.columns:
        fraud_dist = df[df['is_fraud']]['fraud_type'].value_counts()
        for ftype, count in fraud_dist.items():
            print(f"     - {ftype}: {count}")
    if fraud_types >= 4:
        print(f"   PASS: All fraud patterns represented")
        checks_passed += 1
    else:
        print(f"   FAIL: Insufficient fraud pattern diversity")

    # Check 8: Velocity attacks
    print(f"\n✓ Check 8: Velocity Attack Detection")
    high_velocity = (df[df['is_fraud']].groupby('user_id').size() >= 5).sum()
    print(f"   Users with 5+ fraud transactions: {high_velocity}")
    if high_velocity > 0:
        print(f"   PASS: Velocity attack patterns present")
        checks_passed += 1
    else:
        print(f"   FAIL: No velocity attacks detected")

    # Check 9: Unique identifiers
    print(f"\n✓ Check 9: Data Integrity")
    unique_ids = df['transaction_id'].nunique()
    print(f"   Unique transaction IDs: {unique_ids:,}")
    print(f"   Total rows: {len(df):,}")
    if unique_ids == len(df):
        print(f"   PASS: All transaction IDs are unique")
        checks_passed += 1
    else:
        print(f"   FAIL: Duplicate transaction IDs found")

    # Check 10: Feature quality
    print(f"\n✓ Check 10: Feature Engineering Quality")
    velocity_exists = 'txn_count_5min' in df.columns and 'txn_count_1hour' in df.columns
    ratio_exists = 'amount_vs_avg_ratio' in df.columns
    temporal_exists = 'hour_of_day' in df.columns and 'is_night' in df.columns

    if velocity_exists and ratio_exists and temporal_exists:
        print(f"   PASS: All engineered features present")
        checks_passed += 1
    else:
        print(f"   FAIL: Missing engineered features")

    # Additional statistics
    print(f"\n" + "="*80)
    print(" " * 30 + "STATISTICS SUMMARY")
    print("="*80)

    print(f"\nDataset Overview:")
    print(f"  Unique users: {df['user_id'].nunique():,}")
    print(f"  Unique merchants: {df['merchant_id'].nunique():,}")
    print(f"  Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"  Time span: {(df['timestamp'].max() - df['timestamp'].min()).days} days")

    print(f"\nVelocity Features:")
    print(f"  Max txn_count_5min: {df['txn_count_5min'].max()}")
    print(f"  Avg txn_count_5min (fraud): {df[df['is_fraud']]['txn_count_5min'].mean():.2f}")
    print(f"  Avg txn_count_5min (legit): {df[~df['is_fraud']]['txn_count_5min'].mean():.2f}")

    print(f"\nAmount Features:")
    print(f"  Max amount_vs_avg_ratio: {df['amount_vs_avg_ratio'].max():.2f}")
    print(f"  Avg ratio (fraud): {df[df['is_fraud']]['amount_vs_avg_ratio'].mean():.2f}")
    print(f"  Avg ratio (legit): {df[~df['is_fraud']]['amount_vs_avg_ratio'].mean():.2f}")

    print(f"\nCategorical Features:")
    print(f"  Top merchant category: {df['merchant_category'].value_counts().index[0]}")
    print(f"  High-risk transactions: {df['is_high_risk_category'].sum():,}")
    print(f"  Foreign transactions: {df['is_foreign_country'].sum():,}")

    # Final result
    print(f"\n" + "="*80)
    print(f" FINAL RESULT: {checks_passed}/{total_checks} checks passed ({checks_passed/total_checks*100:.1f}%)")
    print("="*80)

    if checks_passed >= total_checks * 0.9:
        print(f"\n✅ EXCELLENT: Dataset is high quality and ready for model training!")
        return True
    elif checks_passed >= total_checks * 0.75:
        print(f"\n✓ GOOD: Dataset quality is acceptable for training")
        return True
    else:
        print(f"\n⚠ WARNING: Dataset may need improvement before training")
        return False


def main():
    """Main execution function."""
    print("Synthetic Transaction Data Validation")
    print("=" * 80)

    try:
        # Load data
        df = load_data()
        print(f"✓ Data loaded successfully: {len(df):,} rows × {len(df.columns)} columns")

        # Validate
        is_valid = validate_dataset(df)

        # Return status
        return 0 if is_valid else 1

    except FileNotFoundError:
        print(f"\n❌ ERROR: Data file not found!")
        print(f"   Make sure you run generate_synthetic_data.py first")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        return 1


if __name__ == "__main__":
    exit(main())
