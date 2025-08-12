#!/usr/bin/env python3
"""
Demo script to test AWS Lambda functions locally
"""

import json
import os
import sys
sys.path.append('/home/hxnguyen/cloudProjects/serverless-e-commerce/lambda')

from rds.rds_operations import (
    lambda_create_tables, 
    lambda_insert_sample_data, 
    lambda_create_custom_table,
    lambda_execute_query
)

def demo_lambda_functions():
    """Demo all Lambda functions"""
    
    # Set environment variables for database credentials
    os.environ['DB_USERNAME'] = 'dbuser'
    os.environ['DB_PASSWORD'] = 'YourSecurePassword123!'
    
    db_instance_identifier = "mypostgresdb"
    
    print("🚀 Testing Lambda functions locally...")
    
    # Test 1: Create tables
    print("\n1. Testing lambda_create_tables...")
    event1 = {
        "db_instance_identifier": db_instance_identifier,
        "use_secrets": False
    }
    
    result1 = lambda_create_tables(event1, None)
    print(f"Response: {json.dumps(result1, indent=2)}")
    
    # Test 2: Insert sample data
    print("\n2. Testing lambda_insert_sample_data...")
    event2 = {
        "db_instance_identifier": db_instance_identifier,
        "use_secrets": False
    }
    
    result2 = lambda_insert_sample_data(event2, None)
    print(f"Response: {json.dumps(result2, indent=2)}")
    
    # Test 3: Create custom table
    print("\n3. Testing lambda_create_custom_table...")
    event3 = {
        "db_instance_identifier": db_instance_identifier,
        "table_name": "analytics",
        "table_schema": """
            CREATE TABLE IF NOT EXISTS analytics (
                id SERIAL PRIMARY KEY,
                event_name VARCHAR(100) NOT NULL,
                user_id INTEGER,
                event_data JSONB,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """,
        "use_secrets": False
    }
    
    result3 = lambda_create_custom_table(event3, None)
    print(f"Response: {json.dumps(result3, indent=2)}")
    
    # Test 4: Execute query
    print("\n4. Testing lambda_execute_query...")
    event4 = {
        "db_instance_identifier": db_instance_identifier,
        "query": "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;",
        "fetch": True,
        "use_secrets": False
    }
    
    result4 = lambda_execute_query(event4, None)
    print(f"Response: {json.dumps(result4, indent=2)}")
    
    # Test 5: Execute insert query
    print("\n5. Testing insert query...")
    event5 = {
        "db_instance_identifier": db_instance_identifier,
        "query": "INSERT INTO analytics (event_name, user_id, event_data) VALUES ('page_view', 1, '{\"page\": \"/home\", \"duration\": 30}');",
        "fetch": False,
        "use_secrets": False
    }
    
    result5 = lambda_execute_query(event5, None)
    print(f"Response: {json.dumps(result5, indent=2)}")

def demo_error_handling():
    """Demo error handling"""
    
    print("\n🔍 Testing error handling...")
    
    # Test with missing required fields
    event_bad = {}
    result = lambda_create_tables(event_bad, None)
    print(f"Error response: {json.dumps(result, indent=2)}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "error":
        demo_error_handling()
    else:
        demo_lambda_functions()
