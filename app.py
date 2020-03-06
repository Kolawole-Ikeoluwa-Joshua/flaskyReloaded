from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
import hashlib
import os

# Init app
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

# reference key gen
def refgen(key):
	rand = [i for i in key]
	random.shuffle(rand)
	rand = ''.join(rand)
	rand = hashlib.md5(rand.encode('utf-8')).hexdigest()
	return rand

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
        fields = ('name', 'description', 'completed')


project_schema = ProjectSchema()
projects_schema = ProjectSchema(many=True)


class ActionSchema(ma.Schema):
    class Meta:
        fields = ('project_id','description','note')


action_schema = ActionSchema()
actions_schema = ActionSchema(many=True)


@app.route('/api/users/register')
def user_reg():
    # fetch user data
    username = request.json['username']
    password = request.json['password']

    new_user = User(username=username,password=password)


# Run Server
if __name__ == '__main__':
    app.run(debug=True)