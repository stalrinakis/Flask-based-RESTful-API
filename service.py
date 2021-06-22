import fmt as fmt
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from flask import Flask, request, jsonify, redirect, Response
import json
import uuid
import time

# Connect to our local MongoDB
client = MongoClient('mongodb://mongodb:27017/')

# Choose database
db = client['DSMarket']

# Choose collections
users = db['Users']
prod = db['Products']

# Initiate Flask App
app = Flask(__name__)

users_sessions = {}
users_total_price = {}
users_items = {}


def create_session(username):
    user_uuid = str(uuid.uuid1())
    users_sessions[user_uuid] = (username, time.time())
    users_total_price[user_uuid] = 0
    users_items[user_uuid] = {}

    return user_uuid


def is_session_valid(user_uuid):
    return user_uuid in users_sessions


# Δημιουργία χρήστη
@app.route('/createUser', methods=['POST'])
def create_user():
    # Request JSON data
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')
    if not "name" in data or not "password" in data or not "email" in data or not "category" in data:
        return Response("Information incomplete", status=500, mimetype="application/json")

    userEx = users.find_one({"email": data['email']})
    if userEx == None:
        if data['category'] == "user":
            user = {"email": data['email'], "name": data['name'], "password": data['password'],
                    "category": data['category'], "orderHistory": {}}
        else:
            user = {"email": data['email'], "name": data['name'], "password": data['password'],
                    "category": data['category']}
        users.insert_one(user)

        return Response(data['email'] + " was added to the MongoDB", status=200,
                        mimetype='application/json')  # ΠΡΟΣΘΗΚΗ STATUS
    else:
        return Response("A user with the given email already exists.", status=400,
                        mimetype='application/json')  # ΠΡΟΣΘΗΚΗ STATUS


# Login στο σύστημα
@app.route('/login', methods=['POST'])
def login():
    # Request JSON data
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')
    if not "password" in data or not "email" in data:
        return Response("Information incomplete", status=500, mimetype="application/json")

    user = users.find_one({"email": data['email']})
    if user == None:
        return Response("Wrong email or password.", status=400, mimetype='application/json')  # ΠΡΟΣΘΗΚΗ STATUS
    else:
        if user['password'] == data['password']:
            user_uuid = create_session(data['email'])
            res = {"uuid": user_uuid, "email": data['email']}
            return Response(json.dumps(res), status=200, mimetype='application/json')  # ΠΡΟΣΘΗΚΗ STATUS
        else:
            return Response("Wrong email or password.", status=400, mimetype='application/json')  # ΠΡΟΣΘΗΚΗ STATUS


# Αναζήτηση προϊόντος
@app.route('/Search', methods=['GET'])
def get_product():
    # Request JSON data
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')
    if not ("category" or "name" or "ID" in data):
        return Response("Information incomplete", status=500, mimetype="application/json")

    if "name" in data:
        pro = prod.find({"name": {"$regex": data['name']}}, {'_id': False}).sort("name")
        pro2 = []
        for x in pro:
            if x != None:
                pro2.append(x)
            else:
                return "No product with this name exists."
        return jsonify(pro2)
    if "category" in data:
        pro = prod.find({"category": {"$regex": data['category']}}, {'_id': False}).sort("price")
        pro2 = []
        for x in pro:
            if x != None:
                pro2.append(x)
            else:
                return "No product exists in this category."
        return jsonify(pro2)
    if "ID" in data:
        pro = prod.find({"ID": {"$regex": data['ID']}}, {'_id': False})
        pro2 = []
        for x in pro:
            if x != None:
                pro2.append(x)
            else:
                return "No product with this ID exists."
        return jsonify(pro2)


# Προσθήκη προϊοντος στην Βάση
@app.route('/insertProduct', methods=['POST'])
def create_product():
    # Request JSON data
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')
    if not "name" in data or not "description" in data or not "price" in data or not "category" in data or not "ID" in data or not "stock" in data:
        return Response("Information incomplete", status=500, mimetype="application/json")

    uid = request.headers.get('authorization')
    if is_session_valid(uid):
        usEx = users.find_one({"email": users_sessions[uid][0]})
        is_admin = usEx['category']
        if is_admin != 'admin':
            return "User is not an admin!"
        exist = prod.find_one({"ID": data['ID']})
        if exist == None:
            product = {"name": data['name'], "price": data["price"], "description": data['description'],
                       "category": data['category'], "stock": data['stock'], "ID": data['ID']}
            prod.insert_one(product)
            return Response(data['ID'] + " was added to the MongoDB", status=200,
                            mimetype='application/json')  # ΠΡΟΣΘΗΚΗ STATUS
        else:
            return "Product already exists in database."
    else:
        return Response("User is not authorized.", status=401,
                        mimetype='application/json')  # ΠΡΟΣΘΗΚΗ STATUS


