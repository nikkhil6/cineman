"""
Integration tests for streaming API endpoint.
"""
import pytest
import json


@pytest.fixture
def client():
    """Create test client."""
    from cineman.app import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestStreamingAPIEndpoint:
    """Test /api/movie streaming data integration."""
    
    def test_movie_api_includes_streaming_data(self, client):
        """Should include streaming data in movie API response."""
        response = client.get('/api/movie?title=Inception')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert 'streaming' in data
        assert isinstance(data['streaming'], list)
    
    def test_streaming_data_structure(self, client):
        """Streaming providers should have required fields."""
        response = client.get('/api/movie?title=The Matrix')
        data = json.loads(response.data)
        
        if data.get('streaming'):
            provider = data['streaming'][0]
            assert 'name' in provider
            assert 'url' in provider
            assert 'type' in provider
    
    def test_streaming_status_endpoint(self, client):
        """Should have streaming status endpoint."""
        response = client.get('/api/streaming/status')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'success'
        assert 'service' in data


class TestStreamingDataFlow:
    """Test end-to-end streaming data flow."""
    
    def test_enrichment_adds_streaming_to_schema(self, client):
        """Schema should include streaming field after enrichment."""
        response = client.get('/api/movie?title=Inception')
        data = json.loads(response.data)
        
        # Check schema structure
        if 'schema' in data:
            assert 'streaming' in data['schema']
            schema_streaming = data['schema']['streaming']
            assert isinstance(schema_streaming, list)
    
    def test_no_duplicate_providers_in_response(self, client):
        """Response should not contain duplicate providers."""
        response = client.get('/api/movie?title=The Godfather')
        data = json.loads(response.data)
        
        if data.get('streaming'):
            provider_names = [p['name'] for p in data['streaming']]
            # Check for duplicates
            assert len(provider_names) == len(set(provider_names)), \
                f"Found duplicate providers: {provider_names}"
