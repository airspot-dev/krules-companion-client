from pydantic import BaseModel
from krules_companion_client.models import EntityUpdatedEvent, EntityCreatedEvent, EntityDeletedEvent, \
    EntityCallbackEvent


def test_entity_updated_model():
    class TestEntityState(BaseModel):
        svar: str
        ivar: int

    data = {
        "changed_properties": ["svar"],
        "id": "X1",
        "group": "G1",
        "subscription": 0,
        "state": {
            "svar": "A",
            "ivar": 1
        },
        "old_state": {
            "svar": "B",
            "ivar": 1
        }
    }
    model = EntityUpdatedEvent[TestEntityState](**data)
    assert "svar" in model.changed_properties
    assert model.id == "X1"
    assert model.group == "G1"
    assert model.state.svar == "A"
    assert model.state.ivar == 1
    assert model.old_state.svar == "B"
    assert model.old_state.ivar == 1


def test_entity_created_model():
    class TestEntityState(BaseModel):
        svar: str
        ivar: int

    data = {
        "changed_properties": ["svar"],
        "id": "X1",
        "group": "G1",
        "subscription": 0,
        "state": {
            "svar": "A",
            "ivar": 1
        },
        "old_state": None
    }
    model = EntityCreatedEvent[TestEntityState](**data)
    assert "svar" in model.changed_properties
    assert model.id == "X1"
    assert model.group == "G1"
    assert model.state.svar == "A"
    assert model.state.ivar == 1
    assert model.old_state is None


def test_entity_deleted_model():
    class TestEntityState(BaseModel):
        svar: str
        ivar: int

    data = {
        "changed_properties": ["svar"],
        "id": "X1",
        "group": "G1",
        "subscription": 0,
        "state": None,
        "old_state": {
            "svar": "A",
            "ivar": 1
        },
    }
    model = EntityDeletedEvent[TestEntityState](**data)
    assert "svar" in model.changed_properties
    assert model.id == "X1"
    assert model.group == "G1"
    assert model.old_state.svar == "A"
    assert model.old_state.ivar == 1
    assert model.state is None

def test_entity_callback():

    class TestEntityState(BaseModel):
        svar: str
        ivar: int

    data = {
        "last_updated": "2020-01-01T00:00:00Z",
        "task_id": "xxx-xxx-xxx",
        "id": "X1",
        "group": "G1",
        "subscription": 0,
        "state": {
            "svar": "A",
            "ivar": 1
        },
        "message": "Hello:)"
    }

    model = EntityCallbackEvent[TestEntityState](**data)
    assert model.last_updated.year == 2020