# Διαγραφη προϊοντος στην Βάση
@app.route('/deleteProduct', methods=['DELETE'])
def delete_product():
    # Request JSON data
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')
    if not "ID" in data:
        return Response("Information incomplete", status=500, mimetype="application/json")

    uid = request.headers.get('authorization')
    if is_session_valid(uid):
        usEx = users.find_one({"email": users_sessions[uid][0]})
        is_admin = usEx['category']
        if is_admin != 'admin':
            return "User is not an admin!"
        exist = prod.find_one({"ID": data['ID']})
        if exist != None:
            prod.delete_one(exist)
            return Response(data['ID'] + " was deleted from the MongoDB", status=200,
                            mimetype='application/json')  # ΠΡΟΣΘΗΚΗ STATUS
        else:
            return "Product does not exists in database."
    else:
        return Response("User is not authorized.", status=401,
                        mimetype='application/json')  # ΠΡΟΣΘΗΚΗ STATUS


# Ενημέρωση προϊοντος στην Βάση
@app.route('/updateProduct', methods=['PATCH'])
def update_product():
    # Request JSON data
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')
    if not "ID" in data or not ("name" or "price" or "description" or "stock" in data):
        return Response("Information incomplete", status=500, mimetype="application/json")

    uid = request.headers.get('authorization')
    if is_session_valid(uid):
        usEx = users.find_one({"email": users_sessions[uid][0]})
        is_admin = usEx['category']
        if is_admin != 'admin':
            return "User is not an admin!"
        exist = prod.find_one({"ID": data['ID']})
        if exist != None:
            if "name" in data:
                prod.update_one({"ID": data['ID']},
                                {"$set": {"name": data['name']}})
            if "price" in data:
                prod.update_one({"ID": data['ID']},
                                {"$set": {"price": data['price']}})
            if "description" in data:
                prod.update_one({"ID": data['ID']},
                                {"$set": {"description": data['description']}})
            if "stock" in data:
                prod.update_one({"ID": data['ID']},
                                {"$set": {"stock": data['stock']}})
            return Response(data['ID'] + " was successfully updated in the MongoDB", status=200,
                            mimetype='application/json')  # ΠΡΟΣΘΗΚΗ STATUS
        else:
            return "Product does not exists in database."
    else:
        return Response("User is not authorized.", status=401,
                        mimetype='application/json')  # ΠΡΟΣΘΗΚΗ STATUS


# Προσθήκη προϊοντος στo καλάθι χρήστη
@app.route('/cartItems', methods=['GET'])
def insert_to_cart():
    # Request JSON data
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')
    if not "ID" in data or not "quantity" in data:
        return Response("Information incomplete", status=500, mimetype="application/json")

    uid = request.headers.get('authorization')
    if is_session_valid(uid):
        exist = prod.find_one({"ID": data['ID']})
        if exist != None:
            if data['quantity'] <= 0:
                return "Please enter a valid quantity."
            elif data['quantity'] > exist['stock']:
                return "Not enough stock, avaible stock is %s" % exist['stock']
            else:
                count = data['quantity']
                for key in users_items[uid]:
                    if data['ID'] == key:
                        if (data['quantity'] + users_items[uid][key]) > exist['stock']:
                            return "Not enough stock, avaible stock is %s" % (exist['stock'] - users_items[uid][key])
                        else:
                            count = users_items[uid][key] + data['quantity']
                users_total_price[uid] = users_total_price[uid] + (
                        data['quantity'] * prod.find_one({'ID': data['ID']})['price'])
                temp = {data['ID']: count}
                for x in temp:
                    users_items[uid][x] = temp[x]
                msg = "Total price of cart:"
                fmt = '{:<8}{:<20}{}'
                cart = str(fmt.format("", 'Product_Id', 'Quantity')) + '\n'
                price = str(users_total_price[uid])
                i = 0
                for key in users_items[uid]:
                    i += 1
                    cart = cart + str(fmt.format(i, key, users_items[uid][key])) + '\n'
                return cart + msg + price + '€'
        else:
            return "Product does not exists in database."


    else:
        return Response("User is not authorized.", status=401,
                        mimetype='application/json')  # ΠΡΟΣΘΗΚΗ STATUS


# Εμφάνιση καλαθιού
@app.route('/printCart', methods=['GET'])
def print_cart():
    uid = request.headers.get('authorization')
    if is_session_valid(uid):
        if len(users_items[uid]) == 0:
            return "No items in the cart!"
        msg = "Total price of cart:"
        fmt = '{:<8}{:<20}{}'
        cart = str(fmt.format("", 'Product_Id', 'Quantity')) + '\n'
        price = str(users_total_price[uid])
        i = 0
        for key in users_items[uid]:
            i += 1
            cart = cart + str(fmt.format(i, key, users_items[uid][key])) + '\n'
        return cart + msg + price + '€'



    else:
        return Response("User is not authorized.", status=401,
                        mimetype='application/json')  # ΠΡΟΣΘΗΚΗ STATUS


