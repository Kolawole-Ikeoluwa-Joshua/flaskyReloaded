from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import hashlib, uuid
import os
from werkzeug.security import generate_password_hash, check_password_hash
import jwt,datetime
from functools import wraps

# Init app
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'db.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'quantum_mechanics'

# Init db
db = SQLAlchemy(app)
# Init ma
ma = Marshmallow(app)

# Models


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True)
    password = db.Column(db.String(100))
    projects = db.relationship('Project', backref='author')

    def __init__(self, username, password):
        self.username = username
        self.password = password


# User Schema
class UserSchema(ma.Schema):
    class Meta:
        fields = ('id', 'username', 'password')


# Init schema
user_schema = UserSchema()
users_schema = UserSchema(many=True)

class Project(db.Model):
    id = db.Column(db.Integer,nullable=False,primary_key=True)
    name = db.Column(db.String(100))
    description = db.Column(db.String(200))
    completed = db.Column(db.Boolean)
    user_id = db.Column(db.Integer,db.ForeignKey('user.id'))
    actions = db.relationship('Action',backref='project')


class Action(db.Model):
    id = db.Column(db.Integer,nullable=False,primary_key=True)
    project_id = db.Column(db.Integer,db.ForeignKey('project.id'))
    description = db.Column(db.String(200),nullable=False)
    note = db.Column(db.String(250))







class ProjectSchema(ma.Schema):
    class Meta:
        fields = ('id','name', 'description', 'completed','user_id')


project_schema = ProjectSchema()
projects_schema = ProjectSchema(many=True)


class ActionSchema(ma.Schema):
    class Meta:
        fields = ('id','project_id','description','note')


action_schema = ActionSchema()
actions_schema = ActionSchema(many=True)


def token_required(f):
    @wraps(f)
    def decorated(*args,**kwargs):
        token = None

        if 'x-access-token' in request.headers:
            token = request.headers['x-access-token']

            if not token:
                return make_response('Token is missing',404)

        try:
            data = jwt.decode(token,app.config['SECRET_KEY'])
            current_user = User.query.filter_by(id=data['id']).first()
        except:
            return jsonify({"message":"Token is invalid"}),401

        return f(current_user, *args, **kwargs)
    return decorated

@app.route('/api/users/register',methods=['GET','POST'])
def user_reg():
    if request.method == 'POST':
        data = request.get_json()
        hashed_password = generate_password_hash(data['password'],method='sha256')
        user = User(username=data['username'],password=hashed_password)

        db.session.add(user)
        db.session.commit()

        if User.query.filter_by(username=user.username).first():
            return make_response('Registration completed',200)

@app.route('/api/projects',methods=['GET','POST'])
@token_required
def projects(current_user):
    if not current_user:
        return ({"message":"Not logged In"}),401
    if request.method == 'GET':
        projects = Project.query.all()
        return jsonify(projects_schema.dump(projects))
    elif request.method == 'POST':
        data = request.get_json()
        new_project = Project(name=data['name'],description=data['description'],completed=data['completed'],user_id=current_user.id)
        db.session.add(new_project)
        db.session.commit()
        return make_response('Project Added',200)

@app.route('/api/projects/<project_id>',methods=['GET','PUT','DELETE'])
@token_required
def project(current_user,project_id):
    if not current_user:
        return ({"message":"Not logged In"}),401
    if request.method == 'GET':
        project = Project.query.filter_by(id=project_id).first()
        if project:
            return project_schema.jsonify(project)
        return make_response('No such project found',404)
    if request.method == 'PUT':
        project = Project.query.filter_by(id=project_id).first()
        if project:
            data = request.get_json()
            project.name = data['name']
            project.description = data['description']
            project.completed = data['completed']
            db.session.commit()

            return make_response('Updated project',200)
        return make_response('No such project found',404)
    if request.method == 'DELETE':
        project = Project.query.filter_by(id=project_id).first()
        if project:
            db.session.delete(project)
            db.session.commit()
            return make_response('Deleted Project',200)
        return make_response('No such project found',404)

