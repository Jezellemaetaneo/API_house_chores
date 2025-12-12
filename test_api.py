import pytest
from app import app, db, User
import json

@pytest.fixture
def client():
    app.config['TESTING'] = True
    # configure a temporary sqlite DB for tests to isolate from MySQL (optional)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # seed minimal data: user + members + chores + assignment
            user = User(username='teacher', password='demo123')
            db.session.add(user)
            db.session.commit()
        yield client
        with app.app_context():
            db.drop_all()

def get_token(client):
    rv = client.post('/auth/login', json={'username':'teacher','password':'demo123'})
    assert rv.status_code == 200
    data = rv.get_json()
    return data['access_token']

def test_member_crud_and_formatting(client):
    token = get_token(client)
    headers = {'Authorization': f'Bearer {token}'}

    # create member
    rv = client.post('/members', json={'name':'Alice'}, headers=headers)
    assert rv.status_code == 201
    j = rv.get_json()
    assert j['name'] == 'Alice' or 'name' in j

    # get members xml
    rv = client.get('/members?format=xml', headers=headers)
    assert rv.status_code == 200
    assert b'<response>' in rv.data

def test_chore_crud_and_search(client):
    token = get_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    # create chore
    rv = client.post('/chores', json={'chore_name':'Vacuum','frequency':'Weekly'}, headers=headers)
    assert rv.status_code == 201
    # search
    rv = client.get('/chores?q=Vacuum', headers=headers)
    assert rv.status_code == 200
    data = rv.get_json()
    assert 'chores' in data

def test_assignment_crud_edge_cases(client):
    token = get_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    # Create member & chore first
    client.post('/members', json={'name':'Bobby'}, headers=headers)
    client.post('/chores', json={'chore_name':'Mop','frequency':'Daily'}, headers=headers)
    # try to create assignment with invalid member
    rv = client.post('/assignments', json={'member_id':999,'chore_id':1,'assigned_date':'2025-01-01'}, headers=headers)
    assert rv.status_code == 404
    # correct create
    # get actual member id and chore id from list endpoints
    m = client.get('/members', headers=headers).get_json()['members'][0]
    c = client.get('/chores', headers=headers).get_json()['chores'][0]
    rv = client.post('/assignments', json={'member_id':m['member_id'],'chore_id':c['chore_id'],'assigned_date':'2025-01-10'}, headers=headers)
    assert rv.status_code == 201
    aid = rv.get_json().get('assignment_id') or rv.get_json().get('assignment_id')
    # update assignment
    rv = client.put(f'/assignments/{aid}', json={'is_completed':True}, headers=headers)
    assert rv.status_code == 200
    # delete assignment
    rv = client.delete(f'/assignments/{aid}', headers=headers)
    assert rv.status_code == 204