# Διαγραφή προϊοντος από το  καλάθι
@app.route('/removeFromCart', methods=['DEELTE'])
def remove_from_cart():
    # Request JSON data
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')
    if not "ID" in data:
        return Response("Information incomplete", status=500, mimetype="application/json")

    uid = request.headers.get('authorization')
    if is_session_valid(uid):
        exist = prod.find_one({"ID": data['ID']})
        if exist != None:
            if data['ID'] not in users_items[uid]:
                return "This item does not exist in your cart."
            else:
                users_total_price[uid] = users_total_price[uid] - (
                        users_items[uid][data['ID']] * prod.find_one({'ID': data['ID']})['price'])
                users_items[uid].pop(data['ID'])
                rem = "The product was successfully removed from the cart. \n"
                if len(users_items[uid]) == 0:
                    return "No items in the cart!"
                else:
                    msg = "Total price of cart:"
                    fmt = '{:<8}{:<20}{}'
                    cart = str(fmt.format("", 'Product_Id', 'Quantity')) + '\n'
                    price = str(users_total_price[uid])
                    i = 0
                    for key in users_items[uid]:
                        i += 1
                        cart = cart + str(fmt.format(i, key, users_items[uid][key])) + '\n'
                return rem + cart + msg + price + '€'
        else:
            return "Product does not exists in database."


    else:
        return Response("User is not authorized.", status=401,
                        mimetype='application/json')  # ΠΡΟΣΘΗΚΗ STATUS


# Αγορα προιοντων
@app.route('/buyItems', methods=['POST'])
def buy_items():
    # Request JSON data
    data = None
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content", status=500, mimetype='application/json')
    if data == None:
        return Response("bad request", status=500, mimetype='application/json')
    if not "card" in data:
        return Response("Information incomplete", status=500, mimetype="application/json")

    uid = request.headers.get('authorization')
    if is_session_valid(uid):
        if len(users_items[uid]) == 0:
            return "No items in the cart!"
        if len(str(data['card'])) == 16 and type(data['card']) == int:
            msg = "Total price of cart:"
            msg2 = "Items bought: \n"
            msg3 = "Thanks fou your preference!"
            fmt = '{:<8}{:<20}{}'
            cart = str(fmt.format("", 'Product_Id', 'Quantity')) + '\n'
            price = str(users_total_price[uid])
            i = 0
            this_cart = {}
            new_order = {}
            old_order = {}
            for key in users_items[uid]:
                i += 1
                cart = cart + str(fmt.format(i, key, users_items[uid][key])) + '\n'
                this_cart[key] = users_items[uid][key]
                item = prod.find_one({"ID": key})
                prod.update_one({"ID": key},
                     {"$set": {"stock": item['stock'] - this_cart[key]}})
            this_cart['Total Price:'] = price
            us = users.find_one({"email": users_sessions[uid][0]})
            history = us['orderHistory']
            new_order['order' + str(len(history) + 1)] = this_cart
            for key in history:
                old_order[key] = history[key]
            new_order.update(old_order)
            users.update_one({"email": users_sessions[uid][0]},
                             {"$set": {"orderHistory": new_order}})
            users_total_price[uid] = 0
            users_items[uid] = {}

            return msg2 + cart + msg + price + '€' + '\n' + msg3

        else:
            return "Wrong card number, please try again."

    else:
        return Response("User is not authorized.", status=401,
                        mimetype='application/json')  # ΠΡΟΣΘΗΚΗ STATUS


# Εμφάνιση Ιστορικό Παραγγελιών
@app.route('/printHistory', methods=['GET'])
def print_history():
    uid = request.headers.get('authorization')
    if is_session_valid(uid):
        usEx = users.find_one({"email": users_sessions[uid][0]})
        history = usEx['orderHistory']
        if len(history) == 0:
            return "No previous orders!"
        return history
    else:
        return Response("User is not authorized.", status=401,
                        mimetype='application/json')  # ΠΡΟΣΘΗΚΗ STATUS

# Διαγραφή Χρήστη
@app.route('/removeUser', methods=['DELETE'])
def remove_user():
    uid = request.headers.get('authorization')
    if is_session_valid(uid):
        usEx = users.find_one({"email": users_sessions[uid][0]})
        users.delete_one(usEx)
        del users_sessions[uid]
        return "User was Deleted!"
    else:
        return Response("User is not authorized.", status=401,
                        mimetype='application/json')  # ΠΡΟΣΘΗΚΗ STATUS


# Εκτέλεση flask service σε debug mode, στην port 5000.
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
