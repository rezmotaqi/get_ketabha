#!/usr/bin/env python3
"""
Test script to verify metrics are working correctly.
Run this to test if metrics are being generated and served.
"""

import time
import requests
import sys
import os

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_metrics_endpoint():
    """Test if the metrics endpoint is accessible."""
    try:
        response = requests.get('http://localhost:8000/metrics', timeout=5)
        if response.status_code == 200:
            print("✅ Metrics endpoint is accessible")
            print(f"Response length: {len(response.text)} characters")
            return True
        else:
            print(f"❌ Metrics endpoint returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to metrics endpoint. Is the bot running?")
        return False
    except Exception as e:
        print(f"❌ Error accessing metrics endpoint: {e}")
        return False

def test_metrics_content():
    """Test if metrics contain expected data."""
    try:
        response = requests.get('http://localhost:8000/metrics', timeout=5)
        content = response.text
        
        # Check for common metrics
        expected_metrics = [
            'http_requests_total',
            'search_requests_total',
            'bot_messages_total',
            'system_status',
            'memory_usage_bytes',
            'cpu_usage_percent'
        ]
        
        found_metrics = []
        for metric in expected_metrics:
            if metric in content:
                found_metrics.append(metric)
                print(f"✅ Found metric: {metric}")
            else:
                print(f"❌ Missing metric: {metric}")
        
        print(f"\nFound {len(found_metrics)}/{len(expected_metrics)} expected metrics")
        return len(found_metrics) > 0
        
    except Exception as e:
        print(f"❌ Error checking metrics content: {e}")
        return False

def test_prometheus_target():
    """Test if Prometheus can reach the target."""
    try:
        # This would require Prometheus to be running
        response = requests.get('http://localhost:9090/api/v1/targets', timeout=5)
        if response.status_code == 200:
            targets = response.json()
            print("✅ Prometheus is running")
            
            # Check for our bot target
            for target in targets.get('data', {}).get('activeTargets', []):
                if target.get('job') == 'libgen-bot':
                    health = target.get('health')
                    print(f"Bot target health: {health}")
                    if health == 'up':
                        print("✅ Bot target is UP in Prometheus")
                        return True
                    else:
                        print(f"❌ Bot target is {health.upper()} in Prometheus")
                        return False
            
            print("❌ Bot target not found in Prometheus")
            return False
        else:
            print(f"❌ Prometheus returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to Prometheus. Is it running?")
        return False
    except Exception as e:
        print(f"❌ Error checking Prometheus targets: {e}")
        return False

def generate_test_metrics():
    """Generate some test metrics by importing and using the monitoring system."""
    try:
        from monitoring import initialize_metrics, get_metrics_integration
        
        print("🔄 Initializing metrics system...")
        if initialize_metrics(port=8001):  # Use different port to avoid conflicts
            print("✅ Metrics system initialized")
            
            # Get metrics integration
            integration = get_metrics_integration()
            metrics = integration.metrics
            
            # Generate some test metrics
            print("🔄 Generating test metrics...")
            
            # Record some test data
            metrics.record_system_status("test_component", "running")
            metrics.record_search_request("test_search", "success", 1.5, 5)
            metrics.record_bot_message("test_message", "success")
            metrics.record_user_info("test_user", "testuser", "test_type", "test_action")
            
            print("✅ Test metrics generated")
            
            # Test the endpoint
            time.sleep(1)  # Give it a moment to update
            response = requests.get('http://localhost:8001/metrics', timeout=5)
            if response.status_code == 200:
                print("✅ Test metrics endpoint is working")
                print("Sample metrics:")
                lines = response.text.split('\n')[:10]  # Show first 10 lines
                for line in lines:
                    if line.strip():
                        print(f"  {line}")
                return True
            else:
                print(f"❌ Test metrics endpoint failed: {response.status_code}")
                return False
        else:
            print("❌ Failed to initialize metrics system")
            return False
            
    except Exception as e:
        print(f"❌ Error generating test metrics: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Testing Metrics System")
    print("=" * 50)
    
    # Test 1: Check if metrics endpoint is accessible
    print("\n1. Testing metrics endpoint accessibility...")
    endpoint_ok = test_metrics_endpoint()
    
    # Test 2: Check metrics content
    print("\n2. Testing metrics content...")
    content_ok = test_metrics_content()
    
    # Test 3: Check Prometheus target
    print("\n3. Testing Prometheus target...")
    prometheus_ok = test_prometheus_target()
    
    # Test 4: Generate test metrics
    print("\n4. Generating test metrics...")
    test_metrics_ok = generate_test_metrics()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results Summary:")
    print(f"  Metrics Endpoint: {'✅ PASS' if endpoint_ok else '❌ FAIL'}")
    print(f"  Metrics Content:  {'✅ PASS' if content_ok else '❌ FAIL'}")
    print(f"  Prometheus Target: {'✅ PASS' if prometheus_ok else '❌ FAIL'}")
    print(f"  Test Metrics:     {'✅ PASS' if test_metrics_ok else '❌ FAIL'}")
    
    if all([endpoint_ok, content_ok, prometheus_ok]):
        print("\n🎉 All tests passed! Metrics should be working in Prometheus.")
    else:
        print("\n⚠️  Some tests failed. Check the troubleshooting guide.")
        print("   See: monitoring/troubleshoot_prometheus.md")

if __name__ == "__main__":
    main()
