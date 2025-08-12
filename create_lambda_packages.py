#!/usr/bin/env python3
"""
Create AWS Lambda deployment packages
"""

import os
import shutil
import zipfile
import subprocess

def create_lambda_package(function_name, files_to_include):
    """Create a Lambda deployment package"""
    
    package_dir = f"lambda_packages/{function_name}"
    zip_file = f"lambda_packages/{function_name}.zip"
    
    # Create package directory
    os.makedirs(package_dir, exist_ok=True)
    os.makedirs("lambda_packages", exist_ok=True)
    
    print(f"📦 Creating Lambda package for {function_name}...")
    
    # Copy files
    for file_path in files_to_include:
        if os.path.exists(file_path):
            shutil.copy2(file_path, package_dir)
            print(f"   ✅ Added {file_path}")
        else:
            print(f"   ❌ File not found: {file_path}")
    
    # Install dependencies
    print("   📥 Installing dependencies...")
    subprocess.run([
        "pip", "install", 
        "-r", "requirements.txt", 
        "-t", package_dir,
        "--no-deps"  # Only install direct dependencies
    ], check=True)
    
    # Create ZIP file
    print(f"   🗜️ Creating {zip_file}...")
    with zipfile.ZipFile(zip_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(package_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, package_dir)
                zipf.write(file_path, arcname)
    
    # Clean up temp directory
    shutil.rmtree(package_dir)
    
    print(f"✅ Lambda package created: {zip_file}")
    print(f"📏 Package size: {os.path.getsize(zip_file) / 1024 / 1024:.2f} MB")
    
    return zip_file

def create_all_packages():
    """Create all Lambda packages"""
    
    packages = {
        "rds_operations": [
            "lambda/rds_operations.py"
        ],
        "rds_setup": [
            "lambda/create_rds.py",
            "lambda/create_vpc.py",
            "lambda/rds_operations.py"
        ]
    }
    
    created_packages = []
    
    for package_name, files in packages.items():
        try:
            zip_file = create_lambda_package(package_name, files)
            created_packages.append(zip_file)
        except Exception as e:
            print(f"❌ Failed to create {package_name}: {e}")
    
    return created_packages

if __name__ == "__main__":
    print("🚀 Creating AWS Lambda deployment packages...")
    
    # Change to project root
    os.chdir("/home/hxnguyen/cloudProjects/serverless-e-commerce")
    
    packages = create_all_packages()
    
    print(f"\n✅ Created {len(packages)} packages:")
    for package in packages:
        print(f"   📦 {package}")
    
    print("\n📋 Next steps:")
    print("1. Upload the ZIP files to AWS Lambda")
    print("2. Set environment variables in Lambda:")
    print("   - DB_USERNAME=dbuser")
    print("   - DB_PASSWORD=YourSecurePassword123!")
    print("3. Configure Lambda with appropriate IAM roles for RDS access")
    print("4. Set up VPC configuration for Lambda to access RDS")
