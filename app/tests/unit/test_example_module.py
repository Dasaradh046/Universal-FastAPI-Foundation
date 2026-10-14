"""
Tests for the example module.
"""
from app.modules.example_module.schemas import ExampleCreate, ExampleUpdate


def test_create_example_schema():
    """Test ExampleCreate schema."""
    example_data = ExampleCreate(
        name="Test Example",
        description="This is a test example"
    )
    assert example_data.name == "Test Example"
    assert example_data.description == "This is a test example"


def test_update_example_schema():
    """Test ExampleUpdate schema."""
    example_data = ExampleUpdate(
        name="Updated Example"
    )
    assert example_data.name == "Updated Example"
    assert example_data.description is None


def test_example_in_db_base():
    """Test ExampleInDBBase schema."""
    # This would normally be tested with an actual ORM model
    pass
