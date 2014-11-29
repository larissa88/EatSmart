import json
import logging
import os
import uuid
import math
from datetime import datetime
import requests
from sqlalchemy_declarative import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound


from flask import Flask, jsonify, request
app = Flask(__name__)


@app.route('/meals/create', methods=['POST'])
def meal_create():
    name = request.form['name']
    DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

    date = datetime.strptime(request.form['date'], DATETIME_FORMAT)
    dateRegistrationEnd = datetime.strptime(request.form['dateRegistrationEnd'], DATETIME_FORMAT)
    price = request.form['price']
    host = request.form['host']
    address = request.form['address']
    typ = request.form['typ']
    session = DBSession()
    host = session.query(User).filter(User.id == host).one()
    meal = Meal(name=name,
                date=date,
                dateRegistrationEnd=dateRegistrationEnd,
                price=price,
                address=address,
                typ=typ,
                host=host,
                latitude=48,
                longitude=10)
    session.add(meal)
    session.commit()
    mealDic = {"success": True, "mealId": meal.id}
    session.close()
    return jsonify(mealDic)
    #pass user id, datum, meal name,... 


@app.route('/meals/<mealId>/delete', methods=['POST'])
def meal_delete(mealId):
    session = DBSession()
    try:
        meal= session.query(Meal).filter(Meal.id==mealId).one()
        session.delete(meal)
        session.commit()
    except NoResultFound:
        return jsonify({"success": False, "error": {"message": "No Meal Found with this id"}})
    session.close()

    return jsonify({"success": True})


def getWalkingDistanceFromGoogle(startCoordinats, listofDestinations):
    origins = str(startCoordinats[0])+","+str(startCoordinats[1])
    destinations = "|".join(listofDestinations).replace(" ", "+")
    googleMapsApiUrl = "http://maps.googleapis.com/maps/api/distancematrix/json?origins={0}&destinations={1}&mode=walking".format(origins,destinations)
    response = requests.get(googleMapsApiUrl).json()

    return response.get('rows')[0].get('elements')

@app.route('/meals/<mealId>/information', methods=['GET'])
def meal_get_information(mealId):
    session = DBSession()
    try:
        meal= session.query(Meal).filter(Meal.id==mealId).one()
        host = meal.host
        responseDic = {"success": True,
                   "mealId": mealId,
                   "typ": meal.typ,
                   "date": meal.date,
                   "dateRegistrationEnd": meal.dateRegistrationEnd,
                   "price": meal.price,
                   "place": meal.address,
                   "walking_distance": 1560,
                   "guest_attending": len(meal.users),
                   "placeGPS": {"latitude": 48.822801, "longitude": 9.165044},
                   "host": {"hostname": host.name, "age": host.age, "phone": host.phone, "gender": host.gender, "hostId": host.id},
                   "image": "http://placekitten.com/g/200/300"}
        session.commit()
    except NoResultFound:
        return jsonify({"success": False, "error": {"message": "No Meal Found with this id"}})
    session.close()
    
    return jsonify(responseDic)
#get guests, date,...


@app.route('/meals/<mealId>/user/<userId>', methods=['POST'])
def meal_user_add(mealId, userId):
    session = DBSession()
    try:
        meal = session.query(Meal).filter(Meal.id == mealId).one()
        user = session.query(User).filter(User.id == userId).one()
        meal.users.append(user)
        session.add(meal)
        session.commit()
    except NoResultFound:
        pass
    session.close()
    responseDic = {"success": True, "mealId": userId}
    return jsonify(responseDic)

@app.route('/meals/<mealId>/user/<userId>', methods=['DELETE'])
def meal_user_remove(mealId, userId):
    session = DBSession()
    try:
        meal = session.query(Meal).filter(Meal.id == mealId).one()
        user = session.query(User).filter(User.id == userId).one()
        meal.users.remove(user)
        session.add(meal)
        session.commit()
    except NoResultFound:
        pass
    except ValueError:
        pass
    session.close()
    responseDic = {"success": True, "mealId": userId}
    return jsonify(responseDic)

@app.route('/meals/search/<float:latitude>/<float:longitude>', methods=['GET'])
def meal_search(latitude, longitude):
    #squareLat, squareLong = getCloseByCoordinats(latitude, longitude, 5000)
    session = DBSession()
    try:
        diffLatitude = 5000/110574
        diffLongitude = 110574*math.cos(math.radians(longitude))
        meals = session.query(Meal)\
        .filter(and_(Meal.longitude <= longitude+diffLongitude, Meal.longitude >= longitude-diffLongitude))\
        .filter(and_(Meal.latitude <= latitude+diffLatitude, Meal.latitude >= latitude-diffLatitude))\
        .all()

        destinations = []
        for meal in meals:
            destinations.append(meal.address)
        walkingTimes = getWalkingDistanceFromGoogle((latitude,longitude),destinations)
        resultList = []
        for i, meal in enumerate(meals):
            resultList.append(
                {"mealId": meal.id,
                 "mealName": meal.name,
                 "walkingTime": walkingTimes[i].get('duration').get('value'),
                 "date": meal.date,
                 # TODO return average host rating
                 "rating": 5,  
                 "price": meal.price})
    except NoResultFound:
        pass
    responseDic = {"success": True, "results": resultList}
    return jsonify(responseDic)
    #pass time, typ

