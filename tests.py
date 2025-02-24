import pytest
from unittest.mock import patch, MagicMock
from my_module import MacatoAgent  # Replace with your actual import path

@pytest.fixture
def sample_fields():
    """
    Sample fields structure that includes the required 'schema' keys.
    This matches what create_field_description_pd expects.
    """
    return {
        "table1": {
            "item_a": {
                "schema": {
                    "field1": {"description": "test field 1", "title": "Title Field1"},
                    "field2": {"description": "test field 2", "title": "Title Field2"}
                }
            },
            "item_b": {
                "schema": {
                    "variable_1": {"description": "ignored var", "title": "Ignore me"},
                    "field3": {"description": "test field 3", "title": "Title Field3"}
                }
            }
        },
        "table2": {
            "item_x": {
                "schema": {
                    "field4": {"description": "test field 4", "title": "Title Field4"}
                }
            }
        }
    }

@pytest.fixture
def macato_agent(sample_fields):
    """Creates a MacatoAgent with the sample fields."""
    return MacatoAgent(fields=sample_fields)

@patch("my_module.FieldsCRUD")
@patch("my_module.create_field_description_pd")
def test_update_fields_calls_correct_methods(mock_create_field_desc, mock_fields_crud_class, macato_agent):
    """
    Unit test ensuring update_fields() calls:
    1) create_field_description_pd(self.fields)
    2) FieldsCRUD().generate_query.get_latest_field_description(...)
    3) FieldsCRUD().process_enddate_update_records(...)
    with the expected parameters.
    """
    # Mock the DataFrame -> dict conversion
    mock_df = MagicMock()
    mock_df.to_dict.return_value = [
        {"component_name": "table1", "field_name": "field1", "field_description": "test field 1"},
        {"component_name": "table1", "field_name": "field2", "field_description": "test field 2"}
    ]
    mock_create_field_desc.return_value = mock_df

    # Mock the FieldsCRUD instance
    mock_crud_instance = MagicMock()
    mock_fields_crud_class.return_value = mock_crud_instance

    # Suppose generate_query.get_latest_field_description returns a “fake_query”
    fake_query = "fake_query_object"
    mock_crud_instance.generate_query.get_latest_field_description.return_value = fake_query

    # Call the method under test
    macato_agent.update_fields()

    # Assertions:
    # 1. create_field_description_pd called once with the agent's fields
    mock_create_field_desc.assert_called_once_with(macato_agent.fields)

    # 2. The mock DataFrame's to_dict() was called with orient="records"
    mock_df.to_dict.assert_called_once_with(orient="records")

    # 3. FieldsCRUD was instantiated
    mock_fields_crud_class.assert_called_once()

    # 4. generate_query.get_latest_field_description called with the right argument
    mock_crud_instance.generate_query.get_latest_field_description.assert_called_once_with(
        query_compile=mock_crud_instance.query_compile
    )

    # 5. process_enddate_update_records is called with the “fake_query” + the records
    mock_crud_instance.process_enddate_update_records.assert_called_once_with(
        query=fake_query,
        input_records=mock_df.to_dict.return_value
    )


@patch("my_module.FieldsCRUD")
@patch("my_module.create_field_description_pd")
def test_update_fields_with_empty_fields(mock_create_field_desc, mock_fields_crud_class):
    """
    Unit test for an agent with empty fields.
    Ensures it gracefully handles the scenario.
    """
    agent = MacatoAgent(fields={})

    # Mock out create_field_description_pd
    mock_df = MagicMock()
    mock_df.to_dict.return_value = []
    mock_create_field_desc.return_value = mock_df

    # Mock FieldsCRUD
    mock_crud_instance = MagicMock()
    mock_fields_crud_class.return_value = mock_crud_instance

    # Act
    agent.update_fields()

    # Assert
    mock_create_field_description_pd.assert_called_once_with({})
    mock_crud_instance.process_enddate_update_records.assert_called_once_with(
        query=mock_crud_instance.generate_query.get_latest_field_description.return_value,
        input_records=[]
    )

#---------------------------- Itegration --------------------

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from my_models import Base, FieldsTable
from my_module import MacatoAgent, FieldsCRUD  # or your actual imports

@pytest.fixture(scope="session")
def engine():
    """Create an in-memory SQLite engine for the entire test session."""
    eng = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(eng)
    return eng

@pytest.fixture(scope="function")
def db_session(engine):
    """
    Creates a new database session for a test.
    Everything is rolled back after the test.
    """
    connection = engine.connect()
    transaction = connection.begin()
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def macato_agent_with_db(db_session):
    """
    Returns a MacatoAgent that is configured with a 
    sample 'fields' structure plus a DB session.
    We assume MacatoAgent can either accept the session
    or retrieve it from somewhere internally.
    """
    test_fields = {
        "table1": {
            "item_a": {
                "schema": {
                    "field1": {"description": "test field 1", "title": "Title Field1"},
                    "field2": {"description": "test field 2", "title": "Title Field2"}
                }
            }
        }
    }
    agent = MacatoAgent(fields=test_fields)
    # If your agent needs the session in a specific attribute, do it here, e.g.:
    agent.session = db_session
    return agent

def test_update_fields_integration(db_session, macato_agent_with_db):
    """
    Integration test that:
    1. Has a real DB session.
    2. Calls update_fields() for real.
    3. Asserts changes in the 'fields_table'.
    """
    # Possibly insert some existing record if your logic end-dates old records
    existing = FieldsTable(
        component_name="table1",
        field_name="field1",
        field_description="Old description"
    )
    db_session.add(existing)
    db_session.commit()

    # Act
    macato_agent_with_db.update_fields()

    # Assert: Check new rows or end-dated rows in the DB
    rows = db_session.query(FieldsTable).all()
    assert len(rows) == 2, "Should have old record end-dated + 1 new record, or 2 new records, etc."

    # For example, let's see how we check them:
    old_record = db_session.query(FieldsTable).filter_by(field_description="Old description").first()
    assert old_record is not None
    assert old_record.end_dttm is not None, "Old record should be end-dated."

    new_record = db_session.query(FieldsTable).filter_by(field_description="test field 1").first()
    assert new_record is not None
    assert new_record.end_dttm is None, "New record is active"
    assert new_record.field_name == "field1"
    # etc.

def test_update_fields_multiple_updates(db_session, macato_agent_with_db):
    """
    Demonstrates calling update_fields() multiple times, verifying historical records.
    """
    # 1) First update
    macato_agent_with_db.update_fields()

    # 2) Now modify the fields to trigger another update
    macato_agent_with_db.fields["table1"]["item_a"]["schema"]["field1"]["description"] = "Updated Description"

    macato_agent_with_db.update_fields()

    # Assert we have old and new records
    rows = db_session.query(FieldsTable).all()
    # e.g. We might have 2 or 3 total records, depending on your logic.
    assert len(rows) >= 2, "Should have old versions plus updated versions"

    # Inspect the latest version of field1
    latest_field1 = (
        db_session.query(FieldsTable)
        .filter(FieldsTable.field_name == "field1")
        .order_by(FieldsTable.id.desc())
        .first()
    )
    assert latest_field1.field_description == "Updated Description"
    assert latest_field1.end_dttm is None, "Should be active"

    # The older version should have an end_dttm
    older_versions = (
        db_session.query(FieldsTable)
        .filter(FieldsTable.field_name == "field1", FieldsTable.id < latest_field1.id)
        .all()
    )
    for record in older_versions:
        assert record.end_dttm is not None, "Older record(s) should be ended"