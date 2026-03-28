import pytest
from debugorm import configure, Model
from debugorm.fields import IntegerField, StringField


@pytest.fixture(autouse=True)
def fresh_db():
    """Each test gets its own in-memory database."""
    configure(":memory:")


@pytest.fixture
def User():
    class User(Model):
        id   = IntegerField(primary_key=True)
        name = StringField(max_length=100)
        age  = IntegerField()

    User.create_table()
    return User


@pytest.fixture
def populated_db(User):
    users = [
        User(name="Alice",   age=25),
        User(name="Bob",     age=17),
        User(name="Charlie", age=30),
        User(name="Diana",   age=22),
    ]
    for u in users:
        u.save()
    return User
