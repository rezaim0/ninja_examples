# test_integration.py
"""
Integration test for database repository, S3 repository, and model review checker.

This test script verifies that all components work together correctly by:
1. Testing database repository configuration and queries
2. Testing S3 repository file access  
3. Testing model review checker coordination
4. Running end-to-end model review process

Run this script to validate your database repository changes.
"""
import logging
import sys
from typing import Dict, Any
from datetime import datetime

# Import your modules
from database_repository import ModelDatabaseRepository, create_database_repository
from s3_file_repository import ModelFileRepository, create_s3_repository
from model_review import ModelReviewChecker, create_model_review_checker

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_repository():
    """Test the database repository configuration and basic operations."""
    print("\n" + "="*60)
    print("🔧 TESTING DATABASE REPOSITORY")
    print("="*60)
    
    try:
        # Test 1: Create repository with config key (recommended approach)
        print("\n1. Testing repository creation with config key 'output'...")
        repo = create_database_repository("output")
        
        # Check configuration
        env_info = repo.get_environment_info()
        print(f"   ✅ Environment: {env_info['environment']}")
        print(f"   ✅ Database: {env_info['database']}")
        print(f"   ✅ Schema: {env_info['schema']}")
        print(f"   ✅ Table: {env_info['table_name']}")
        print(f"   ✅ Full table name: {env_info['full_table_name']}")
        print(f"   ✅ Available tables: {env_info['available_tables']}")
        
        # Test 2: Health check
        print("\n2. Testing database health check...")
        is_healthy = repo.health_check()
        if is_healthy:
            print("   ✅ Database connection successful")
        else:
            print("   ❌ Database connection failed")
            return False
        
        # Test 3: Try to get model review dates
        print("\n3. Testing model review dates query...")
        review_dates = repo.get_model_review_dates()
        
        if review_dates is not None:
            print(f"   ✅ Successfully retrieved review dates for {len(review_dates)} models")
            
            # Show first few examples
            count = 0
            for model_name, review_date in review_dates.items():
                if count < 3:  # Show first 3 examples
                    print(f"      - {model_name}: {review_date}")
                    count += 1
                else:
                    break
            
            if len(review_dates) > 3:
                print(f"      ... and {len(review_dates) - 3} more models")
        else:
            print("   ⚠️  No review dates found (this might be expected if table is empty)")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Database repository test failed: {e}")
        logger.exception("Database repository test error:")
        return False

def test_s3_repository(bucket_name: str, bucket_prefix: str = ""):
    """Test the S3 repository file operations."""
    print("\n" + "="*60)
    print("🔧 TESTING S3 FILE REPOSITORY") 
    print("="*60)
    
    try:
        # Test 1: Create S3 repository
        print(f"\n1. Testing S3 repository creation...")
        print(f"   Bucket: {bucket_name}")
        print(f"   Prefix: {bucket_prefix or '(none)'}")
        
        repo = create_s3_repository(bucket_name, bucket_prefix)
        
        # Test 2: Health check
        print("\n2. Testing S3 health check...")
        is_healthy = repo.health_check()
        if is_healthy:
            print("   ✅ S3 connection successful")
        else:
            print("   ❌ S3 connection failed")
            return False, None
        
        # Test 3: Get latest model paths
        print("\n3. Testing latest model paths retrieval...")
        model_paths = repo.get_latest_model_paths()
        
        if model_paths:
            print(f"   ✅ Found {len(model_paths)} latest model files")
            
            # Show first few examples
            count = 0
            for model_name, s3_path in model_paths.items():
                if count < 3:
                    print(f"      - {model_name}: {s3_path}")
                    count += 1
                else:
                    break
            
            if len(model_paths) > 3:
                print(f"      ... and {len(model_paths) - 3} more models")
        else:
            print("   ⚠️  No model files found")
            return True, None  # Not necessarily an error
        
        # Test 4: Get AAP group IDs (only if we have model paths)
        if model_paths:
            print("\n4. Testing AAP group ID extraction...")
            
            # Test with just first few models to avoid long processing time
            sample_paths = dict(list(model_paths.items())[:3])
            aap_groups = repo.get_models_by_aap_group_id(sample_paths)
            
            if aap_groups:
                print(f"   ✅ Successfully extracted AAP group IDs for {len(aap_groups)} models")
                for model_name, aap_id in aap_groups.items():
                    print(f"      - {model_name}: {aap_id}")
            else:
                print("   ⚠️  No AAP group IDs found in sample models")
        
        return True, model_paths
        
    except Exception as e:
        print(f"   ❌ S3 repository test failed: {e}")
        logger.exception("S3 repository test error:")
        return False, None

