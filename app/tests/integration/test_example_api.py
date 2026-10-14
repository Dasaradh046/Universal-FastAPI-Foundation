"""
API tests for the example module.
"""
from fastapi import status
from app.modules.example_module.schemas import ExampleCreate


def test_create_example(client):
    """Test creating an example."""
    response = client.post(
        "/api/v1/examples/",
        json={
            "name": "Test Example",
            "description": "This is a test example"
        }
    )
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Test Example"
    assert data["description"] == "This is a test example"
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_read_examples(client):
    """Test reading examples."""
    response = client.get("/api/v1/examples/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)


def test_read_example_not_found(client):
    """Test reading a non-existent example."""
    response = client.get("/api/v1/examples/999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
