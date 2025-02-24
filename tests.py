import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from your_module import MacatoAgent, FieldsCRUD, create_field_description_pd, BaseModel

# ---------- Unit Tests ----------

@pytest.fixture
def macato_agent():
    return MacatoAgent(fields={"field1": "value1", "field2": "value2"})

@patch('your_module.create_field_description_pd')
@patch('your_module.FieldsCRUD')
def test_update_fields_calls_correct_methods(mock_fields_crud_class, mock_create_field_description_pd, macato_agent):
    # Setup mocks
    mock_field_description = MagicMock()
    mock_field_description.to_dict.return_value = {'record1': 'data1'}
    mock_create_field_description_pd.return_value = mock_field_description
    
    mock_fields_crud = MagicMock()
    mock_fields_crud_class.return_value = mock_fields_crud
    mock_query = MagicMock()
    mock_fields_crud.generate_query.get_latest_field_description.return_value = mock_query
    
    # Call the method
    macato_agent.update_fields()
    
    # Verify interactions
    mock_create_field_description_pd.assert_called_once_with(macato_agent.fields)
    mock_field_description.to_dict.assert_called_once_with(orient="records")
    mock_fields_crud.generate_query.get_latest_field_description.assert_called_once()
    mock_fields_crud.process_enddate_update_records.assert_called_once_with(
        query=mock_query,
        input_records=mock_field_description.to_dict.return_value
    )

@patch('your_module.create_field_description_pd')
@patch('your_module.FieldsCRUD')
def test_update_fields_with_empty_fields(mock_fields_crud_class, mock_create_field_description_pd):
    # Test with empty fields
    agent = MacatoAgent(fields={})
    
    # Setup mocks
    mock_field_description = MagicMock()
    mock_field_description.to_dict.return_value = {}
    mock_create_field_description_pd.return_value = mock_field_description
    
    mock_fields_crud = MagicMock()
    mock_fields_crud_class.return_value = mock_fields_crud
    
    # Call and verify
    agent.update_fields()
    mock_fields_crud.process_enddate_update_records.assert_called_once_with(
        query=mock_fields_crud.generate_query.get_latest_field_description.return_value,
        input_records={}
    )

# ---------- Integration Tests ----------

@pytest.fixture(scope="session")
def test_engine():
    """Create SQLAlchemy engine for testing."""
    engine = create_engine('sqlite:///:memory:')
    BaseModel.metadata.create_all(engine)
    return engine

@pytest.fixture(scope="function")
def db_session(test_engine):
    """Provide a transactional database session."""
    connection = test_engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def test_macato_agent(db_session):
    """Create a test MacatoAgent instance."""
    agent = MacatoAgent(
        database="test_db",
        fields={
            "field_name": "test_field",
            "field_type": "text",
            "field_value": "test_value"
        }
    )
    return agent

def test_update_fields_integration(db_session, test_macato_agent):
    # Execute update_fields
    test_macato_agent.update_fields()
    
    # Query the database to verify the field records were created
    fields_crud = FieldsCRUD()
    latest_fields = fields_crud.get_latest_fields()  # Assuming such method exists
    
    # Verify the records match our test data
    assert len(latest_fields) > 0
    field_record = latest_fields[0]
    assert field_record.field_name == "test_field"
    assert field_record.field_type == "text"
    assert field_record.field_value == "test_value"

def test_update_fields_multiple_updates(db_session, test_macato_agent):
    # First update
    test_macato_agent.update_fields()
    
    # Modify fields
    test_macato_agent.fields["field_value"] = "updated_value"
    
    # Second update
    test_macato_agent.update_fields()
    
    # Verify the updates
    fields_crud = FieldsCRUD()
    latest_fields = fields_crud.get_latest_fields()
    
    # Check latest record has updated value
    latest_record = latest_fields[0]
    assert latest_record.field_value == "updated_value"
    
    # Check history exists
    field_history = fields_crud.get_field_history()  # Assuming such method exists
    assert len(field_history) >= 2  # Should have at least 2 records