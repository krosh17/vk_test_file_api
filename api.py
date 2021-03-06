import os
import pandas as pd

import werkzeug

from flask import Flask
from flask_httpauth import HTTPBasicAuth
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_restful import Api, Resource, reqparse
from flask_sqlalchemy import SQLAlchemy
from passlib.apps import custom_app_context as pwd_context
from werkzeug.contrib.fixers import ProxyFix

from magic import magic

MAX_FILE_SIZE = 1024 * 1024 * 100
N_FIELDS = 7

user_limits = [20, 5, 2]
ip_limits = [40, 10, 5]

basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'app.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

app.wsgi_app = ProxyFix(app.wsgi_app, num_proxies=1)

db = SQLAlchemy(app)
migrate = Migrate(app, db)
api = Api(app)
auth = HTTPBasicAuth()

limiter_user = Limiter(
    app,
    key_func=lambda: auth.username(),
    default_limits=['{} per day'.format(user_limits[0]),
                    '{} per hour'.format(user_limits[1]),
                    '{} per 5 minute'.format(user_limits[2])]
)

limiter_ip = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=['{} per day'.format(ip_limits[0]),
                    '{} per hour'.format(ip_limits[1]),
                    '{} per 5 minute'.format(ip_limits[2])])


class User(db.Model):
    """
    Class for users with hash from their passwords
    """

    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(32), index = True)
    password_hash = db.Column(db.String(128))

    def hash_password(self, password):
        self.password_hash = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password_hash)


@auth.verify_password
def verify_password(username, password):
    user = User.query.filter_by(username=username).first()
    if not user or not user.verify_password(password):
        return False
    return True


@auth.error_handler
def unauthorized():
    # return 403 instead of 401 to prevent browsers from displaying the default
    # auth dialog
    return 'Unauthorized access', 403


class CreateUser(Resource):
    """
    Create user POST
    """

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('username', type=str, required=True,
                                   help='No username provided',
                                   location='json')
        self.reqparse.add_argument('password', type=str, required=True,
                                   help='No password provided',
                                   location='json')
        super(CreateUser, self).__init__()

    def post(self):
        args = self.reqparse.parse_args()
        username = args['username']
        password = args['password']
        if username is None or password is None:
            return {'message': 'username must be not None'}, 400
        if User.query.filter_by(username=username).first() is not None:
            return {'message': 'username already exist'}, 400

        user = User(username=username)
        user.hash_password(password)
        db.session.add(user)
        db.session.commit()

        return {'username': user.username}, 201


class FileMagic(Resource):
    """
    Find bots and suspect objects with pandas magic
    """

    decorators = [auth.login_required]

    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('file', type=werkzeug.datastructures.FileStorage, required=True,
                                   help='No file provided',
                                   location='files')
        super(FileMagic, self).__init__()

    def post(self):

        args = self.reqparse.parse_args()
        f = args['file']
        try:
            df = pd.read_csv(f)
            df.columns = ['id', 'Click_time', 'Ad_id', 'Advertiser_id', 'Site_id', 'User_id', 'User_IP']
        except:
            return {'message': """first line- columns name
                            each line must contains 7 fields
                            id, "Click time", "Ad id", "Advertiser id", "Site id", "User id", "User IP"
                            separated by ','"""}, 201

        return magic(df)


api.add_resource(FileMagic, '/api/file_upload')
api.add_resource(CreateUser, '/api/create_user')

if __name__ == '__main__':
    app.run(debug=True)
