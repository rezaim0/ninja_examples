# test_integration.py
"""
Comprehensive integration tests for the notification system.

Tests the complete workflow from database/S3 → model review → notifications → JSON output.
Uses pytest fixtures, parameterization, and mocking to test various scenarios and edge cases.

Run with: pytest test_integration.py -v
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any, Optional
import pandas as pd

# Import your modules
from database_repository import ModelDatabaseRepository, DatabaseConfig
from s3_file_repository import ModelFileRepository
from model_review import ModelReviewChecker
from notification_strategy import ModelReviewNotification, PerformanceDegradationNotification
from notification_factory import NotificationFactory
from notification_delivery import NotificationDelivery
from notification_manager import NotificationManager, create_notification_manager
from config import Environment

# Test Data Fixtures
@pytest.fixture
def sample_review_dates():
    """Sample model review dates for testing."""
    base_date = datetime.now()
    return {
        'model_current': (base_date - timedelta(days=30)).strftime('%Y-%m-%d'),      # Current
        'model_overdue': (base_date - timedelta(days=200)).strftime('%Y-%m-%d'),     # Overdue
        'model_critical': (base_date - timedelta(days=300)).strftime('%Y-%m-%d'),    # Critical
        'model_recent': (base_date - timedelta(days=10)).strftime('%Y-%m-%d'),       # Recent
        'model_invalid_date': 'invalid-date',                                        # Invalid
        'model_empty_date': '',                                                      # Empty
    }

@pytest.fixture
def sample_model_paths():
    """Sample S3 model file paths."""
    return {
        'model_overdue': 's3://bucket/models/docato_model_overdue_20240601_120000.pkl',
        'model_critical': 's3://bucket/models/docato_model_critical_20240301_120000.pkl',
        'model_current': 's3://bucket/models/docato_model_current_20241101_120000.pkl',
        'model_recent': 's3://bucket/models/docato_model_recent_20241220_120000.pkl',
    }

@pytest.fixture
def sample_aap_groups():
    """Sample AAP group mappings."""
    return {
        'model_overdue': 'group_finance',
        'model_critical': 'group_risk',
        'model_current': 'group_marketing',
        'model_recent': 'group_operations',
        'model_invalid_date': 'group_test',
        'model_empty_date': 'group_empty',
    }

@pytest.fixture
def temp_output_dir():
    """Temporary directory for test output files."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)

@pytest.fixture
def mock_db_config():
    """Mock database configuration."""
    return DatabaseConfig(
        environment=Environment.DEV,
        database="test_db",
        schema="test_schema",
        table_names={"output": "test_modelops_output"}
    )

@pytest.fixture
def mock_database_repo(mock_db_config, sample_review_dates):
    """Mock database repository with test data."""
    repo = Mock(spec=ModelDatabaseRepository)
    repo.get_model_review_dates.return_value = sample_review_dates
    repo.get_environment_info.return_value = {
        'environment': 'DEV',
        'database': 'test_db',
        'schema': 'test_schema',
        'table_name': 'test_modelops_output',
        'full_table_name': 'test_schema.test_modelops_output'
    }
    repo.health_check.return_value = True
    return repo

@pytest.fixture
def mock_s3_repo(sample_model_paths, sample_aap_groups):
    """Mock S3 repository with test data."""
    repo = Mock(spec=ModelFileRepository)
    repo.get_latest_model_paths.return_value = sample_model_paths
    repo.get_models_by_aap_group_id.return_value = sample_aap_groups
    repo.health_check.return_value = True
    return repo

