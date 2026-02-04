"""
Tests for the Mergington High School API
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the API"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities data before each test"""
    # Store original state
    original_activities = {
        name: {**details, "participants": details["participants"].copy()}
        for name, details in activities.items()
    }
    
    yield
    
    # Restore original state after test
    for name, details in original_activities.items():
        activities[name]["participants"] = details["participants"].copy()


def test_root_redirect(client):
    """Test that root redirects to static/index.html"""
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/static/index.html"


def test_get_activities(client):
    """Test getting all activities"""
    response = client.get("/activities")
    assert response.status_code == 200
    data = response.json()
    
    # Verify structure
    assert isinstance(data, dict)
    assert "Chess Club" in data
    assert "Basketball Team" in data
    
    # Verify activity details
    chess_club = data["Chess Club"]
    assert "description" in chess_club
    assert "schedule" in chess_club
    assert "max_participants" in chess_club
    assert "participants" in chess_club
    assert isinstance(chess_club["participants"], list)


def test_signup_for_activity_success(client):
    """Test successful signup for an activity"""
    response = client.post(
        "/activities/Chess%20Club/signup?email=test@mergington.edu"
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "test@mergington.edu" in data["message"]
    assert "Chess Club" in data["message"]
    
    # Verify participant was added
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    assert "test@mergington.edu" in activities_data["Chess Club"]["participants"]


def test_signup_for_nonexistent_activity(client):
    """Test signup for an activity that doesn't exist"""
    response = client.post(
        "/activities/Nonexistent%20Activity/signup?email=test@mergington.edu"
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Activity not found"


def test_signup_duplicate_participant(client):
    """Test that a student cannot sign up twice for the same activity"""
    email = "duplicate@mergington.edu"
    activity = "Chess Club"
    
    # First signup should succeed
    response1 = client.post(
        f"/activities/{activity}/signup?email={email}"
    )
    assert response1.status_code == 200
    
    # Second signup should fail
    response2 = client.post(
        f"/activities/{activity}/signup?email={email}"
    )
    assert response2.status_code == 400
    data = response2.json()
    assert data["detail"] == "Student already signed up for this activity"


def test_unregister_from_activity_success(client):
    """Test successful unregistration from an activity"""
    # First, sign up a participant
    email = "unregister@mergington.edu"
    activity = "Chess Club"
    client.post(f"/activities/{activity}/signup?email={email}")
    
    # Now unregister
    response = client.delete(
        f"/activities/{activity}/unregister?email={email}"
    )
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert email in data["message"]
    assert activity in data["message"]
    
    # Verify participant was removed
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    assert email not in activities_data[activity]["participants"]


def test_unregister_from_nonexistent_activity(client):
    """Test unregister from an activity that doesn't exist"""
    response = client.delete(
        "/activities/Nonexistent%20Activity/unregister?email=test@mergington.edu"
    )
    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Activity not found"


def test_unregister_non_participant(client):
    """Test unregistering a student who is not signed up"""
    response = client.delete(
        "/activities/Chess%20Club/unregister?email=notregistered@mergington.edu"
    )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Student is not signed up for this activity"


def test_unregister_existing_participant(client):
    """Test unregistering an existing participant"""
    # Use a pre-existing participant
    email = "michael@mergington.edu"
    activity = "Chess Club"
    
    # Verify they are registered
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    assert email in activities_data[activity]["participants"]
    
    # Unregister them
    response = client.delete(
        f"/activities/{activity}/unregister?email={email}"
    )
    assert response.status_code == 200
    
    # Verify they were removed
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    assert email not in activities_data[activity]["participants"]


def test_signup_and_unregister_workflow(client):
    """Test complete workflow of signing up and unregistering"""
    email = "workflow@mergington.edu"
    activity = "Drama Club"
    
    # Get initial participant count
    response = client.get("/activities")
    initial_count = len(response.json()[activity]["participants"])
    
    # Sign up
    signup_response = client.post(
        f"/activities/{activity}/signup?email={email}"
    )
    assert signup_response.status_code == 200
    
    # Verify count increased
    response = client.get("/activities")
    assert len(response.json()[activity]["participants"]) == initial_count + 1
    
    # Unregister
    unregister_response = client.delete(
        f"/activities/{activity}/unregister?email={email}"
    )
    assert unregister_response.status_code == 200
    
    # Verify count back to original
    response = client.get("/activities")
    assert len(response.json()[activity]["participants"]) == initial_count


def test_multiple_activities_signup(client):
    """Test that a student can sign up for multiple different activities"""
    email = "multi@mergington.edu"
    
    # Sign up for multiple activities
    response1 = client.post(f"/activities/Chess%20Club/signup?email={email}")
    assert response1.status_code == 200
    
    response2 = client.post(f"/activities/Drama%20Club/signup?email={email}")
    assert response2.status_code == 200
    
    response3 = client.post(f"/activities/Art%20Studio/signup?email={email}")
    assert response3.status_code == 200
    
    # Verify all signups
    activities_response = client.get("/activities")
    activities_data = activities_response.json()
    assert email in activities_data["Chess Club"]["participants"]
    assert email in activities_data["Drama Club"]["participants"]
    assert email in activities_data["Art Studio"]["participants"]
