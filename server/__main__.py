import math
from datetime import datetime
import requests
from sqlalchemy_declarative import *
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from flask import Flask, jsonify, request
app = Flask(__name__)
DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'


@app.route('/0.2.1b/meals/create', methods=['POST'])
def meal_create():
    name = request.form['name']
    date = datetime.strptime(request.form['date'], DATETIME_FORMAT)
    dateRegistrationEnd = datetime.strptime(
        request.form['dateRegistrationEnd'],
        DATETIME_FORMAT)
    price = request.form['price']
    host = request.form['host']
    address = request.form['address']
    typ = request.form['typ']
    maxGuests = request.form['maxGuests']
    description = request.form['description']
    nutrition_typ = request.form['nutrition_typ']
    session = DBSession()
    try:
        host = session.query(User).filter(User.id == host).one()
    except NoResultFound:
        return jsonify({"success": False,
                        "error": {"message": "No User Found with this id."}})
    latitude, longitude = getGPSCoordinatesFromGoogle(address)
    meal = Meal(name=name,
                date=date,
                dateRegistrationEnd=dateRegistrationEnd,
                maxGuests=maxGuests,
                price=price,
                address=address,
                typ=typ,
                nutrition_typ=nutrition_typ,
                host=host,
                latitude=latitude,
                longitude=longitude,
                description=description)
    session.add(meal)
    session.commit()
    mealDic = {"success": True, "mealId": meal.id}
    session.close()
    return jsonify(mealDic)
    # pass user id, datum, meal name,...


@app.route('/0.2.1b/meals/<mealId>', methods=['DELETE'])
def meal_delete(mealId):
    session = DBSession()
    try:
        meal = session.query(Meal).filter(Meal.id == mealId).one()
        session.delete(meal)
        session.commit()
    except NoResultFound:
        return jsonify({"success": False,
                        "error": {"message": "No Meal Found with this id."}})
    session.close()

    return jsonify({"success": True})


@app.route('/0.2.1b/meals/<mealId>', methods=['GET'])
def meal_get_information(mealId):
    session = DBSession()
    try:
        meal = session.query(Meal).filter(Meal.id == mealId).one()
        host = meal.host
        reviews = []
        for rating in meal.host.hostratings:
            if rating.comment:
                reviews.append(rating.comment)
        responseDic = {"success": True,
                       "mealId": mealId,
                       "typ": meal.typ,
                       "date": meal.date,
                       "dateRegistrationEnd": meal.dateRegistrationEnd,
                       "price": meal.price,
                       "place": meal.address,
                       "maxGuests": meal.maxGuests,
                       "guest_attending": len(meal.users),
                       "reviews": reviews,
                       "nutrition_typ": meal.nutrition_typ,
                       "description": meal.description,
                       "placeGPS": {
                           "latitude": meal.latitude,
                           "longitude": meal.longitude},
                       "host": {
                           "hostname": host.name,
                           "age": host.age,
                           "phone": host.phone,
                           "gender": host.gender,
                           "hostId": host.id,
                           "registerdsince": host.firstLogin,
                           "image": meal.host.imageUrl},
                       }
        session.commit()
    except NoResultFound:
        return jsonify({"success": False,
                        "error": {"message": "No Meal Found with this id"}})
    session.close()

    return jsonify(responseDic)
#get guests, date,...


@app.route('/0.2.1b/meals/<mealId>/user/<userId>', methods=['POST'])
def meal_user_add_request(mealId, userId):
    session = DBSession()
    try:
        meal = session.query(Meal).filter(Meal.id == mealId).one()
        user = session.query(User).filter(User.id == userId).one()
        meal.unconfirmedUsers.append(user)
        session.add(meal)
        session.commit()
    except NoResultFound:
        return jsonify({"success": False,
                        "error": {"message": "No User or Meal found with this id"}})
    session.close()
    responseDic = {"success": True, "mealId": userId}
    return jsonify(responseDic)


