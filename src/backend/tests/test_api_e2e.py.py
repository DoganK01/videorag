import os
import pytest
import httpx
from httpx import AsyncClient

pytestmark = pytest.mark.e2e

@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """Ensure the tests use the correct docker-compose file."""
    return os.path.join(str(pytestconfig.rootdir), "deployment", "docker-compose.yml")

@pytest.fixture(scope="session")
def api_service(docker_ip, docker_services):
    """
    Waits for the API service to be healthy and returns its URL.
    This fixture ensures that tests only run after the entire stack is up.
    """
    port = docker_services.port_for("api", 8000)
    url = f"http://{docker_ip}:{port}"
    # Wait for the service to be ready
    docker_services.wait_until_responsive(
        timeout=120.0, pause=1.0, check=lambda: httpx.get(f"{url}/").is_success
    )
    return url

@pytest.mark.asyncio
async def test_full_end_to_end_pipeline(api_service, docker_compose):
    """
    A complete end-to-end test for the VideoRAG application.

    This test performs the following steps:
    1.  (Implicitly handled by pytest-docker) Starts the entire application stack.
    2.  Executes the indexing pipeline on a sample video file.
    3.  Waits for indexing to complete.
    4.  Sends a query to the live API endpoint.
    5.  Validates the structure and content of the API response.
    """
    # --- Step 1 & 2: Run the Indexer ---
    # We use docker_compose to execute a command in the 'indexer' service container.
    sample_video_path = "/app/source_videos/sample_video.mp4" # Path inside the container
    
    # Before running, make sure the sample video is in the 'deployment/source_videos' directory
    # on the host machine, as it's mounted into the container.
    if not os.path.exists("deployment/source_videos/sample_video.mp4"):
        pytest.fail("Sample video 'sample_video.mp4' not found in deployment/source_videos/. Please add it.")

    indexer_command = f"indexer --video-path {sample_video_path}"
    
    # Execute the indexing command. This will block until it's complete.
    result = docker_compose.execute(indexer_command)
    
    # Assert that the indexing process completed successfully (exit code 0)
    assert result.exit_code == 0, f"Indexing failed with output:\n{result.output.decode()}"
    print("Indexing completed successfully.")

    # --- Step 3: Query the API ---
    # The api_service fixture ensures the API is ready.
    query_payload = {
        "query": "What is discussed in the sample video?" # A generic query for the sample video
    }
    
    async with AsyncClient(base_url=api_service, timeout=60.0) as client:
        response = await client.post("/api/v1/query", json=query_payload)

    # --- Step 4: Validate the Response ---
    assert response.status_code == 200, f"API returned non-200 status: {response.text}"
    
    response_data = response.json()
    
    # Validate the response schema
    assert "query" in response_data
    assert "answer" in response_data
    assert "retrieved_sources" in response_data
    
    assert response_data["query"] == query_payload["query"]
    assert isinstance(response_data["answer"], str)
    assert len(response_data["answer"]) > 0, "API returned an empty answer."
    
    assert isinstance(response_data["retrieved_sources"], list)
    
    # If sources were retrieved, validate the schema of the first source
    if response_data["retrieved_sources"]:
        source = response_data["retrieved_sources"][0]
        assert "clip_id" in source
        assert "source_video_id" in source
        assert "start_time" in source
        assert "end_time" in source
        assert "retrieval_score" in source
        assert "source_type" in source
        assert source["source_video_id"] == "sample_video" # Assuming video ID is the stem of the filename
        
    print(f"E2E Test Passed. API Answer: {response_data['answer'][:100]}...")