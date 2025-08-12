#!/usr/bin/env python3
"""
Complete setup: Create RDS instance and set up tables
"""

import sys
import os
sys.path.append('/home/hxnguyen/cloudProjects/serverless-e-commerce/lambda')

from rds import RDSManager
from rds.rds_operations import RDSOperations

def setup_complete_ecommerce_database():
    """Create RDS instance and set up e-commerce tables"""
    
    # Configuration
    db_instance_identifier = "mypostgresdb"
    instance_identifier = "myinstance"
    
    print("🚀 Setting up complete e-commerce database...")
    
    # Step 1: Create RDS infrastructure
    print("\n1. Creating RDS infrastructure...")
    rds_manager = RDSManager()
    
    try:
        # Clean up first (optional)
        # rds_manager.cleanup_complete_setup(db_instance_identifier, instance_identifier)
        
        # Create complete setup
        result = rds_manager.create_complete_rds_setup(db_instance_identifier, instance_identifier)
        print("✅ RDS infrastructure created successfully!")
        
        # Wait a bit for RDS to be fully available
        print("\n⏳ Waiting for RDS instance to be fully available...")
        import time
        time.sleep(60)  # Wait 1 minute
        
        # Step 2: Create database tables
        print("\n2. Creating e-commerce tables...")
        rds_ops = RDSOperations()
        
        # Set environment variables for database credentials
        os.environ['DB_USERNAME'] = 'dbuser'
        os.environ['DB_PASSWORD'] = 'YourSecurePassword123!'
        
        table_result = rds_ops.create_ecommerce_tables(db_instance_identifier)
        
        if table_result['success']:
            print("✅ All tables created successfully!")
            
            # Step 3: Insert sample data
            print("\n3. Inserting sample data...")
            sample_result = rds_ops.insert_sample_data(db_instance_identifier)
            
            if sample_result['success']:
                print("✅ Sample data inserted successfully!")
            else:
                print("⚠️ Some sample data insertion failed:")
                for error in sample_result['errors']:
                    print(f"   {error}")
        else:
            print("❌ Table creation failed:")
            for error in table_result['errors']:
                print(f"   {error}")
        
        print(f"\n🎉 E-commerce database setup complete!")
        print(f"📊 Database: {db_instance_identifier}")
        print(f"🔗 VPC: {result['vpc_info']['vpc_id']}")
        print(f"📋 Tables created: {table_result['created_tables'] if table_result['success'] else 'Failed'}")
        
    except Exception as e:
        print(f"❌ Setup failed: {e}")
        return False
    
    return True

def test_database_connection():
    """Test connection to the database and list tables"""
    
    db_instance_identifier = "mypostgresdb"
    
    print("\n🔍 Testing database connection...")
    
    try:
        rds_ops = RDSOperations()
        
        # Set environment variables
        os.environ['DB_USERNAME'] = 'dbuser'
        os.environ['DB_PASSWORD'] = 'YourSecurePassword123!'
        
        connection = rds_ops.connect_to_database(db_instance_identifier)
        
        # List all tables
        query = """
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        ORDER BY table_name;
        """
        
        tables = rds_ops.execute_sql_query(connection, query, fetch=True)
        
        print("✅ Database connection successful!")
        print("📋 Tables in database:")
        for table in tables:
            print(f"   - {table[0]}")
        
        # Get some sample data
        print("\n📊 Sample data from users table:")
        users_query = "SELECT user_id, username, email, first_name, last_name FROM users LIMIT 5;"
        users = rds_ops.execute_sql_query(connection, users_query, fetch=True)
        
        if users:
            for user in users:
                print(f"   User ID: {user[0]}, Username: {user[1]}, Email: {user[2]}, Name: {user[3]} {user[4]}")
        else:
            print("   No users found")
        
        connection.close()
        
    except Exception as e:
        print(f"❌ Database connection test failed: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "setup":
            setup_complete_ecommerce_database()
        elif sys.argv[1] == "test":
            test_database_connection()
        else:
            print("Usage:")
            print("  python complete_setup.py setup  # Create RDS and tables")
            print("  python complete_setup.py test   # Test database connection")
    else:
        print("Usage:")
        print("  python complete_setup.py setup  # Create RDS and tables")
        print("  python complete_setup.py test   # Test database connection")