@app.route('/0.2.1b/meals/<mealId>/user/<userId>', methods=['DELETE'])
def meal_remove_unconfirmed_user(mealId, userId):
    session = DBSession()
    try:
        meal = session.query(Meal).filter(Meal.id == mealId).one()
        user = session.query(User).filter(User.id == userId).one()
        meal.unconfirmedUsers.remove(user)
        session.add(meal)
        session.commit()
    except NoResultFound:
        return jsonify({"success": False,
                        "error": {"message": "No User or Meal found with this id"}})
    except ValueError:
        return jsonify({"success": False,
                        "error": {"message": "This User was not there in the first place"}})
    session.close()
    responseDic = {"success": True, "mealId": userId}
    return jsonify(responseDic)


@app.route('/0.2.1b/meals/<mealId>/user/<userId>', methods=['PUT'])
def meal_confirm_unconfirmed_user(mealId, userId):
    print('called')
    session = DBSession()
    try:
        meal = session.query(Meal).filter(Meal.id == mealId).one()
        user = session.query(User).filter(User.id == userId).one()
        try:
            meal.unconfirmedUsers.remove(user)
            #just add to list if it was in the confirmations list before.
            if(len(meal.users) < meal.maxGuests):
                meal.users.append(user)
        except ValueError:
            return jsonify({"success": False,
                        "error": {"message": "This User was not there in the first place"}})
        session.add(meal)
        session.commit()
    except NoResultFound:
        return jsonify({"success": False,
                        "error": {"message": "No User or Meal found with this id"}})
    mailToAccepted(userId, mealId)
    #TO DO Error Respone, konnte nicht confirmed werden
    #confirmed, nicht confirmed
    session.close()
    responseDic = {"success": True, "mealId": userId}
    return jsonify(responseDic)


@app.route('/0.2.1b/meals/search/<float:latitude>/<float:longitude>', methods=['GET'])
def meal_search(latitude, longitude):
    price = request.args.get('price', 30)
    walkingtime = request.args.get('walkingTime', 3600)
    lowestRating = request.args.get('lowestRating', 1)
    typ = request.args.get('typ', None)
    date = datetime.strptime(request.args.get('date', "2013-11-29 12:00:00"), DATETIME_FORMAT)
    #squareLat, squareLong = getCloseByCoordinats(latitude, longitude, 5000)
    session = DBSession()
    try:
        diffLatitude = 5000/110574
        diffLongitude = 110574*math.cos(math.radians(longitude))
        meals = session.query(Meal)\
            .filter(and_(Meal.longitude <= longitude+diffLongitude,
                         Meal.longitude >= longitude-diffLongitude))\
            .filter(and_(Meal.latitude <= latitude+diffLatitude,
                         Meal.latitude >= latitude-diffLatitude))\
            .filter(Meal.price <= price)\
            .filter(Meal.date >= date)\
            .all()
        if len(meals) == 0:
            return jsonify({"success": True, "results": []})
        destinations = []
        for meal in meals:
            destinations.append(meal.address)
        walkingTimes = getWalkingDistanceFromGoogle((latitude, longitude), destinations)
        resultList = []
        for i, meal in enumerate(meals):
            if meal.maxGuests <= len(meal.users):
                continue
            if walkingTimes[i].get('duration').get('value') > walkingtime:
                continue
            if typ:
                if typ != meal.typ:
                    continue
            rating = calculateTotalAverageHostRating(meal.host.id)
            numberOfRatings = getNumberOfRatings(meal.host.id)
            resultList.append(
                {"mealId": meal.id,
                 "mealName": meal.name,
                 "walkingTime": walkingTimes[i].get('duration').get('value'),
                 "date": meal.date,
                 "maxGuests": meal.maxGuests,
                 "guest_attending": len(meal.users),
                 "address": meal.address,
                 "placeGPS": {"latitude": meal.latitude, "longitude": meal.longitude},
                 "imageUrl": "http://placekitten.com/g/200/300", # change back to image value
                 "rating": rating,
                 "numberOfRatings": numberOfRatings,
                 "price": meal.price,
                 "typ": meal.typ})
    except NoResultFound:
        return jsonify({"success": False,
                        "error": {"message": "No User or Meal found with this id"}})
    responseDic = {"success": True, "results": resultList}
    return jsonify(responseDic)
    #pass time, typ


