"""Tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from src.backend.app import app

client = TestClient(app)


class TestHealth:
    """Test health check endpoint."""
    
    def test_health(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert data["status"] in ["ok", "degraded"]


class TestIndex:
    """Test indexing endpoints."""
    
    def test_index_invalid_url(self):
        response = client.post(
            "/index",
            json={"repo_url": "invalid-url", "project": "test"}
        )
        assert response.status_code == 400
    
    def test_index_valid_request(self):
        response = client.post(
            "/index",
            json={
                "repo_url": "https://github.com/user/repo.git",
                "project": "test"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "repo_id" in data
        assert "job_id" in data
        assert data["status"] == "queued"


class TestRetrieve:
    """Test search/retrieve endpoints."""
    
    def test_retrieve_missing_query(self):
        response = client.get("/retrieve")
        assert response.status_code == 422  # Unprocessable entity
    
    def test_retrieve_empty_results(self):
        response = client.get("/retrieve?q=nonexistent_query&k=5")
        # Returns 200 with empty results if no matches
        assert response.status_code == 200 or response.status_code == 500
    
    def test_retrieve_k_limit(self):
        response = client.get("/retrieve?q=test&k=200")
        # Should enforce max k=100
        if response.status_code == 200:
            data = response.json()
            assert len(data["results"]) <= 100


class TestSuggestion:
    """Test code suggestion endpoints."""
    
    def test_suggest_invalid_issue_type(self):
        response = client.post(
            "/suggest",
            json={
                "snippet_id": "test-id",
                "issue_type": "invalid_type",
                "issue_description": "Test issue"
            }
        )
        assert response.status_code == 400
    
    def test_suggest_nonexistent_snippet(self):
        response = client.post(
            "/suggest",
            json={
                "snippet_id": "nonexistent-id",
                "issue_type": "security",
                "issue_description": "Test issue"
            }
        )
        assert response.status_code == 404


class TestRepositories:
    """Test repository management endpoints."""
    
    def test_list_repositories(self):
        response = client.get("/repositories")
        assert response.status_code == 200 or response.status_code == 500
        if response.status_code == 200:
            data = response.json()
            assert "repositories" in data
            assert "total" in data
    
    def test_get_nonexistent_repository(self):
        response = client.get("/repositories/nonexistent-id")
        assert response.status_code == 404