@app.route('/rating/host/<uhostID>', methods=['POST'])
def rating_host_add(uhostId):
    pass
        #pass uID => to identify if user really participated in meal
        #check if bewertung exists
    #pass userId,mealID

@app.route('/rating/host/average/<uhostID>', methods=['GET'])
def rating_host_average_get(uhostID):
    hostRatingDic = {"success":True}
    hostRatingDic.update(calculateAverageHostRating(uhostID))
    return jsonify(hostRatingDic)


@app.route('/rating/guest/<userId>', methods=['POST'])
def rating_guest_add(userId):
    uhostId = request.form['uhostId']
    uhostId = request.form['uhostId']
    print(uhostId)
    mealId = request.form['mealId']
    _guestRating = request.form['guestRating']
    session = DBSession()
    alreadyAdded = False
    try:
        guestRatingsForThisUser = session.query(GuestRating).filter(and_(GuestRating.user_id == userId, GuestRating.meal_id == mealId)).one()
    except NoResultFound:
        try:
            guest = session.query(User).filter(User.id == userId).one()
            meal = session.query(Meal).filter(Meal.id == mealId).one()
            #host muss man nicht zwingend erstellen, man könnte id auch direkt weitergeben, aber so überprüfung ob host für diese id existiert
            host = session.query(User).filter(User.id == uhostId).one()
            new_rating = GuestRating(guestRating = _guestRating, user = guest, meal = meal, host_id = host.id)
            session.add(new_rating)
            session.commit()
        except NoResultFound:
            return jsonify({"error": True})
    session.close()
    return jsonify({'success': "1"})


@app.route('/rating/guest/average/<userId>', methods=['GET'])
def rating_guest_average_get(userId):
    guestRatingDic = {"success":True, "guestRating":calculateAverageGuestRating(userId)}
    return jsonify(guestRatingDic)

@app.route('/user/create', methods=['POST'])
def createUser():

    new_user = User()
    session = DBSession()
    session.add(new_user)
    session.commit()
    userDic = {"success": True, "userId":new_user.id}
    session.close()
    return jsonify(userDic)


@app.route('/user/<userId>/information', methods=['GET'])
def getUserInformation(userId):
    hostRating = calculateAverageHostRating(userId)
    user = session.query(User).filter(User.id == userId).one()
    userDic = {"success": True,
                "userId":userId,
                #könnte auch None sein, wenn name nicht gesetzt ist
                "name":user.name,
                "firstLogin": user.firstLogin,
                "age":user.age,
                "phone":user.phone,
                "hostRating":hostRating,
                "guestRating":calculateAverageGuestRating(userId)}

    return jsonify(userDic);


@app.route('/user/<userId>/information', methods=['PUT'])
def setUserInfromation(userId):
    age = request.headers.get('age')
    phone = request.headers.get('phone')
    name = request.headers.get('name')
    gender = request.headers.get('gender')
    session = DBSession()
    try:
        user = session.query(User).filter(User.id == userId).one()
        user.age = age
        user.phone = phone
        user.name = name
        user.gender = gender
        session.add(user)
        session.commit()
    except NoResultFound:
        pass
    session.close()
    return jsonify({"success": True})

def calculateAverageGuestRating(userId):
    session = DBSession()
    user = session.query(User).filter(User.id == userId).one()
    averageGuestRating = 0
    for guestrate in user.guestratings:
        print(averageGuestRating)
        averageGuestRating += guestrate.guestRating
    numberOfRatings = len(user.guestratings)
    session.close()
    if(numberOfRatings == 0):
        return None
    else:
        return averageGuestRating/numberOfRatings

def calculateAverageHostRating(userId):
    session = DBSession()
    user = session.query(User).filter(User.id == userId).one()
    averageQuality = 0
    averageQuantity = 0
    averageAmbience = 0
    averageMood = 0
    numberOfRatings = len(user.hostratings)
    if(numberOfRatings !=0):
        comments = []
        for hostrate in user.hostratings:
            averageQuality += hostrate.quality
            averageQuantity += hostrate.quantity
            averageAmbience += hostrate.ambience
            averageMood += hostrate.mood
            if hostrate.comment is not None:
                l.append(hostrate.comment)
        session.close()
        if len(comments)==0:
            comments = None
        return{"quality":averageQuality/numberOfRatings,
                    "quantity":averageQuantity/numberOfRatings,
                    "ambience":averageAmbience/numberOfRatings,
                    "mood":averageMood/numberOfRatings,
                    "comments":comments}
    else:
        session.close()
        return {"quality":None,
                    "quantity":None,
                    "ambience":None,
                    "mood":None,
                    "comments":None}

if __name__ == '__main__':
    engine = create_engine('sqlite:///sqlalchemy.db')
    DBSession = sessionmaker(bind=engine)
    app.run(debug=True, host='0.0.0.0')

    #version api