@app.route('/0.2.1b/rating/host/<uhostId>', methods=['POST'])
def rating_host_add(uhostId):
    userId = int(request.form['userId'])
    mealId = int(request.form['mealId'])
    quality = request.form['quality']
    quantity = request.form['quantity']
    onTime = request.form['onTime']
    mood = request.form['mood']

    try:
        comment = request.form['comments']
    except Exception:
        comment = None

    alreadyAdded = False
    session = DBSession()
    hostRatingsForThisHostAndMeal = session.query(HostRating).filter(and_(HostRating.host_id == uhostId, HostRating.meal_id == mealId)).all()
    for hostRate in hostRatingsForThisHostAndMeal:
        if(hostRate.user_id==userId):
            alreadyAdded = True
    if not alreadyAdded:
        #pass userID => to identify if user really participated in meal => TODO
        host = session.query(User).filter(User.id == uhostId).one()
        meal = session.query(Meal).filter(Meal.id == mealId).one()
        user = session.query(User).filter(User.id == userId).one()
        hostRate = HostRating(quality = quality, quantity = quantity,onTime = onTime, mood = mood,comment = comment, host = host, meal = meal, user_id = user.id)
        session.add(hostRate)
        session.commit()
    session.close()
    return jsonify({'success': 1})

@app.route('/0.2.1b/rating/host/average/<uhostID>', methods=['GET'])
def rating_host_average_get(uhostID):
    hostRatingDic = {"success":True}

    hostRatingDic.update(calculateAverageHostRating(uhostID))
    return jsonify(hostRatingDic)


@app.route('/0.2.1b/rating/guest/<userId>', methods=['POST'])
def rating_guest_add(userId):
    uhostId = request.form['uhostId']
    mealId = request.form['mealId']
    _guestRating = request.form['guestRating']
    session = DBSession()
    alreadyAdded = False
    try:
        guestRatingsForThisUserAndMeal = session.query(GuestRating).filter(and_(GuestRating.user_id == userId, GuestRating.meal_id == mealId)).one()
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


@app.route('/0.2.1b/rating/guest/average/<userId>', methods=['GET'])
def rating_guest_average_get(userId):
    guestRatingDic = {"success":True, "guestRating":calculateAverageGuestRating(userId)}
    return jsonify(guestRatingDic)

@app.route('/0.2.1b/user/create', methods=['POST'])
def createUser():

    new_user = User()
    session = DBSession()
    session.add(new_user)
    session.commit()
    userDic = {"success": True, "userId":new_user.id}
    session.close()
    return jsonify(userDic)


@app.route('/0.2.1b/user/<userId>/information', methods=['GET'])
def getUserInformation(userId):
    hostRating = calculateAverageHostRating(userId)
    user = session.query(User).filter(User.id == userId).one()
    userDic = {"success": True,
               "userId": userId,
               "name": user.name,
               "firstLogin": user.firstLogin,
               "age": user.age,
               "phone": user.phone,
               "gender": user.gender,
               "hostRating": hostRating,
               "guestRating": calculateAverageGuestRating(userId)}

    return jsonify(userDic)


@app.route('/0.2.1b/user/<userId>/information', methods=['PUT'])
def setUserInfromation(userId):
    age = request.headers.get('age')
    phone = request.headers.get('phone')
    name = request.headers.get('name')
    gender = request.headers.get('gender')
    email = request.headers.get('email')
    session = DBSession()
    try:
        user = session.query(User).filter(User.id == userId).one()
        user.age = age
        user.phone = phone
        user.name = name
        user.gender = gender
        user.email = email
        session.add(user)
        session.commit()
    except NoResultFound:
        return jsonify({"success": False,
                        "error": {"message": "No User found with this id"}})
    session.close()
    return jsonify({"success": True})


def  mailToAccepted(userId, mealId):
    try:
        session = DBSession()

        user = serssion.query(User).filter(User.id == userId).one()
        payload = {'to': user.email, 'from': 'info@eatcookNmeet.com', 'html': render_template('index.html', **locals())}
        r = requests.post("http://httpbin.org/post", data=payload)
    except NoResultFound:
        pass

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

