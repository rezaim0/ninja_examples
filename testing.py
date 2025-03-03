import pytest
from unittest.mock import MagicMock, patch

# Mock for the remove_matching_records function
@pytest.fixture
def remove_matching_records_mock():
    with patch('builtins.remove_matching_records') as mock:
        yield mock

# Mock instance of GeneralCRUD for testing
@pytest.fixture
def crud_instance():
    # For testing purposes, we'll create a mock class with the same structure
    class GeneralCRUD:
        def __init__(self, query_compile=False, generate_query=None):
            self.query_compile = query_compile
            self.generate_query = generate_query
            self.con = None
            self.database_config = None
        
        def get_latest_records(self, query):
            pass
            
        def generate_query(self):
            pass
            
        def enddate_output_records(self, records_to_db_enddate):
            pass
            
        def bulk_upload_records_to_db(self, records):
            pass
    
    # Create and configure the mock instance
    crud = GeneralCRUD()
    crud.get_latest_records = MagicMock()
    crud.generate_query = MagicMock()
    crud.enddate_output_records = MagicMock()
    crud.bulk_upload_records_to_db = MagicMock()
    
    # Mock the generate_query.get_table_name method
    crud.generate_query.get_table_name = MagicMock()
    
    return crud

def test_typical_case(crud_instance, remove_matching_records_mock):
    """Test with typical input data that requires both enddate and upload operations."""
    # Setup mock data
    query = "test_query"
    input_records = [
        {"id": 1, "value": "test1", "docato_version": "v1"},
        {"id": 2, "value": "test2", "docato_version": "v2"}
    ]
    
    db_latest_records = [
        {"id": 1, "value": "old_test1", "docato_version": "v0"},
        {"id": 3, "value": "test3", "docato_version": "v1"}
    ]
    
    records_to_enddate = [{"id": 1, "value": "old_test1", "docato_version": "v0"}]
    records_to_upload = [{"id": 2, "value": "test2", "docato_version": "v2"}]
    
    # Configure mocks
    crud_instance.get_latest_records.return_value = db_latest_records
    remove_matching_records_mock.return_value = (records_to_enddate, records_to_upload)
    crud_instance.generate_query.get_table_name.return_value = "test_table"
    
    # Call the function
    crud_instance.process_enddate_update_records(query, input_records)
    
    # Assertions
    crud_instance.get_latest_records.assert_called_once_with(query=query)
    remove_matching_records_mock.assert_called_once_with(db_latest_records, input_records)
    crud_instance.enddate_output_records.assert_called_once_with(records_to_db_enddate=records_to_enddate)
    crud_instance.bulk_upload_records_to_db.assert_called_once_with(records=records_to_upload)

def test_no_records(crud_instance, remove_matching_records_mock):
    """Test when there are no records to update or upload."""
    # Setup
    query = "test_query"
    input_records = []
    db_latest_records = []
    
    # Configure mocks
    crud_instance.get_latest_records.return_value = db_latest_records
    remove_matching_records_mock.return_value = ([], [])
    crud_instance.generate_query.get_table_name.return_value = "test_table"
    
    # Call the function
    crud_instance.process_enddate_update_records(query, input_records)
    
    # Assertions
    crud_instance.get_latest_records.assert_called_once_with(query=query)
    remove_matching_records_mock.assert_called_once_with(db_latest_records, input_records)
    crud_instance.enddate_output_records.assert_not_called()
    crud_instance.bulk_upload_records_to_db.assert_not_called()

def test_docato_version_check(crud_instance, remove_matching_records_mock):
    """Test the docato_version check that prevents updates."""
    # Setup
    query = "test_query"
    input_records = [{"id": 1, "docato_version": "v1"}]
    db_latest_records = [{"id": 1, "docato_version": "v1"}]  # Same version
    
    # Configure mocks
    crud_instance.get_latest_records.return_value = db_latest_records
    remove_matching_records_mock.return_value = ([], [])
    crud_instance.generate_query.get_table_name.return_value = "docato_version_table"
    
    # Mock logger
    with patch('logger.info') as mock_logger:
        # Call the function
        crud_instance.process_enddate_update_records(query, input_records)
    
    # Assertions
    crud_instance.get_latest_records.assert_called_once_with(query=query)
    mock_logger.assert_called_with("Docato version exists! Stop updating")
    crud_instance.enddate_output_records.assert_not_called()
    crud_instance.bulk_upload_records_to_db.assert_not_called()

def test_only_enddate(crud_instance, remove_matching_records_mock):
    """Test when there are only records to enddate but none to upload."""
    # Setup
    query = "test_query"
    input_records = [{"id": 1, "value": "test1", "docato_version": "v2"}]
    db_latest_records = [{"id": 1, "value": "old_test1", "docato_version": "v1"}]
    
    records_to_enddate = [{"id": 1, "value": "old_test1", "docato_version": "v1"}]
    records_to_upload = []
    
    # Configure mocks
    crud_instance.get_latest_records.return_value = db_latest_records
    remove_matching_records_mock.return_value = (records_to_enddate, records_to_upload)
    crud_instance.generate_query.get_table_name.return_value = "test_table"
    
    # Call the function
    crud_instance.process_enddate_update_records(query, input_records)
    
    # Assertions
    crud_instance.enddate_output_records.assert_called_once_with(records_to_db_enddate=records_to_enddate)
    crud_instance.bulk_upload_records_to_db.assert_not_called()

def test_only_upload(crud_instance, remove_matching_records_mock):
    """Test when there are only records to upload but none to enddate."""
    # Setup
    query = "test_query"
    input_records = [{"id": 2, "value": "test2", "docato_version": "v1"}]
    db_latest_records = [{"id": 1, "value": "test1", "docato_version": "v1"}]
    
    records_to_enddate = []
    records_to_upload = [{"id": 2, "value": "test2", "docato_version": "v1"}]
    
    # Configure mocks
    crud_instance.get_latest_records.return_value = db_latest_records
    remove_matching_records_mock.return_value = (records_to_enddate, records_to_upload)
    crud_instance.generate_query.get_table_name.return_value = "test_table"
    
    # Call the function
    crud_instance.process_enddate_update_records(query, input_records)
    
    # Assertions
    crud_instance.enddate_output_records.assert_not_called()
    crud_instance.bulk_upload_records_to_db.assert_called_once_with(records=records_to_upload)