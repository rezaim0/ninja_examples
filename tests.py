import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from your_module import MacatoAgent, FieldsCRUD, docato_schema, BaseModel

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
    # Using docato_schema() as that's the default
    agent = MacatoAgent(database="test_db")
    
    # Create a mock ATO model if needed
    ato_model = {"some": "model"}  # adjust based on actual ATOModelOps structure
    agent.model = ato_model
    
    return agent

def test_update_fields_integration_with_default_schema(db_session, test_macato_agent):
    """Test update_fields with default docato_schema"""
    # Execute update_fields
    test_macato_agent.update_fields()
    
    # Use FieldsCRUD to verify the results
    fields_crud = FieldsCRUD()
    latest_records = fields_crud.execute_query(
        fields_crud.generate_query.get_latest_field_description()
    )
    
    # Assert records were created
    assert len(latest_records) > 0
    # Add more specific assertions based on what docato_schema() returns

def test_update_fields_integration_with_custom_fields(db_session):
    """Test update_fields with custom fields"""
    custom_fields = {
        "table1": {
            "column1": {"type": "string", "description": "test column"}
        }
    }
    
    agent = MacatoAgent(database="test_db", fields=custom_fields)
    agent.update_fields()
    
    # Verify the custom fields were saved
    fields_crud = FieldsCRUD()
    latest_records = fields_crud.execute_query(
        fields_crud.generate_query.get_latest_field_description()
    )
    
    # Assert the custom fields were saved correctly
    assert len(latest_records) > 0
    # Add specific assertions based on your custom_fields structure

def test_update_fields_integration_updates_existing_records(db_session, test_macato_agent):
    """Test that update_fields properly handles updating existing records"""
    # First update
    test_macato_agent.update_fields()
    
    # Get timestamp of first update
    fields_crud = FieldsCRUD()
    first_update_records = fields_crud.execute_query(
        fields_crud.generate_query.get_latest_field_description()
    )
    
    # Second update with same data
    test_macato_agent.update_fields()
    
    # Get latest records
    latest_records = fields_crud.execute_query(
        fields_crud.generate_query.get_latest_field_description()
    )
    
    # Verify the behavior (depending on your implementation)
    # Either the records should be the same (if idempotent)
    # Or there should be new records with the old ones end-dated