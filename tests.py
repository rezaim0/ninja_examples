import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from your_module import Agent, FieldCRUD, create_field_description
from your_module.models import Base, FieldDescription  # Assuming these exist

# ---------- Unit Tests ----------

@pytest.fixture
def agent_with_fields():
    test_fields = {'field1': 'value1', 'field2': 'value2'}
    return Agent(fields=test_fields)

@patch('your_module.create_field_description')
@patch('your_module.FieldCRUD')
def test_update_fields_calls_correct_methods(mock_field_crud_class, mock_create_field_description, agent_with_fields):
    # Setup mocks
    mock_field_description = MagicMock()
    mock_field_description.to_dict.return_value = {'record1': 'data1'}
    mock_create_field_description.return_value = mock_field_description
    
    mock_field_crud = MagicMock()
    mock_field_crud_class.return_value = mock_field_crud
    mock_query = MagicMock()
    mock_field_crud.generate_query.get_latest_field_description.return_value = mock_query
    mock_field_crud.query.compile.return_value = "compiled_query"
    
    # Call the method
    agent_with_fields.update_fields()
    
    # Verify all interactions
    mock_create_field_description.assert_called_once_with(agent_with_fields.fields)
    mock_field_description.to_dict.assert_called_once_with(content="records")
    mock_field_crud.generate_query.get_latest_field_description.assert_called_once()
    mock_field_crud.query.compile.assert_called_once()
    mock_field_crud.process_enddate_and_update_records.assert_called_once_with(
        query="compiled_query", 
        input_records={'record1': 'data1'}
    )

@patch('your_module.create_field_description')
@patch('your_module.FieldCRUD')
def test_update_fields_with_empty_fields(mock_field_crud_class, mock_create_field_description):
    # Test behavior with empty fields
    agent = Agent(fields={})
    
    # Setup mocks
    mock_field_description = MagicMock()
    mock_field_description.to_dict.return_value = {}
    mock_create_field_description.return_value = mock_field_description
    
    mock_field_crud = MagicMock()
    mock_field_crud_class.return_value = mock_field_crud
    
    # Call and verify
    agent.update_fields()
    mock_field_crud.process_enddate_and_update_records.assert_called_once_with(
        query=mock_field_crud.query.compile.return_value, 
        input_records={}
    )

# ---------- Integration Tests with SQLAlchemy ----------

@pytest.fixture(scope="session")
def test_engine():
    """Create an SQLAlchemy engine for testing."""
    # Use in-memory SQLite for tests
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return engine

@pytest.fixture(scope="function")
def db_session(test_engine):
    """Create a new database session for a test."""
    connection = test_engine.connect()
    transaction = connection.begin()
    
    # Create session bound to the connection
    Session = scoped_session(sessionmaker(bind=connection))
    session = Session()
    
    # Inject session dependency if your Agent/FieldCRUD uses a global session
    from your_module import set_session
    set_session(session)  # Assuming you have such a function
    
    yield session
    
    # Rollback transaction and close session after test
    Session.remove()
    transaction.rollback()
    connection.close()

@pytest.fixture
def seed_test_data(db_session):
    """Seed the database with test data."""
    # Add initial field descriptions
    field_desc = FieldDescription(
        field_id='001',
        name='Test Agent',
        type='old_type',
        status='inactive',
        start_date='2023-01-01',
        end_date=None
    )
    db_session.add(field_desc)
    db_session.commit()

@pytest.fixture
def test_agent():
    return Agent(fields={
        'name': 'Test Agent',
        'type': 'integration_test',
        'status': 'active'
    })

def test_update_fields_integration(db_session, seed_test_data, test_agent):
    # Perform the update
    test_agent.update_fields()
    
    # Query for updated records
    latest_fields = db_session.query(FieldDescription).filter(
        FieldDescription.end_date.is_(None)
    ).all()
    
    # Verify old records were end-dated
    closed_records = db_session.query(FieldDescription).filter(
        FieldDescription.end_date.is_not(None)
    ).all()
    
    assert len(closed_records) > 0
    
    # Find the record matching our agent
    agent_record = next((f for f in latest_fields if f.name == test_agent.fields['name']), None)
    assert agent_record is not None
    assert agent_record.type == test_agent.fields['type']
    assert agent_record.status == test_agent.fields['status']

def test_update_fields_idempotence(db_session, seed_test_data, test_agent):
    # First update
    test_agent.update_fields()
    
    # Count records after first update
    first_count = db_session.query(FieldDescription).count()
    
    # Update again with same data
    test_agent.update_fields()
    
    # Count records after second update
    second_count = db_session.query(FieldDescription).count()
    
    # Depending on your implementation:
    # If you don't create new records for unchanged data:
    assert second_count == first_count
    
    # Or if you always create new records, this would be the test:
    # assert second_count > first_count

def test_update_fields_with_changed_data(db_session, seed_test_data, test_agent):
    # Initial update
    test_agent.update_fields()
    
    # Change fields
    test_agent.fields['status'] = 'inactive'
    test_agent.fields['type'] = 'updated_test_type'
    
    # Update again
    test_agent.update_fields()
    
    # Query for latest records
    latest_record = db_session.query(FieldDescription).filter(
        FieldDescription.name == test_agent.fields['name'],
        FieldDescription.end_date.is_(None)
    ).one()
    
    # Verify fields are updated
    assert latest_record.status == 'inactive'
    assert latest_record.type == 'updated_test_type'
    
    # Verify history exists
    history_count = db_session.query(FieldDescription).filter(
        FieldDescription.name == test_agent.fields['name']
    ).count()
    
    assert history_count >= 2  # At least original + updated