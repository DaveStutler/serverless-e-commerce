import boto3
import psycopg2
import json
import os
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError


class RDSOperations:
    """
    AWS Lambda functions for RDS PostgreSQL operations using psycopg2
    """
    
    def __init__(self):
        self.rds_client = boto3.client('rds')
        self.secrets_client = boto3.client('secretsmanager')
    
    def check_rds_instance_status(self, db_instance_identifier: str) -> Dict[str, Any]:
        """Check the status and details of an RDS instance"""
        try:
            response = self.rds_client.describe_db_instances(
                DBInstanceIdentifier=db_instance_identifier
            )
            
            db_instance = response['DBInstances'][0]
            
            status_info = {
                'identifier': db_instance['DBInstanceIdentifier'],
                'status': db_instance['DBInstanceStatus'],
                'engine': db_instance['Engine'],
                'engine_version': db_instance['EngineVersion'],
                'instance_class': db_instance['DBInstanceClass'],
                'allocated_storage': db_instance['AllocatedStorage'],
                'multi_az': db_instance['MultiAZ'],
                'publicly_accessible': db_instance['PubliclyAccessible'],
                'vpc_security_groups': [sg['VpcSecurityGroupId'] for sg in db_instance['VpcSecurityGroups']],
                'availability_zone': db_instance.get('AvailabilityZone', 'N/A'),
                'backup_retention_period': db_instance['BackupRetentionPeriod'],
                'creation_time': db_instance['InstanceCreateTime'].isoformat() if 'InstanceCreateTime' in db_instance else 'N/A'
            }
            
            if 'Endpoint' in db_instance:
                status_info['endpoint'] = {
                    'address': db_instance['Endpoint']['Address'],
                    'port': db_instance['Endpoint']['Port']
                }
            else:
                status_info['endpoint'] = None
                
            return status_info
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'DBInstanceNotFoundFault':
                return {'error': f"RDS instance '{db_instance_identifier}' not found"}
            else:
                return {'error': f"AWS error: {e.response['Error']['Message']}"}
        except Exception as e:
            return {'error': f"Unexpected error: {str(e)}"}
    
    def wait_for_rds_available(self, db_instance_identifier: str, max_wait_minutes: int = 10) -> bool:
        """Wait for RDS instance to become available"""
        import time
        
        print(f"⏳ Waiting for RDS instance '{db_instance_identifier}' to become available...")
        start_time = time.time()
        max_wait_seconds = max_wait_minutes * 60
        
        while time.time() - start_time < max_wait_seconds:
            status_info = self.check_rds_instance_status(db_instance_identifier)
            
            if 'error' in status_info:
                print(f"❌ Error checking instance: {status_info['error']}")
                return False
            
            current_status = status_info['status']
            elapsed_minutes = (time.time() - start_time) / 60
            
            print(f"📊 Status: {current_status} (waited {elapsed_minutes:.1f}/{max_wait_minutes} minutes)")
            
            if current_status == 'available':
                print(f"✅ RDS instance is now available!")
                return True
            elif current_status in ['failed', 'incompatible-parameters', 'incompatible-restore']:
                print(f"❌ RDS instance is in failed state: {current_status}")
                return False
            
            print("⏳ Still waiting... (checking again in 30 seconds)")
            time.sleep(30)
        
        print(f"⏰ Timeout: RDS instance did not become available within {max_wait_minutes} minutes")
        return False
    
    def get_db_connection_info(self, db_instance_identifier: str) -> Dict[str, str]:
        """Get RDS instance connection information"""
        try:
            response = self.rds_client.describe_db_instances(
                DBInstanceIdentifier=db_instance_identifier
            )
            
            db_instance = response['DBInstances'][0]
            
            # Handle DBName safely - it might not exist or be None
            db_name = db_instance.get('DBName')
            if not db_name:
                db_name = 'postgres'  # Default PostgreSQL database
            
            return {
                'host': db_instance['Endpoint']['Address'],
                'port': db_instance['Endpoint']['Port'],
                'database': db_name,
                'engine': db_instance['Engine'],
                'status': db_instance['DBInstanceStatus']
            }
        except Exception as e:
            print(f"Error getting DB connection info: {e}")
            raise
    
    def get_db_credentials_from_env(self) -> Dict[str, str]:
        """Get database credentials from environment variables"""
        return {
            'username': os.environ.get('DB_USERNAME', 'dbuser'),
            'password': os.environ.get('DB_PASSWORD', 'YourSecurePassword123!')
        }
    
    def get_db_credentials_from_secrets(self, secret_name: str) -> Dict[str, str]:
        """Get database credentials from AWS Secrets Manager"""
        try:
            response = self.secrets_client.get_secret_value(SecretId=secret_name)
            secret = json.loads(response['SecretString'])
            
            return {
                'username': secret['username'],
                'password': secret['password']
            }
        except Exception as e:
            print(f"Error getting credentials from Secrets Manager: {e}")
            raise
    
    def connect_to_database(self, db_instance_identifier: str, use_secrets: bool = False, secret_name: str = None) -> psycopg2.extensions.connection:
        """Create a connection to the PostgreSQL database"""
        try:
            # Get connection info
            print(f"🔍 Getting connection info for RDS instance: {db_instance_identifier}")
            conn_info = self.get_db_connection_info(db_instance_identifier)
            
            print(f"📋 Connection details:")
            print(f"   Host: {conn_info['host']}")
            print(f"   Port: {conn_info['port']}")
            print(f"   Database: {conn_info['database']}")
            print(f"   Status: {conn_info['status']}")
            
            # Check if RDS instance is available
            if conn_info['status'] != 'available':
                raise Exception(f"RDS instance is not available. Current status: {conn_info['status']}")
            
            # Get credentials
            if use_secrets and secret_name:
                print(f"🔐 Getting credentials from Secrets Manager: {secret_name}")
                credentials = self.get_db_credentials_from_secrets(secret_name)
            else:
                print("🔐 Getting credentials from environment variables")
                credentials = self.get_db_credentials_from_env()
            
            print(f"   Username: {credentials['username']}")
            print(f"   Password: {'*' * len(credentials['password'])}")
            
            # Create connection with longer timeout
            print("🔌 Attempting database connection...")
            connection = psycopg2.connect(
                host=conn_info['host'],
                port=conn_info['port'],
                database=conn_info['database'],
                user=credentials['username'],
                password=credentials['password'],
                connect_timeout=30,  # Increased timeout to 30 seconds
                application_name='RDSOperations'
            )
            
            # Test the connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT version();")
                version = cursor.fetchone()[0]
                print(f"✅ Successfully connected to PostgreSQL: {version[:50]}...")
            
            return connection
            
        except psycopg2.OperationalError as e:
            error_msg = str(e)
            print(f"❌ Database connection failed: {error_msg}")
            
            if "timeout" in error_msg.lower():
                print("💡 Troubleshooting timeout:")
                print("   1. Check if RDS instance is in 'available' status")
                print("   2. Verify security group allows inbound connections on port 5432")
                print("   3. Check if Lambda is in the same VPC as RDS (if using Lambda)")
                print("   4. Verify subnet routing and NACLs")
            elif "authentication" in error_msg.lower() or "password" in error_msg.lower():
                print("💡 Troubleshooting authentication:")
                print("   1. Verify DB_USERNAME and DB_PASSWORD environment variables")
                print("   2. Check if the user exists in PostgreSQL")
                print("   3. Verify password is correct")
            elif "no such host" in error_msg.lower() or "name resolution" in error_msg.lower():
                print("💡 Troubleshooting DNS/network:")
                print("   1. Check if RDS endpoint is correct")
                print("   2. Verify network connectivity")
                print("   3. Check VPC DNS settings")
            
            raise
        except psycopg2.Error as e:
            print(f"❌ PostgreSQL error: {e}")
            raise
        except Exception as e:
            print(f"❌ General connection error: {e}")
            raise

    def execute_sql_query(self, connection: psycopg2.extensions.connection, query: str, params: tuple = None, fetch: bool = False) -> Optional[List]:
        """Execute a SQL query and optionally fetch results"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                
                if fetch:
                    results = cursor.fetchall()
                    return results
                else:
                    connection.commit()
                    print(f"Query executed successfully: {cursor.rowcount} rows affected")
                    return None
                    
        except psycopg2.Error as e:
            connection.rollback()
            print(f"SQL execution error: {e}")
            raise
        except Exception as e:
            connection.rollback()
            print(f"Error executing SQL: {e}")
            raise

    def create_ecommerce_tables(self, db_instance_identifier: str, use_secrets: bool = False, secret_name: str = None) -> Dict[str, Any]:
        """Create e-commerce related tables in the PostgreSQL database"""
        
        # Define table creation SQL statements
        tables = {
            'users': '''
                CREATE TABLE IF NOT EXISTS users (
                    user_id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    email VARCHAR(100) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    first_name VARCHAR(50),
                    last_name VARCHAR(50),
                    phone VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                );
            ''',
            
            'categories': '''
                CREATE TABLE IF NOT EXISTS categories (
                    category_id SERIAL PRIMARY KEY,
                    category_name VARCHAR(100) NOT NULL,
                    description TEXT,
                    parent_category_id INTEGER REFERENCES categories(category_id),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                );
            ''',
            
            'products': '''
                CREATE TABLE IF NOT EXISTS products (
                    product_id SERIAL PRIMARY KEY,
                    product_name VARCHAR(200) NOT NULL,
                    description TEXT,
                    price DECIMAL(10, 2) NOT NULL,
                    category_id INTEGER REFERENCES categories(category_id),
                    sku VARCHAR(50) UNIQUE NOT NULL,
                    stock_quantity INTEGER DEFAULT 0,
                    weight DECIMAL(8, 2),
                    dimensions JSONB,
                    images JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT TRUE
                );
            ''',
            
            'addresses': '''
                CREATE TABLE IF NOT EXISTS addresses (
                    address_id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(user_id),
                    address_type VARCHAR(20) CHECK (address_type IN ('billing', 'shipping')),
                    street_address VARCHAR(200) NOT NULL,
                    city VARCHAR(100) NOT NULL,
                    state VARCHAR(100),
                    postal_code VARCHAR(20),
                    country VARCHAR(100) NOT NULL,
                    is_default BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''',
            
            'shopping_carts': '''
                CREATE TABLE IF NOT EXISTS shopping_carts (
                    cart_id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(user_id),
                    session_id VARCHAR(255),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''',
            
            'cart_items': '''
                CREATE TABLE IF NOT EXISTS cart_items (
                    cart_item_id SERIAL PRIMARY KEY,
                    cart_id INTEGER REFERENCES shopping_carts(cart_id) ON DELETE CASCADE,
                    product_id INTEGER REFERENCES products(product_id),
                    quantity INTEGER NOT NULL DEFAULT 1,
                    price DECIMAL(10, 2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(cart_id, product_id)
                );
            ''',
            
            'orders': '''
                CREATE TABLE IF NOT EXISTS orders (
                    order_id SERIAL PRIMARY KEY,
                    user_id INTEGER REFERENCES users(user_id),
                    order_number VARCHAR(50) UNIQUE NOT NULL,
                    order_status VARCHAR(20) DEFAULT 'pending' 
                        CHECK (order_status IN ('pending', 'confirmed', 'processing', 'shipped', 'delivered', 'cancelled')),
                    total_amount DECIMAL(10, 2) NOT NULL,
                    shipping_address_id INTEGER REFERENCES addresses(address_id),
                    billing_address_id INTEGER REFERENCES addresses(address_id),
                    payment_method VARCHAR(50),
                    payment_status VARCHAR(20) DEFAULT 'pending'
                        CHECK (payment_status IN ('pending', 'paid', 'failed', 'refunded')),
                    shipping_cost DECIMAL(10, 2) DEFAULT 0,
                    tax_amount DECIMAL(10, 2) DEFAULT 0,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''',
            
            'order_items': '''
                CREATE TABLE IF NOT EXISTS order_items (
                    order_item_id SERIAL PRIMARY KEY,
                    order_id INTEGER REFERENCES orders(order_id) ON DELETE CASCADE,
                    product_id INTEGER REFERENCES products(product_id),
                    quantity INTEGER NOT NULL,
                    unit_price DECIMAL(10, 2) NOT NULL,
                    total_price DECIMAL(10, 2) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            ''',
            
            'reviews': '''
                CREATE TABLE IF NOT EXISTS reviews (
                    review_id SERIAL PRIMARY KEY,
                    product_id INTEGER REFERENCES products(product_id) ON DELETE CASCADE,
                    user_id INTEGER REFERENCES users(user_id),
                    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
                    title VARCHAR(200),
                    comment TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(product_id, user_id)
                );
            '''
        }
        
        try:
            # Connect to database
            connection = self.connect_to_database(db_instance_identifier, use_secrets, secret_name)
            
            created_tables = []
            errors = []
            
            # Create tables in order (respecting foreign key dependencies)
            table_order = ['users', 'categories', 'products', 'addresses', 'shopping_carts', 'cart_items', 'orders', 'order_items', 'reviews']
            
            for table_name in table_order:
                try:
                    print(f"Creating table: {table_name}")
                    self.execute_sql_query(connection, tables[table_name])
                    created_tables.append(table_name)
                    print(f"✅ Table '{table_name}' created successfully")
                except Exception as e:
                    error_msg = f"❌ Error creating table '{table_name}': {e}"
                    print(error_msg)
                    errors.append(error_msg)
            
            # Create indexes for better performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_products_category ON products(category_id);",
                "CREATE INDEX IF NOT EXISTS idx_products_sku ON products(sku);",
                "CREATE INDEX IF NOT EXISTS idx_orders_user ON orders(user_id);",
                "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(order_status);",
                "CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);",
                "CREATE INDEX IF NOT EXISTS idx_cart_items_cart ON cart_items(cart_id);",
                "CREATE INDEX IF NOT EXISTS idx_reviews_product ON reviews(product_id);",
                "CREATE INDEX IF NOT EXISTS idx_addresses_user ON addresses(user_id);"
            ]
            
            print("\nCreating indexes...")
            for index_sql in indexes:
                try:
                    self.execute_sql_query(connection, index_sql)
                except Exception as e:
                    print(f"Warning: Index creation failed: {e}")
            
            connection.close()
            
            return {
                'success': len(errors) == 0,
                'created_tables': created_tables,
                'errors': errors,
                'total_tables': len(table_order)
            }
            
        except Exception as e:
            print(f"Error in create_ecommerce_tables: {e}")
            raise

    def create_custom_table(self, db_instance_identifier: str, table_name: str, table_schema: str, use_secrets: bool = False, secret_name: str = None) -> bool:
        """Create a custom table with provided schema"""
        try:
            connection = self.connect_to_database(db_instance_identifier, use_secrets, secret_name)
            
            # Add IF NOT EXISTS to the schema if not present
            if "IF NOT EXISTS" not in table_schema.upper():
                table_schema = table_schema.replace(f"CREATE TABLE {table_name}", f"CREATE TABLE IF NOT EXISTS {table_name}")
            
            self.execute_sql_query(connection, table_schema)
            connection.close()
            
            print(f"✅ Custom table '{table_name}' created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error creating custom table '{table_name}': {e}")
            return False

    def insert_sample_data(self, db_instance_identifier: str, use_secrets: bool = False, secret_name: str = None) -> Dict[str, Any]:
        """Insert sample data into the e-commerce tables"""
        
        sample_data = {
            'categories': [
                "INSERT INTO categories (category_name, description) VALUES ('Electronics', 'Electronic devices and gadgets') ON CONFLICT DO NOTHING;",
                "INSERT INTO categories (category_name, description) VALUES ('Clothing', 'Apparel and fashion items') ON CONFLICT DO NOTHING;",
                "INSERT INTO categories (category_name, description) VALUES ('Books', 'Books and literature') ON CONFLICT DO NOTHING;"
            ],
            
            'users': [
                "INSERT INTO users (username, email, password_hash, first_name, last_name) VALUES ('johndoe', 'john@example.com', 'hashed_password_123', 'John', 'Doe') ON CONFLICT DO NOTHING;",
                "INSERT INTO users (username, email, password_hash, first_name, last_name) VALUES ('janesmith', 'jane@example.com', 'hashed_password_456', 'Jane', 'Smith') ON CONFLICT DO NOTHING;"
            ],
            
            'products': [
                "INSERT INTO products (product_name, description, price, category_id, sku, stock_quantity) VALUES ('Smartphone', 'Latest smartphone with advanced features', 599.99, 1, 'PHONE001', 50) ON CONFLICT DO NOTHING;",
                "INSERT INTO products (product_name, description, price, category_id, sku, stock_quantity) VALUES ('T-Shirt', 'Comfortable cotton t-shirt', 29.99, 2, 'SHIRT001', 100) ON CONFLICT DO NOTHING;",
                "INSERT INTO products (product_name, description, price, category_id, sku, stock_quantity) VALUES ('Programming Book', 'Learn programming fundamentals', 49.99, 3, 'BOOK001', 25) ON CONFLICT DO NOTHING;"
            ]
        }
        
        try:
            connection = self.connect_to_database(db_instance_identifier, use_secrets, secret_name)
            
            inserted_data = {}
            errors = []
            
            for table, queries in sample_data.items():
                inserted_data[table] = 0
                for query in queries:
                    try:
                        self.execute_sql_query(connection, query)
                        inserted_data[table] += 1
                    except Exception as e:
                        error_msg = f"Error inserting into {table}: {e}"
                        print(error_msg)
                        errors.append(error_msg)
            
            connection.close()
            
            return {
                'success': len(errors) == 0,
                'inserted_data': inserted_data,
                'errors': errors
            }
            
        except Exception as e:
            print(f"Error inserting sample data: {e}")
            raise


# AWS Lambda Handler Functions
def lambda_create_tables(event, context):
    """
    AWS Lambda handler to create e-commerce tables
    
    Expected event structure:
    {
        "db_instance_identifier": "mypostgresdb",
        "use_secrets": false,
        "secret_name": "optional-secret-name"
    }
    """
    try:
        db_instance_identifier = event.get('db_instance_identifier')
        use_secrets = event.get('use_secrets', False)
        secret_name = event.get('secret_name')
        
        if not db_instance_identifier:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'db_instance_identifier is required'
                })
            }
        
        rds_ops = RDSOperations()
        result = rds_ops.create_ecommerce_tables(db_instance_identifier, use_secrets, secret_name)
        
        return {
            'statusCode': 200 if result['success'] else 500,
            'body': json.dumps({
                'message': 'Table creation completed',
                'result': result
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to create tables'
            })
        }


def lambda_insert_sample_data(event, context):
    """
    AWS Lambda handler to insert sample data
    
    Expected event structure:
    {
        "db_instance_identifier": "mypostgresdb",
        "use_secrets": false,
        "secret_name": "optional-secret-name"
    }
    """
    try:
        db_instance_identifier = event.get('db_instance_identifier')
        use_secrets = event.get('use_secrets', False)
        secret_name = event.get('secret_name')
        
        if not db_instance_identifier:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'db_instance_identifier is required'
                })
            }
        
        rds_ops = RDSOperations()
        result = rds_ops.insert_sample_data(db_instance_identifier, use_secrets, secret_name)
        
        return {
            'statusCode': 200 if result['success'] else 500,
            'body': json.dumps({
                'message': 'Sample data insertion completed',
                'result': result
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to insert sample data'
            })
        }


def lambda_create_custom_table(event, context):
    """
    AWS Lambda handler to create a custom table
    
    Expected event structure:
    {
        "db_instance_identifier": "mypostgresdb",
        "table_name": "custom_table",
        "table_schema": "CREATE TABLE custom_table (id SERIAL PRIMARY KEY, name VARCHAR(100));",
        "use_secrets": false,
        "secret_name": "optional-secret-name"
    }
    """
    try:
        db_instance_identifier = event.get('db_instance_identifier')
        table_name = event.get('table_name')
        table_schema = event.get('table_schema')
        use_secrets = event.get('use_secrets', False)
        secret_name = event.get('secret_name')
        
        if not all([db_instance_identifier, table_name, table_schema]):
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'db_instance_identifier, table_name, and table_schema are required'
                })
            }
        
        rds_ops = RDSOperations()
        success = rds_ops.create_custom_table(db_instance_identifier, table_name, table_schema, use_secrets, secret_name)
        
        return {
            'statusCode': 200 if success else 500,
            'body': json.dumps({
                'message': f'Custom table {table_name} {"created successfully" if success else "creation failed"}',
                'success': success
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to create custom table'
            })
        }


def lambda_execute_query(event, context):
    """
    AWS Lambda handler to execute custom SQL queries
    
    Expected event structure:
    {
        "db_instance_identifier": "mypostgresdb",
        "query": "SELECT * FROM users LIMIT 10;",
        "fetch": true,
        "use_secrets": false,
        "secret_name": "optional-secret-name"
    }
    """
    try:
        db_instance_identifier = event.get('db_instance_identifier')
        query = event.get('query')
        fetch = event.get('fetch', False)
        use_secrets = event.get('use_secrets', False)
        secret_name = event.get('secret_name')
        
        if not all([db_instance_identifier, query]):
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'db_instance_identifier and query are required'
                })
            }
        
        rds_ops = RDSOperations()
        connection = rds_ops.connect_to_database(db_instance_identifier, use_secrets, secret_name)
        
        result = rds_ops.execute_sql_query(connection, query, fetch=fetch)
        connection.close()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Query executed successfully',
                'result': result if fetch else 'Query executed (no results returned)',
                'rows_returned': len(result) if fetch and result else 0
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to execute query'
            })
        }


# Local testing and example usage
if __name__ == "__main__":
    import sys
    
    # Example usage for local testing
    rds_ops = RDSOperations()
    
    # Set your database instance identifier
    db_instance_identifier = "my-ecommerce-db"
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "status":
            print("🔍 Checking RDS instance status...")
            status = rds_ops.check_rds_instance_status(db_instance_identifier)
            
            if 'error' in status:
                print(f"❌ {status['error']}")
            else:
                print(f"📋 RDS Instance Details:")
                for key, value in status.items():
                    if key == 'endpoint' and value:
                        print(f"   {key}: {value['address']}:{value['port']}")
                    else:
                        print(f"   {key}: {value}")
                        
        elif command == "wait":
            print("⏳ Waiting for RDS instance to become available...")
            if rds_ops.wait_for_rds_available(db_instance_identifier):
                print("✅ RDS instance is ready!")
            else:
                print("❌ RDS instance is not ready")
                
        elif command == "test-connection":
            print("🔌 Testing database connection...")
            try:
                connection = rds_ops.connect_to_database(db_instance_identifier)
                connection.close()
                print("✅ Connection test successful!")
            except Exception as e:
                print(f"❌ Connection test failed: {e}")
                
        elif command == "create":
            print("🏗️ Creating e-commerce tables...")
            try:
                # First check if RDS is available
                status = rds_ops.check_rds_instance_status(db_instance_identifier)
                if 'error' in status:
                    print(f"❌ {status['error']}")
                    sys.exit(1)
                
                if status['status'] != 'available':
                    print(f"⚠️ RDS instance status: {status['status']}")
                    print("Waiting for instance to become available...")
                    if not rds_ops.wait_for_rds_available(db_instance_identifier):
                        print("❌ Cannot proceed - RDS instance not available")
                        sys.exit(1)
                
                result = rds_ops.create_ecommerce_tables(db_instance_identifier)
                print(f"📊 Result: {result}")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                
        elif command == "sample":
            print("📝 Inserting sample data...")
            try:
                # First check if RDS is available
                status = rds_ops.check_rds_instance_status(db_instance_identifier)
                if 'error' in status:
                    print(f"❌ {status['error']}")
                    sys.exit(1)
                
                if status['status'] != 'available':
                    print(f"⚠️ RDS instance status: {status['status']}")
                    print("Waiting for instance to become available...")
                    if not rds_ops.wait_for_rds_available(db_instance_identifier):
                        print("❌ Cannot proceed - RDS instance not available")
                        sys.exit(1)
                
                result = rds_ops.insert_sample_data(db_instance_identifier)
                print(f"📊 Result: {result}")
                
            except Exception as e:
                print(f"❌ Error: {e}")
                
        else:
            print(f"❌ Unknown command: {command}")
            
    else:
        print("🚀 RDS Operations Tool")
        print("Usage:")
        print("  python rds_operations.py status          # Check RDS instance status")
        print("  python rds_operations.py wait            # Wait for RDS to become available")
        print("  python rds_operations.py test-connection # Test database connection")
        print("  python rds_operations.py create          # Create tables")
        print("  python rds_operations.py sample          # Insert sample data")
        print("\n🔧 Or use as Lambda functions:")
        print("  lambda_create_tables")
        print("  lambda_insert_sample_data")
        print("  lambda_create_custom_table")
        print("  lambda_execute_query")

