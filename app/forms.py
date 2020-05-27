from flask_wtf import FlaskForm
from wtforms import BooleanField
from wtforms import PasswordField
from wtforms import StringField
from wtforms import SubmitField
from wtforms.validators import DataRequired
from wtforms.validators import ValidationError
from wtforms.validators import Email
from wtforms.validators import EqualTo
from app.models import User


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')
    remember_me = BooleanField('Remember Me')


class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    #email = StringField('Email', validators=[DataRequired(), Email()]) 
    #email = StringField('email', validators=[InputRequired(), Email(message='Invalid email'), Length(max=50)])
    password = PasswordField('Password', validators=[DataRequired()])
#     password2 = PasswordField(
#         'Repeat Password', validators=[DataRequired(), EqualTo('password')]) 
    submit = SubmitField('Register')
    
#     def validate_username(self, username):
#         user = User.query.filter_by(username=username.data).first()
#         if user is not None:
#             raise ValidationError('Username taken.') 
            
#     def validate_email(self, email):
#         user = User.query.filter_by(email=email.data).first()
#         if user is not None:
#             raise ValidationError('Email address already used.') #
