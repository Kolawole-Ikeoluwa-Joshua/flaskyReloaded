from flask import Flask, request, jsonify, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import hashlib, uuid
import os
from werkzeug.security import generate_password_hash, check_password_hash
import jwt,datetime

# Init app
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'db.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
        fields = ('id','name', 'description', 'completed')


project_schema = ProjectSchema()
projects_schema = ProjectSchema(many=True)


class ActionSchema(ma.Schema):
    class Meta:
        fields = ('project_id','description','note')


action_schema = ActionSchema()
actions_schema = ActionSchema(many=True)


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
def projects():
    if request.method == 'GET':
        projects = Project.query.all()
        return jsonify(projects_schema.dump(projects))
    elif request.method == 'POST':
        data = request.get_json()
        new_project = Project(name=data['name'],description=data['description'],completed=data['completed'])
        db.session.add(new_project)
        db.session.commit()
        return make_response('Project Added',200)

@app.route('/api/projects/<project_id>',methods=['GET','PUT','DELETE'])
def project(project_id):
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

@app.route('/api/users/auth')
def user_auth():
    auth = request.authorization
    if not auth or not auth.password or not auth.username:
        return make_response('Could not verify',401,{'WWW-Authenticate' : 'Basic realm="Login Required"'})

    user = User.filter_by(username=auth.username).first()

    if not user:
        return make_response('User not found',404,{'WWW-Authenticate' : 'Basic realm="Login Required"'})
    
    if check_password_hash(user.password,auth.password):
        token = jwt.encode({"id":user.id, "exp":datetime.datetime.utcnow() + datetime.timedelta(minutes=30)})

        return jsonify({"token":token.decode('UTF-8')})
        
    return make_response('Could not verify',401,{'WWW-Authenticate' : 'Basic realm="Login Required"'})


# Run Server
if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)