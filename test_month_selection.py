#!/usr/bin/env python3
"""
Test script to demonstrate the new month selection functionality.
This script shows how the improved invoice processing works.
"""

import asyncio
from src.polaroo_scrape import (
    get_user_month_selection,
    filter_invoices_by_date_range,
    analyze_invoices_with_cohere
)

def test_month_selection():
    """Test the month selection functionality."""
    print("🧪 [TEST] Testing month selection functionality...")
    
    # Test month selection (commented out for automated testing)
    # start_month, end_month = get_user_month_selection()
    # print(f"Selected months: {start_month} to {end_month}")
    
    # For testing, use hardcoded months
    start_month = "2024-10"
    end_month = "2024-11"
    print(f"Using test months: {start_month} to {end_month}")

def test_invoice_filtering():
    """Test the invoice filtering functionality."""
    print("🧪 [TEST] Testing invoice filtering...")
    
    # Sample invoice data
    sample_invoices = [
        {
            'service': 'electricity',
            'initial_date': '2024-10-01',
            'final_date': '2024-10-31',
            'total': '€45.50',
            'provider': 'Iberdrola'
        },
        {
            'service': 'electricity',
            'initial_date': '2024-11-01',
            'final_date': '2024-11-30',
            'total': '€52.30',
            'provider': 'Iberdrola'
        },
        {
            'service': 'water',
            'initial_date': '2024-10-01',
            'final_date': '2024-11-30',
            'total': '€38.75',
            'provider': 'Canal de Isabel II'
        },
        {
            'service': 'electricity',
            'initial_date': '2024-09-01',
            'final_date': '2024-09-30',
            'total': '€41.20',
            'provider': 'Iberdrola'
        }
    ]
    
    # Test filtering
    start_month = "2024-10"
    end_month = "2024-11"
    filtered = filter_invoices_by_date_range(sample_invoices, start_month, end_month)
    
    print(f"Original invoices: {len(sample_invoices)}")
    print(f"Filtered invoices: {len(filtered)}")
    
    for inv in filtered:
        print(f"  - {inv['service']}: {inv['initial_date']} to {inv['final_date']} = {inv['total']}")

def test_llm_analysis():
    """Test the LLM analysis functionality."""
    print("🧪 [TEST] Testing LLM analysis...")
    
    # Sample filtered invoices
    sample_invoices = [
        {
            'service': 'electricity',
            'initial_date': '2024-10-01',
            'final_date': '2024-10-31',
            'total': '€45.50',
            'provider': 'Iberdrola',
            'company': 'Test Company'
        },
        {
            'service': 'electricity',
            'initial_date': '2024-11-01',
            'final_date': '2024-11-30',
            'total': '€52.30',
            'provider': 'Iberdrola',
            'company': 'Test Company'
        },
        {
            'service': 'water',
            'initial_date': '2024-10-01',
            'final_date': '2024-11-30',
            'total': '€38.75',
            'provider': 'Canal de Isabel II',
            'company': 'Test Company'
        }
    ]
    
    start_month = "2024-10"
    end_month = "2024-11"
    
    # Test analysis (this will use fallback logic if Cohere is not available)
    analysis = analyze_invoices_with_cohere(sample_invoices, start_month, end_month)
    
    print(f"Analysis results:")
    print(f"  - Total electricity: €{analysis['total_electricity']:.2f}")
    print(f"  - Total water: €{analysis['total_water']:.2f}")
    print(f"  - Total all: €{analysis['total_all']:.2f}")
    print(f"  - Selected invoices: {len(analysis['selected_invoices'])}")
    print(f"  - Reasoning: {analysis['reasoning']}")

if __name__ == "__main__":
    print("🚀 [START] Testing improved Polaroo invoice processing...")
    
    test_month_selection()
    print()
    
    test_invoice_filtering()
    print()
    
    test_llm_analysis()
    print()
    
    print("✅ [COMPLETE] All tests completed!")