@pytest.fixture
def mock_model_checker(mock_database_repo, mock_s3_repo):
    """Mock model review checker with realistic behavior."""
    checker = Mock(spec=ModelReviewChecker)
    
    # Simulate models needing review (overdue models only)
    models_needing_review = {
        'model_overdue': {
            'review_date': '2024-06-01',
            'app_group_id': 'group_finance',
            'model_path': 's3://bucket/models/docato_model_overdue_20240601_120000.pkl',
            'days_overdue': 200,
            'review_interval_days': 180,
            'notification_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        },
        'model_critical': {
            'review_date': '2024-03-01',
            'app_group_id': 'group_risk',
            'model_path': 's3://bucket/models/docato_model_critical_20240301_120000.pkl',
            'days_overdue': 300,
            'review_interval_days': 180,
            'notification_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    }
    
    checker.check_models_due_for_review.return_value = models_needing_review
    return checker

# Test Classes
class TestDatabaseRepository:
    """Test database repository functionality."""
    
    @pytest.mark.parametrize("table_name,expected_key", [
        ("output", "output"),
        ("modelops_docato_output", "modelops_docato_output"),
        ("unknown_table", "unknown_table"),
    ])
    def test_table_name_resolution(self, table_name, expected_key):
        """Test table name resolution with different inputs."""
        with patch('database_repository.get_db_config') as mock_config:
            mock_config.return_value = Mock(
                environment=Environment.DEV,
                database="test_db",
                schema="test_schema",
                table_names={"output": "kfp123_modelops_docato_output"}
            )
            
            repo = ModelDatabaseRepository(table_name)
            
            if table_name == "output":
                assert repo.table_name == "kfp123_modelops_docato_output"
            else:
                assert repo.table_name == table_name

    def test_full_table_name_building(self):
        """Test full table name construction."""
        with patch('database_repository.get_db_config') as mock_config:
            mock_config.return_value = Mock(
                environment=Environment.DEV,
                database="edw",
                schema="ptap",
                table_names={"output": "kfp123_modelops_docato_output"}
            )
            
            repo = ModelDatabaseRepository("output")
            assert repo.full_table_name == "ptap.kfp123_modelops_docato_output"

    def test_review_dates_processing(self, mock_database_repo):
        """Test review dates retrieval and processing."""
        review_dates = mock_database_repo.get_model_review_dates()
        
        assert len(review_dates) == 6
        assert 'model_overdue' in review_dates
        assert 'model_current' in review_dates
        assert review_dates['model_invalid_date'] == 'invalid-date'

class TestS3Repository:
    """Test S3 repository functionality."""
    
    @pytest.mark.parametrize("file_count,expected_result", [
        (0, None),           # No files
        (5, True),           # Normal case
        (1000, True),        # Large number of files
    ])
    def test_model_paths_scenarios(self, file_count, expected_result):
        """Test different scenarios for model path retrieval."""
        mock_repo = Mock(spec=ModelFileRepository)
        
        if file_count == 0:
            mock_repo.get_latest_model_paths.return_value = None
        else:
            paths = {f'model_{i}': f's3://bucket/model_{i}.pkl' for i in range(file_count)}
            mock_repo.get_latest_model_paths.return_value = paths
        
        result = mock_repo.get_latest_model_paths()
        
        if expected_result is None:
            assert result is None
        else:
            assert result is not None
            assert len(result) == file_count

    def test_aap_group_extraction_edge_cases(self):
        """Test AAP group ID extraction with edge cases."""
        mock_repo = Mock(spec=ModelFileRepository)
        
        # Test various scenarios
        test_cases = [
            ({'model_a': 'path_a'}, {'model_a': 'group_a'}),           # Normal case
            ({'model_b': 'path_b'}, {}),                              # No AAP groups found
            ({}, None),                                               # No model paths
        ]
        
        for model_paths, expected in test_cases:
            mock_repo.get_models_by_aap_group_id.return_value = expected
            result = mock_repo.get_models_by_aap_group_id(model_paths)
            assert result == expected

class TestModelReviewChecker:
    """Test model review checker business logic."""
    
    @pytest.mark.parametrize("days_overdue,should_need_review", [
        (10, False),          # Recent review
        (185, True),          # Just overdue
        (300, True),          # Very overdue
        (0, False),           # Today
        (-1, False),          # Future date (edge case)
    ])
    def test_review_requirement_logic(self, days_overdue, should_need_review):
        """Test business logic for determining review requirements."""
        checker = ModelReviewChecker(Mock(), Mock())
        
        # Calculate review date based on days overdue
        review_date = datetime.now() - timedelta(days=days_overdue)
        review_date_str = review_date.strftime('%Y-%m-%d')
        
        result = checker._is_review_required(review_date_str)
        assert result == should_need_review

    def test_integration_with_repositories(self, mock_database_repo, mock_s3_repo):
        """Test integration between database and S3 repositories."""
        checker = ModelReviewChecker(mock_database_repo, mock_s3_repo)
        
        # Mock the repository responses
        mock_database_repo.get_model_review_dates.return_value = {
            'model_overdue': '2024-06-01',
            'model_current': '2024-11-01'
        }
        
        mock_s3_repo.get_latest_model_paths.return_value = {
            'model_overdue': 's3://bucket/model_overdue.pkl'
        }
        
        mock_s3_repo.get_models_by_aap_group_id.return_value = {
            'model_overdue': 'group_finance'
        }
        
        # Test the integration
        with patch.object(checker, '_is_review_required', return_value=True):
            result = checker.check_models_due_for_review()
            
            assert result is not None
            assert 'model_overdue' in result
            assert result['model_overdue']['app_group_id'] == 'group_finance'

class TestNotificationStrategies:
    """Test notification strategy implementations."""
    
    @pytest.mark.parametrize("strategy_class,notification_type", [
        (ModelReviewNotification, "model_review"),
        (PerformanceDegradationNotification, "performance_degradation"),
    ])
    def test_strategy_implementations(self, strategy_class, notification_type):
        """Test different notification strategy implementations."""
        strategy = strategy_class()
        
        metadata = {
            'review_date': '2024-06-01',
            'days_overdue': 185,
            'model_path': 's3://bucket/test_model.pkl'
        }
        
        content = strategy.create_notification_content(
            "test_model", "test_group", metadata
        )
        
        assert strategy.get_notification_type() == notification_type
        assert "test_model" in content
        assert "test_group" in content
        assert len(content) > 100  # Ensure substantial content

    def test_html_content_generation(self):
        """Test HTML content generation in model review strategy."""
        strategy = ModelReviewNotification()
        
        metadata = {
            'review_date': '2024-06-01',
            'days_overdue': 185,
            'model_path': 's3://bucket/test_model.pkl',
            'review_interval_days': 180
        }
        
        content = strategy.create_notification_content(
            "test_model", "test_group", metadata
        )
        
        # Verify HTML structure
        assert content.startswith('<!DOCTYPE html>')
        assert '<html' in content
        assert '</html>' in content
        assert 'test_model' in content
        assert 'test_group' in content
        assert '185' in content  # Days overdue

class TestNotificationFactory:
    """Test notification factory functionality."""
    
    def test_factory_registration_and_creation(self):
        """Test strategy registration and creation."""
        factory = NotificationFactory()
        
        # Test built-in strategies
        strategy = factory.create_notification("model_review")
        assert strategy is not None
        assert isinstance(strategy, ModelReviewNotification)
        
        # Test unknown strategy
        unknown_strategy = factory.create_notification("unknown_type")
        assert unknown_strategy is None

    def test_factory_methods(self):
        """Test factory utility methods."""
        factory = NotificationFactory()
        
        registered_types = factory.get_registered_types()
        assert "model_review" in registered_types
        assert "performance_degradation" in registered_types
        
        assert factory.is_registered("model_review") is True
        assert factory.is_registered("unknown_type") is False

class TestNotificationDelivery:
    """Test notification delivery (JSON file generation)."""
    
    def test_json_file_generation(self, temp_output_dir):
        """Test JSON file creation and content."""
        delivery = NotificationDelivery(str(temp_output_dir))
        
        success = delivery.send(
            aap_group_id="test_group",
            subject="Test Subject",
            content="<html><body>Test Content</body></html>",
            model_name="test_model",
            notification_type="model_review",
            metadata={"key": "value"}
        )
        
        assert success is True
        
        # Check file was created
        files = delivery.get_generated_files()
        assert len(files) == 1
        
        # Verify file content
        with open(files[0], 'r') as f:
            data = json.load(f)
        
        assert data['aap_group_id'] == "test_group"
        assert data['email_subject'] == "Test Subject"
        assert data['model_name'] == "test_model"
        assert data['notification_type'] == "model_review"
        assert data['metadata']['key'] == "value"

    @pytest.mark.parametrize("aap_group_id,expected_success", [
        ("valid_group", True),
        ("", False),              # Empty group ID
        (None, False),            # None group ID
        ("group with spaces", True),  # Spaces (should be sanitized)
        ("group/with\\chars", True),  # Special chars (should be sanitized)
    ])
    def test_edge_cases_validation(self, temp_output_dir, aap_group_id, expected_success):
        """Test edge cases in delivery validation."""
        delivery = NotificationDelivery(str(temp_output_dir))
        
        success = delivery.send(
            aap_group_id=aap_group_id,
            subject="Test Subject",
            content="Test Content",
            model_name="test_model"
        )
        
        assert success == expected_success

class TestNotificationManager:
    """Test complete notification manager workflow."""
    
    def test_end_to_end_notification_process(self, mock_model_checker, temp_output_dir):
        """Test complete end-to-end notification process."""
        delivery = NotificationDelivery(str(temp_output_dir))
        factory = NotificationFactory()
        manager = NotificationManager(mock_model_checker, delivery, factory)
        
        # Run the notification process
        results = manager.send_model_review_notifications()
        
        # Verify results
        assert results['total_models_checked'] == 2
        assert results['notifications_generated'] == 2
        assert results['json_files_created'] == 2
        assert len(results['errors']) == 0
        
        # Verify files were created
        files = delivery.get_generated_files()
        assert len(files) == 2
        
        # Verify file contents
        for file_path in files:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            assert data['aap_group_id'] in ['group_finance', 'group_risk']
            assert 'Model Review Required' in data['email_subject']
            assert data['notification_type'] == 'model_review'
            assert '<!DOCTYPE html>' in data['email_content']

    def test_error_handling_scenarios(self, temp_output_dir):
        """Test error handling in various failure scenarios."""
        # Test with no models needing review
        mock_checker = Mock()
        mock_checker.check_models_due_for_review.return_value = None
        
        delivery = NotificationDelivery(str(temp_output_dir))
        manager = NotificationManager(mock_checker, delivery)
        
        results = manager.send_model_review_notifications()
        assert results['total_models_checked'] == 0
        assert results['notifications_generated'] == 0

    def test_missing_aap_group_handling(self, temp_output_dir):
        """Test handling of models without AAP group IDs."""
        # Mock checker with model missing AAP group
        mock_checker = Mock()
        mock_checker.check_models_due_for_review.return_value = {
            'model_no_group': {
                'review_date': '2024-06-01',
                'app_group_id': None,  # Missing group
                'model_path': 's3://bucket/model.pkl',
                'days_overdue': 200
            }
        }
        
        delivery = NotificationDelivery(str(temp_output_dir))
        factory = NotificationFactory()
        manager = NotificationManager(mock_checker, delivery, factory)
        
        results = manager.send_model_review_notifications()
        
        assert results['total_models_checked'] == 1
        assert results['notifications_generated'] == 0  # Should skip model without group
        assert results['notifications_failed'] == 1
        assert len(results['failed_notifications']) == 1

class TestSystemIntegration:
    """Integration tests for the complete system."""
    
    @pytest.mark.integration
    def test_create_notification_manager_factory(self, temp_output_dir):
        """Test the factory function for creating notification manager."""
        with patch('model_review.create_model_review_checker') as mock_create:
            mock_checker = Mock()
            mock_create.return_value = mock_checker
            
            manager = create_notification_manager(
                bucket_name="test-bucket",
                bucket_prefix="models/",
                output_directory=str(temp_output_dir)
            )
            
            assert isinstance(manager, NotificationManager)
            mock_create.assert_called_once_with(
                bucket_name="test-bucket",
                bucket_prefix="models/",
                table_name="output"
            )

    @pytest.mark.integration
    def test_notification_workflow_with_realistic_data(self, temp_output_dir):
        """Test complete workflow with realistic data scenarios."""
        # Create realistic test data
        models_data = {
            'fraud_detection_v2': {
                'review_date': '2024-04-01',
                'app_group_id': 'risk_management',
                'model_path': 's3://models/fraud_detection_v2_20240401_120000.pkl',
                'days_overdue': 245,
                'review_interval_days': 180,
                'notification_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'credit_scoring_v3': {
                'review_date': '2024-05-15',
                'app_group_id': 'credit_team',
                'model_path': 's3://models/credit_scoring_v3_20240515_120000.pkl',
                'days_overdue': 200,
                'review_interval_days': 180,
                'notification_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        }
        
        # Mock the checker
        mock_checker = Mock()
        mock_checker.check_models_due_for_review.return_value = models_data
        
        # Create manager and run process
        delivery = NotificationDelivery(str(temp_output_dir))
        factory = NotificationFactory()
        manager = NotificationManager(mock_checker, delivery, factory)
        
        results = manager.send_model_review_notifications()
        
        # Verify results
        assert results['notifications_generated'] == 2
        assert results['json_files_created'] == 2
        
        # Verify realistic content in generated files
        files = delivery.get_generated_files()
        for file_path in files:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Check that content is realistic
            assert data['model_name'] in ['fraud_detection_v2', 'credit_scoring_v3']
            assert data['aap_group_id'] in ['risk_management', 'credit_team']
            assert 'fraud_detection' in data['email_content'] or 'credit_scoring' in data['email_content']
            
            # Verify HTML structure
            html_content = data['email_content']
            assert '<!DOCTYPE html>' in html_content
            assert 'OVERDUE' in html_content or 'CRITICALLY OVERDUE' in html_content

# Performance and Load Tests
class TestPerformance:
    """Test system performance with larger datasets."""
    
    @pytest.mark.performance
    def test_large_dataset_processing(self, temp_output_dir):
        """Test processing large number of models."""
        # Create mock data for 100 models
        large_dataset = {}
        for i in range(100):
            large_dataset[f'model_{i}'] = {
                'review_date': '2024-06-01',
                'app_group_id': f'group_{i % 10}',  # 10 different groups
                'model_path': f's3://bucket/model_{i}.pkl',
                'days_overdue': 200 + i,
                'review_interval_days': 180
            }
        
        mock_checker = Mock()
        mock_checker.check_models_due_for_review.return_value = large_dataset
        
        delivery = NotificationDelivery(str(temp_output_dir))
        factory = NotificationFactory()
        manager = NotificationManager(mock_checker, delivery, factory)
        
        # Measure processing time
        import time
        start_time = time.time()
        results = manager.send_model_review_notifications()
        processing_time = time.time() - start_time
        
        # Verify results
        assert results['notifications_generated'] == 100
        assert results['json_files_created'] == 100
        assert processing_time < 10  # Should complete within 10 seconds
        
        # Verify all files were created
        files = delivery.get_generated_files()
        assert len(files) == 100

# Cleanup utility
@pytest.fixture(autouse=True)
def cleanup_after_tests():
    """Cleanup after each test."""
    yield
    # Any cleanup code can go here if needed