def calculateTotalAverageHostRating(userId):
    dic = calculateAverageHostRating(userId)
    if not dic.get('quality'):
        return 0
    return(int(round(float((dic.get('quality')+dic.get('quantity')+dic.get('mood')+dic.get('onTime'))/4))))


def getNumberOfRatings(userId):
    session = DBSession()
    numberOfRatings = len(session.query(HostRating).filter(HostRating.host_id == userId).all())
    session.close()
    return numberOfRatings


def calculateAverageHostRating(userId):
    session = DBSession()
    user = session.query(User).filter(User.id == userId).one()
    averageQuality = 0
    averageQuantity = 0
    averageonTime = 0
    averageMood = 0
    numberOfRatings = len(user.hostratings)
    if(numberOfRatings != 0):
        comments = []
        for hostrate in user.hostratings:
            averageQuality += hostrate.quality
            averageQuantity += hostrate.quantity
            averageonTime += hostrate.onTime
            averageMood += hostrate.mood
            if hostrate.comment is not None:
                l.append(hostrate.comment)
        session.close()
        if len(comments) == 0:
            comments = None
        return{"quality": averageQuality/numberOfRatings,
               "quantity": averageQuantity/numberOfRatings,
               "onTime": averageonTime/numberOfRatings,
               "mood": averageMood/numberOfRatings,
               "comments": comments}
    else:
        session.close()
        return {"quality": None,
                "quantity": None,
                "onTime": None,
                "mood": None,
                "comments": None}


def getWalkingDistanceFromGoogle(startCoordinats, listofDestinations):
    origins = str(startCoordinats[0])+","+str(startCoordinats[1])
    destinations = "|".join(listofDestinations).replace(" ", "+")
    googleMapsApiUrl = "http://maps.googleapis.com/maps/api/distancematrix/json?origins={0}&destinations={1}&mode=walking".format(origins,destinations)
    try:
        response = requests.get(googleMapsApiUrl).json().get('rows')[0]
        return response.get('elements')
    except IndexError:
        pass

    return None


def getGPSCoordinatesFromGoogle(address):
    url = "https://maps.google.com/maps/api/geocode/json?address={0}&sensor=false".format(address.replace(" ","+"))
    response = requests.get(url).json().get('results')[0].get('geometry').get('location')
    return response.get('lat'), response.get('lng')


def meal_user_remove(mealId, userId):
    session = DBSession()
    try:
        meal = session.query(Meal).filter(Meal.id == mealId).one()
        user = session.query(User).filter(User.id == userId).one()
        meal.users.remove(user)
        session.add(meal)
        session.commit()
    except NoResultFound:
        return jsonify({"success": False,
                        "error": {"message": "No User or Meal found with this id"}})
    except ValueError:
        return jsonify({"success": False,
                        "error": {"message": "The User was not here in the first place"}})
    session.close()
    responseDic = {"success": True, "mealId": userId}
    return jsonify(responseDic)


if __name__ == '__main__':
    mysqlhost = '127.0.0.1'
    mysqlport = 3306
    mysqluser = 'eatsmart'
    mysqlpassword = 'test'
    mysqldb = 'EatSmart'
    engine = create_engine("mysql+pymysql://{0}:{1}@{2}/{3}?charset=utf8"
                           .format(mysqluser,
                                   mysqlpassword,
                                   mysqlhost,
                                   mysqldb),
                           encoding='utf-8', echo=False)
    Base.metadata.create_all(engine)
    package_directory = os.path.dirname(os.path.abspath(__file__))
    #logging.basicConfig(filename=package_directory+'/logs/kolumbus-server.log',
    #                    level=logging.DEBUG)

    #logging.info("Connected to mysql on {0}:{1}/{2}".format(
    #    mysqlhost, mysqlport, mysqldb))
    DBSession = sessionmaker(bind=engine)
    # app.register_error_handler(Exception, error_handler)
    app.run(debug=True, host='0.0.0.0')

    #version api