@app.route('/api/users')
def all_users():
    users = User.query.all()
    return jsonify(users_schema.dump(users)),200

@app.route('/api/users/auth')
def user_auth():
    auth = request.authorization
    if not auth or not auth.password or not auth.username:
        return make_response('Could not verify',401,{'WWW-Authenticate' : 'Basic realm="Login Required"'})

    user = User.query.filter_by(username=auth.username).first()

    if not user:
        return make_response('User not found',404,{'WWW-Authenticate' : 'Basic realm="Login Required"'})
    
    if check_password_hash(user.password,auth.password):
        token = jwt.encode({"id":user.id, "exp":datetime.datetime.utcnow() + datetime.timedelta(minutes=30)},app.config['SECRET_KEY'])

        return jsonify({"token":token.decode('UTF-8')})
        
    return make_response('Invalid Password entry',401,{'WWW-Authenticate' : 'Basic realm="Login Required"'})

@app.route('/api/projects/<project_id>/actions',methods=['GET','POST'])
@token_required
def proact(current_user,project_id):
    if not current_user:
        return make_response('Not logged in',401)
    if request.method == 'POST':
        #fetch user
        project = Project.query.filter_by(id=project_id).first()
        data = request.get_json()
        description = data['description']
        note = data['note']
        action = Action(project_id=project.id,description=description,note=note)

        db.session.add(action)
        db.session.commit()
        return make_response(f'Action added for project:{project_id}',200)
    if request.method == 'GET':
        project = Project.query.filter_by(id=project_id).first()
        actions = Action.query.filter_by(project_id=project.id)
        return jsonify(actions_schema.dump(actions)),200

@app.route('/api/actions',methods=['GET'])
@token_required
def actions(current_user):
    if not current_user:
        return make_response('Not logged in',401)
    actions = Action.query.all()
    return jsonify(actions_schema.dump(actions)),200

@app.route('/api/actions/<action_id>')
@token_required
def action(current_user,action_id):
    if not current_user:
        return make_response('Not logged in',401)
    action = Action.query.filter_by(id=action_id).first()
    if action:
        return action_schema.jsonify(action),200
    return jsonify({"message":"No such action found"}),404

@app.route('/api/projects/<project_id>/actions/<action_id>',methods=['GET','PUT','DELETE'])
@token_required
def project_action(current_user,project_id,action_id):
    if not current_user:
       return make_response('Not logged in',401)
    if request.method == 'GET':
        project = Project.query.filter_by(id=project_id).first()
        action = Project.query.filter_by(id=action_id).first()
        if project and action:
            result = Action.query.filter_by(project_id=project.id).all()
            for i in result:
                if i.id == action.id:
                    return action_schema.jsonify(i)
        return make_response('No such action found',404)
    
    if request.method == 'PUT':
        project = Project.query.filter_by(id=project_id).first()
        action = Project.query.filter_by(id=action_id).first()
        data = request.get_json()
        if project and action:
            result = Action.query.filter_by(project_id=project.id).all()
            for i in result:
                if i.id == action.id:
                    if data['description'] and data['note']:
                        i.description = data['description']
                        i.note = data['note']
                        db.session.commit()

                        return make_response('Updated action successfully',200)
                    return make_response('Invalid entry sent',401)
        return make_response('no such action',404)

    if request.method == 'DELETE':
        project = Project.query.filter_by(id=project_id).first()
        action = Project.query.filter_by(id=action_id).first()
        data = request.get_json()
        if project and action:
            result = Action.query.filter_by(project_id=project.id).all()
            for i in result:
                if i.id == action.id:
                    db.session.delete(i)
                    db.session.commit()
                    return make_response('deleted !!',200)
        return make_response('no such action',404)        
                    


# Run Server
if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)