def test_model_review_checker(bucket_name: str, bucket_prefix: str = ""):
    """Test the model review checker integration."""
    print("\n" + "="*60)
    print("🔧 TESTING MODEL REVIEW CHECKER")
    print("="*60)
    
    try:
        # Test 1: Create model review checker
        print("\n1. Testing model review checker creation...")
        checker = create_model_review_checker(
            bucket_name=bucket_name,
            bucket_prefix=bucket_prefix,
            table_name="output"  # Use config key
        )
        print("   ✅ Model review checker created successfully")
        
        # Test 2: Run the full review process
        print("\n2. Testing complete model review process...")
        models_needing_review = checker.check_models_due_for_review()
        
        if models_needing_review:
            print(f"   ✅ Found {len(models_needing_review)} models needing review")
            
            # Show details for first few models
            count = 0
            for model_name, metadata in models_needing_review.items():
                if count < 3:
                    print(f"      - {model_name}:")
                    print(f"        Review date: {metadata.get('review_date')}")
                    print(f"        Days overdue: {metadata.get('days_overdue')}")
                    print(f"        AAP group: {metadata.get('app_group_id')}")
                    print(f"        Model path: {metadata.get('model_path', 'N/A')}")
                    count += 1
                else:
                    break
            
            if len(models_needing_review) > 3:
                print(f"      ... and {len(models_needing_review) - 3} more models")
                
        else:
            print("   ✅ No models currently need review (or none found)")
        
        return True, models_needing_review
        
    except Exception as e:
        print(f"   ❌ Model review checker test failed: {e}")
        logger.exception("Model review checker test error:")
        return False, None

def run_integration_test(bucket_name: str, bucket_prefix: str = ""):
    """Run complete integration test of all components."""
    print("🚀 STARTING INTEGRATION TEST")
    print(f"📅 Test started at: {datetime.now()}")
    print(f"🪣 S3 Bucket: {bucket_name}")
    print(f"📁 S3 Prefix: {bucket_prefix or '(none)'}")
    
    results = {
        'database_test': False,
        's3_test': False, 
        'model_review_test': False,
        'overall_success': False
    }
    
    try:
        # Test 1: Database Repository
        results['database_test'] = test_database_repository()
        
        # Test 2: S3 Repository  
        s3_success, model_paths = test_s3_repository(bucket_name, bucket_prefix)
        results['s3_test'] = s3_success
        
        # Test 3: Model Review Checker (only if previous tests passed)
        if results['database_test'] and results['s3_test']:
            review_success, models_needing_review = test_model_review_checker(bucket_name, bucket_prefix)
            results['model_review_test'] = review_success
        else:
            print("\n⚠️  Skipping model review test due to previous failures")
        
        # Overall result
        results['overall_success'] = all([
            results['database_test'],
            results['s3_test'], 
            results['model_review_test']
        ])
        
    except Exception as e:
        print(f"\n❌ Integration test failed with error: {e}")
        logger.exception("Integration test error:")
    
    # Print summary
    print("\n" + "="*60)
    print("📊 INTEGRATION TEST SUMMARY")
    print("="*60)
    print(f"Database Repository: {'✅ PASS' if results['database_test'] else '❌ FAIL'}")
    print(f"S3 File Repository:  {'✅ PASS' if results['s3_test'] else '❌ FAIL'}")
    print(f"Model Review Checker: {'✅ PASS' if results['model_review_test'] else '❌ FAIL'}")
    print(f"Overall Result:      {'✅ PASS' if results['overall_success'] else '❌ FAIL'}")
    print(f"Test completed at:   {datetime.now()}")
    
    return results

if __name__ == "__main__":
    """
    Run the integration test.
    
    Usage:
        python test_integration.py
        
    Or modify the parameters below for your specific S3 setup.
    """
    
    # 🔧 CONFIGURE YOUR TEST PARAMETERS HERE
    TEST_BUCKET_NAME = "your-model-bucket-name"  # Replace with your actual bucket
    TEST_BUCKET_PREFIX = ""  # Replace with your S3 prefix if any
    
    # Check if bucket name was updated
    if TEST_BUCKET_NAME == "your-model-bucket-name":
        print("❌ Please update TEST_BUCKET_NAME in the script with your actual S3 bucket name")
        sys.exit(1)
    
    # Run the test
    results = run_integration_test(TEST_BUCKET_NAME, TEST_BUCKET_PREFIX)
    
    # Exit with appropriate code
    sys.exit(0 if results['overall_success'] else 1)