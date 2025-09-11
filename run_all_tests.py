#!/usr/bin/env python3
"""
Test Runner
Runs all tests and provides a comprehensive report
"""

import asyncio
import sys
import os
import time
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import test modules
from test_concurrent_downloads import test_concurrent_downloads
from test_bot_integration import test_bot_integration
from test_performance_metrics import test_performance_metrics
from test_error_handling import test_error_handling

async def run_all_tests():
    """Run all tests and provide comprehensive report"""
    print("🧪 Comprehensive Test Suite")
    print("=" * 60)
    print(f"⏰ Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Test configuration
    tests = [
        {
            'name': 'Concurrent Downloads',
            'description': 'Tests true concurrent file downloads without blocking',
            'function': test_concurrent_downloads,
            'critical': True
        },
        {
            'name': 'Bot Integration',
            'description': 'Tests bot integration with concurrent file handling',
            'function': test_bot_integration,
            'critical': True
        },
        {
            'name': 'Performance Metrics',
            'description': 'Tests performance tracking and logging features',
            'function': test_performance_metrics,
            'critical': False
        },
        {
            'name': 'Error Handling',
            'description': 'Tests error handling and edge cases',
            'function': test_error_handling,
            'critical': False
        }
    ]
    
    # Run tests
    test_results = []
    overall_start_time = time.time()
    
    for i, test in enumerate(tests, 1):
        print(f"🔬 Test {i}/{len(tests)}: {test['name']}")
        print(f"   📝 {test['description']}")
        print(f"   {'🔴 Critical' if test['critical'] else '🟡 Optional'}")
        print()
        
        test_start_time = time.time()
        
        try:
            result = await test['function']()
            test_duration = time.time() - test_start_time
            
            test_results.append({
                'name': test['name'],
                'description': test['description'],
                'critical': test['critical'],
                'passed': result,
                'duration': test_duration,
                'error': None
            })
            
            status = "✅ PASSED" if result else "❌ FAILED"
            print(f"   {status} in {test_duration:.2f}s")
            
        except Exception as e:
            test_duration = time.time() - test_start_time
            
            test_results.append({
                'name': test['name'],
                'description': test['description'],
                'critical': test['critical'],
                'passed': False,
                'duration': test_duration,
                'error': str(e)
            })
            
            print(f"   💥 ERROR in {test_duration:.2f}s: {e}")
        
        print()
    
    total_duration = time.time() - overall_start_time
    
    # Generate comprehensive report
    print("📊 Test Results Summary")
    print("=" * 60)
    print(f"⏰ Completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️ Total Duration: {total_duration:.2f}s")
    print()
    
    # Test results table
    print("📋 Test Results:")
    print("-" * 80)
    print(f"{'Test Name':<20} {'Status':<8} {'Duration':<10} {'Critical':<8} {'Notes'}")
    print("-" * 80)
    
    for result in test_results:
        status = "✅ PASS" if result['passed'] else "❌ FAIL"
        critical = "🔴 YES" if result['critical'] else "🟡 NO"
        duration = f"{result['duration']:.2f}s"
        notes = "ERROR" if result['error'] else ""
        
        print(f"{result['name']:<20} {status:<8} {duration:<10} {critical:<8} {notes}")
    
    print("-" * 80)
    
    # Statistics
    total_tests = len(test_results)
    passed_tests = len([r for r in test_results if r['passed']])
    failed_tests = total_tests - passed_tests
    critical_tests = len([r for r in test_results if r['critical']])
    critical_passed = len([r for r in test_results if r['critical'] and r['passed']])
    critical_failed = critical_tests - critical_passed
    
    print(f"\n📈 Statistics:")
    print(f"   📊 Total Tests: {total_tests}")
    print(f"   ✅ Passed: {passed_tests}")
    print(f"   ❌ Failed: {failed_tests}")
    print(f"   📊 Success Rate: {passed_tests/total_tests:.1%}")
    print()
    print(f"   🔴 Critical Tests: {critical_tests}")
    print(f"   ✅ Critical Passed: {critical_passed}")
    print(f"   ❌ Critical Failed: {critical_failed}")
    print(f"   📊 Critical Success Rate: {critical_passed/critical_tests:.1%}" if critical_tests > 0 else "   📊 Critical Success Rate: N/A")
    
    # Performance analysis
    avg_duration = sum(r['duration'] for r in test_results) / total_tests
    fastest_test = min(test_results, key=lambda x: x['duration'])
    slowest_test = max(test_results, key=lambda x: x['duration'])
    
    print(f"\n⚡ Performance Analysis:")
    print(f"   ⏱️ Average Test Duration: {avg_duration:.2f}s")
    print(f"   🚀 Fastest Test: {fastest_test['name']} ({fastest_test['duration']:.2f}s)")
    print(f"   🐌 Slowest Test: {slowest_test['name']} ({slowest_test['duration']:.2f}s)")
    
    # Failed tests details
    failed_tests_list = [r for r in test_results if not r['passed']]
    if failed_tests_list:
        print(f"\n❌ Failed Tests Details:")
        for result in failed_tests_list:
            print(f"   🔴 {result['name']}: {result['error'] or 'Test failed'}")
    
    # Overall result
    all_critical_passed = critical_failed == 0
    overall_success_rate = passed_tests / total_tests
    
    print(f"\n🎯 Overall Result:")
    print(f"   📊 Overall Success Rate: {overall_success_rate:.1%}")
    print(f"   🔴 Critical Tests: {'✅ ALL PASSED' if all_critical_passed else '❌ SOME FAILED'}")
    
    if all_critical_passed and overall_success_rate >= 0.8:
        print(f"   🎉 OVERALL: ✅ PASSED - System is ready for production!")
        overall_passed = True
    elif all_critical_passed:
        print(f"   ⚠️ OVERALL: ⚠️ PARTIAL - Critical tests passed but some optional tests failed")
        overall_passed = True
    else:
        print(f"   💥 OVERALL: ❌ FAILED - Critical tests failed, system needs fixes")
        overall_passed = False
    
    # Recommendations
    print(f"\n💡 Recommendations:")
    if all_critical_passed and overall_success_rate >= 0.9:
        print(f"   ✅ Excellent! All systems are working optimally.")
        print(f"   🚀 Ready for production deployment.")
    elif all_critical_passed:
        print(f"   ✅ Good! Critical functionality is working.")
        print(f"   🔧 Consider fixing failed optional tests for better performance.")
    else:
        print(f"   🔧 Critical issues found that need immediate attention.")
        print(f"   🛠️ Fix failed critical tests before deployment.")
    
    if failed_tests_list:
        print(f"   📝 Focus on these failed tests:")
        for result in failed_tests_list:
            if result['critical']:
                print(f"      🔴 {result['name']} (CRITICAL)")
            else:
                print(f"      🟡 {result['name']} (Optional)")
    
    print(f"\n🏁 Test suite completed!")
    
    return overall_passed

if __name__ == '__main__':
    result = asyncio.run(run_all_tests())
    exit(0 if result else 1)
