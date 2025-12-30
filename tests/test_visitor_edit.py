import pytest
from app.models import Visitor


def test_edit_visitor_access(client, app):
    """Test that the edit visitor route is accessible and updates data."""
    # Setup
    with app.app_context():
        from app.models import User, db

        admin = User(email="admin@mecws.org", role="Shelter Supervisor")
        visitor = Visitor(name="Test Visitor", alias="TV")
        db.session.add(admin)
        db.session.add(visitor)
        db.session.commit()
        admin_id = admin.id
        visitor_id = visitor.id

    # Login
    with client.session_transaction() as sess:
        sess["_user_id"] = str(admin_id)
        sess["_fresh"] = True

    # GET
    resp = client.get(f"/visitors/{visitor_id}/edit")
    assert resp.status_code == 200
    assert b"Edit Visitor" in resp.data
    assert b"Test Visitor" in resp.data

    # POST (Update)
    resp = client.post(
        f"/visitors/{visitor_id}/edit",
        data={"name": "Updated Visitor", "alias": "UV"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"Updated Visitor" in resp.data

    # Verify DB
    with app.app_context():
        v = Visitor.query.get(visitor_id)
        assert v.name == "Updated Visitor"
