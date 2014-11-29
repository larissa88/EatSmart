import os
import sys
from sqlalchemy import *
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=True)
    firstLogin = Column(DateTime(timezone=True),
                       nullable=True
                       )
    age = Column(Integer, nullable=True)
    phone = Column(String(250), nullable=True)
    gender = Column(String(250), nullable=True)
    meals = relationship(
        'Meal',
        secondary='meal_user_link'
    )

class HostRating(Base):
    __tablename__ = 'hostRating'
    id = Column(Integer, primary_key=True)
    quality = Column(Integer)
    quantity = Column(Integer)
    ambience = Column(Integer)
    mood = Column(Integer)
    # => one to many relationship => one user many HostRatings
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User', backref=backref('hostratings', order_by=id))
    # for a list of hostratings call user.hostratings
    # Meal und nicht 'Meal' as Meal is not defined at this moment
    meal_id = Column(Integer, ForeignKey('meal.id'))
    meal = relationship('Meal')


class GuestRating(Base):
    __tablename__ = 'guestRating'
    id = Column(Integer, primary_key=True)
    guestRating = Column(Integer)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship('User')
    meal_id = Column(Integer, ForeignKey('meal.id'))
    meal = relationship('Meal')

class Meal(Base):
    __tablename__ = 'meal'
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    typ = Column(String(250), nullable=True)
    date = Column(DateTime(timezone=True),
                        nullable=False
                       )
    dateRegistrationEnd = Column(DateTime(timezone=True),
                        nullable=False
                       )    
    #for many to many relationship: (meal/user)
    users = relationship(
    'User',
    secondary='meal_user_link'
    )
    price = Column(Float,nullable=False)
    address = Column(String(500), nullable=False)
    #"placeGPS": {"longitude": 48.822801, "latitude": 9.165044},
    host_id = Column(Integer, ForeignKey('user.id'))
    host = relationship(User)
    imageUrl = Column(String(250), nullable=True)


class MealUserLink(Base):
    __tablename__ = 'meal_user_link'
    meal_id = Column(Integer, ForeignKey('meal.id'), primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), primary_key=True)



engine = create_engine('sqlite:///sqlalchemy.db')
Base.metadata.create_all(engine)

