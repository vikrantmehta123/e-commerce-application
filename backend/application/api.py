from flask import request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity, create_access_token
from application import cache, app
from application.utils import *
from bcrypt import checkpw
from application.dal import *
from application.fts import search_in_database
from flask import Blueprint
import json
from celery.result import AsyncResult

api = Blueprint('api', __name__, url_prefix='/api/v1')

# region Pending Approvals for admin
@api.route('/pending_requests', methods=['GET'])
@jwt_required()
@role_required('admin')
@cache.cached(timeout=60)
def get_pending_request_count():
    category_req_count = PendingRequestsDAL.get_pending_category_request_count()
    manager_reqs_count = PendingRequestsDAL.get_pending_manager_approval_request_count()
    return jsonify({"message": "successfully fetched requests", 
                    "category_requests": category_req_count,
                    "manager_requests" : manager_reqs_count
                    }), 200

@api.route('/pending_requests/<req_type>', methods=['GET'])
@jwt_required()
@role_required('admin')
def get_pending_requests(req_type):
    if req_type not in ['manager', 'category']:
        return jsonify({'message':'invalid request type. Must be one of "manager" or "category"'}), 400
    
    if req_type == 'category':
        reqs = PendingRequestsDAL.category_requests_get_pending_requests()
    else:
        reqs = PendingRequestsDAL.manager_requests_get_pending_requests()

    return jsonify({"message" :"succeffully fetched", "requests" : [req.to_json() for req in reqs]}), 200

@api.route('/pending_requests/<req_type>/approval', methods=['POST'])
@jwt_required()
@role_required("admin")
def pending_requests_approval(req_type):
    if req_type not in ['manager', 'category']:
        return jsonify({'message':'invalid request type. Must be one of "manager" or "category"'}), 400
    data = request.json
    if req_type == 'category':
        PendingRequestsDAL.category_requests_update_approval_status(data['request_id'], data['status'])
    else:
        PendingRequestsDAL.manager_requests_update_approval_status(data['request_id'], data['status'])
    return jsonify({"message" : "successfully executed"}), 200

@api.route('/manager/category_request', methods=["POST"])
@jwt_required()
@role_required("manager")
def request_category_action():
    current_user = get_jwt_identity()
    user_id =  current_user['id']

    unique_filename = None
    category_id = request.form.get('category_id') if 'category_id' in request.form else None

    # Save the file
    if 'file' in request.files:
        file = request.files['file']
        unique_filename = generate_unique_name_for_file(file=file)
        file_storage_path = create_image_path(unique_filename, "categories")
        file.save(file_storage_path)
    
    try:
        req_type=request.form.get('req_type')
        cat_name=request.form.get('category_name')
        cat_desc=request.form.get('category_description') if req_type != 'delete' else None
        img_path=unique_filename if req_type != 'delete' else None

        req = PendingRequestsDAL.category_requests_create_request(
            user_id=user_id, cat_name=cat_name,
            cat_desc=cat_desc, img_path=img_path, 
            req_type=request.form.get('req_type'), remark=request.form.get('remark'), 
            category_id=category_id
        )
        return jsonify({"message": "Request created", 'category':req.to_json()}), 201
    except Exception as e:
        return jsonify({"message": e.args[0]}), 500

# endregion

# region CRUD on categories
@api.route('/categories', methods=['POST'])
@jwt_required()
@role_required('admin')
def create_category():
    # Save the file
    file = request.files['file']
    unique_filename = generate_unique_name_for_file(file=file)
    file_storage_path = create_image_path(unique_filename, "categories")
    file.save(file_storage_path)

    # Create the category
    try:
        category = CategoryDAL.create( 
            name=request.form.get('category_name'),
            description=request.form.get('category_description'),
            image_path=unique_filename
        )
    
        return jsonify({"message": "Category created", 'category':category.to_json()}), 201
    except IntegrityError:
        return jsonify({"message": "The category name already exists. Please try a different name."}), 401
    except Exception as e:
        return jsonify({"message": e.args[0]}), 500

@api.route('/categories', methods=['GET'])
@cache.cached(timeout=25)
def get_categories():
    categories = CategoryDAL.get_all_categories()
    return jsonify({"categories":[category.to_json() for category in categories], "message":"fetched successfully"}), 200

@api.route('/categories/<int:id>', methods=['PUT', "DELETE", "GET"])
@jwt_required()
@role_required("admin")
def update_category(id):
    if request.method == "PUT":
        category_to_update = CategoryDAL.get_category_by_id(category_id=id)
        category_name = request.form.get('category_name')
        category_description = request.form.get('category_description')
        new_image_path = request.form.get('category_image_path')

        if 'file' in request.files:
            # Save the new image file if it is added
            file = request.files['file'] if request.files['file'] else None
            new_image_path = generate_unique_name_for_file(file=file)
            new_file_storage_path = create_image_path(new_image_path, "categories")
            file.save(new_file_storage_path)

        category = CategoryDAL.update(category_to_update, name=category_name, description=category_description, new_image_path=new_image_path)
        return jsonify({"message": "Category updated", "category": category.to_json()}), 200    
    elif request.method == "DELETE":
        category = CategoryDAL.delete(category_id=id)
        return jsonify({"message": "Category deleted", "category": category.to_json()})
    else:
        category = CategoryDAL.get_category_by_id(category_id=id)
        return jsonify({"message": "Category fetched", "category": category.to_json()})
# endregion

# region CRUD on Products
@api.route('/products', methods=['POST'])
@jwt_required()
@role_required("manager")
def products_post():
    product_data = {}

    # Save the file
    file = request.files['file']
    unique_filename = generate_unique_name_for_file(file=file)
    file_storage_path = create_image_path(unique_filename, "products")
    file.save(file_storage_path)
    product_data['image_path'] = unique_filename

    # Extract form data
    product_data['category_id'] = int(request.form.get('category_id'))
    product_data['product_name'] = request.form.get('product_name')
    product_data['description'] = request.form.get('description')
    product_data['price'] = request.form.get('price')
    product_data['brand'] = request.form.get('brand')
    product_data['unit'] = request.form.get('unit')

    try:
        product = ProductDAL.create(product_data=product_data)
    except IntegrityError:
        return jsonify({"message": "The product name already exists. Please try a different name."}), 401
    except Exception as e:
        raise e
        return jsonify({'message':e.args[0]}), 500

    return jsonify({'message': 'Product added successfully.', 'product':product.to_json()}), 201

@api.route('/products', methods=['GET'])
def products_get_all_products():
    if "limit" in request.args:
        limit = int( request.args['limit'] )
        products = ProductDAL.get_top_x_products(limit)
        return jsonify({"products" : [ product.to_json() for product in products]})

    elif "category" in request.args:
        category_id = int(request.args['category'])
        category = CategoryDAL.get_category_by_id(category_id=category_id)
        products = [product.to_json() for product in category.products if product.is_deleted == False] # Return only non deleted products   
        return jsonify({"products" : products})
    else:
        products = ProductDAL.get_products()
        return jsonify({"products" : [ product.to_json() for product in products]})
    

@api.route('/products/<int:id>', methods=["DELETE", "PATCH"])
@jwt_required()
@role_required("manager")
def product_get_put_delete(id:int):
    if request.method == "DELETE":
        # Delete the product with the given ID
        try:
            product = ProductDAL.delete(product_id=id)
            message = "product deleted" if product else "no product for the given id found"
            return jsonify({"message" : message, "product": product.to_json()})
        except Exception as e:
            raise e
    elif request.method == "PATCH":
        # Update the product with the given ID
        data = request.form
        id, name, desc, price, brand, unit = data['id'], data['product_name'], data['description'], data['price'], data['brand'], data['unit']
        product = ProductDAL.get_product_from_id(id)
        new_image_path = None
        # Save the file if another file is added
        if 'file' in request.files:
            file = request.files['file']
            unique_filename = generate_unique_name_for_file(file=file)
            file_storage_path = create_image_path(unique_filename, "products")
            file.save(file_storage_path)
            new_image_path = unique_filename
        try:
            product = ProductDAL.update(product=product, name=name, desc=desc, price=price, brand=brand, unit=unit, img_path=new_image_path)
            return jsonify({'message':'successfully updated', 'product':product.to_json()}), 201
        except Exception as e:
            raise e
# endregion

# region search
@api.route('/search', methods=['GET'])
def search():
    q = request.args.get('q')
    if not q:
        return jsonify({ 'products' : []})
    results = search_in_database(q) # Only products are going to be searched and returned
    return jsonify(results)

# endregion

# region customer related endpoints
@api.route("/place_order", methods=["POST"])
@jwt_required()
@role_required('user')
def place_order():
    current_user = get_jwt_identity()
    cart_items = request.form.getlist('cart')
    cart = [json.loads(item) for item in cart_items]
    print(cart)
    order_details = [ ]
    for item in cart:
        print(item)
        order_detail = OrderDetails(product_id=item['productId'], quantity=item['quantity'], price=item['price'])
        order_details.append(order_detail)
    OrderDAL.place_order(current_user['id'], order_details)
    return jsonify({"message":"order placed successfully"}), 200


@api.route('/products/<int:product_id>', methods=["GET"])
@cache.memoize(timeout=120)
def get_full_product_details(product_id):
    if request.method == "GET":
        product = ProductDAL.get_product_from_id(product_id=product_id)
        return jsonify({"message" : "Success", "product" :product.to_json()}), 200
# endregion


# region Stocks

@api.route('/stocks', methods=['GET', 'POST'])
@jwt_required()
@role_required('manager')
def stocks():
    if request.method == 'GET':
        stock_transactions = StockDAL.read()
        return jsonify({"message" : "Success", "transactions" : [tr.to_json() for tr in stock_transactions]}), 200
    else:
        data = request.json
    
        # Convert mfdDate and expDate to date objects
        mfd_date = datetime.strptime(data['mfdDate'], '%Y-%m-%d').date()
        exp_date = datetime.strptime(data['expDate'], '%Y-%m-%d').date()
        StockDAL.create(product_id = data['productId'], transaction_type=data['type'], 
                      mfd_date=mfd_date, exp_date=exp_date, qty=data['quantity'])
        return jsonify({'message':'successfully created'}), 200
# endregion

# region Async jobs
@api.route('/manager/product_report')
@jwt_required()
@role_required('manager')
def generate_task_id():
    from application.tasks import generate_product_details_report
    with app.app_context():
        task = generate_product_details_report.delay()
        return jsonify({"task_id":task.id}), 202    

@api.route('/manager/poll_product_report/<id>')
@jwt_required()
@role_required('manager')
def poll_task(id):
    from application import celery
    id = str(id)
    res = celery.AsyncResult(id=id)
    status = res.status
    return jsonify({'task_status': status}), 200

@api.route('/manager/get_report')
@jwt_required()
@role_required('manager')
def send_report():
    file_path = r'/mnt/d/IITM/MAD-II/Project V2/backend/static/reports/product_details.csv'
    return send_file(file_path, as_attachment=True)
# endregion


@api.route('/user/order_history', methods=['GET'])
@jwt_required()
@role_required('user')
@cache.cached(timeout=60)
def get_order_history():
    current_user = get_jwt_identity()
    user = UserDAL.get_user_by_id(current_user['id'])
    orders = [ ]
    for order in user.orders:
        for order_detail in order.order_details:
            temp = {
                "order_id" : order.id, 
                "order_date" : order.placed_on, 
                'product_id' : order_detail.product_id, 
                'product_name' : order_detail.product.product_name, 
                "price" : order_detail.price, 
                'quantity' : order_detail.quantity, 
                'order_detail_id' : order_detail.id, 
                'status' : order.status
            }
            orders.append(temp)
    return jsonify({'orders' : orders, "message" : "Order history fetched successfully"}), 200

@api.route('/user/order_history/<int:order_detail_id>', methods=['GET', 'POST'])
@jwt_required()
@role_required('user')
def submit_order_review(order_detail_id):
    current_user = get_jwt_identity()
    if request.method == 'GET':
        order_detail = OrderDetailsDAL.get_order_detail_by_id(order_detail_id=int(order_detail_id))
        if order_detail.order.user_id != current_user['id']:
            return jsonify({"message":"You're not authorized to view this"}), 401
        else:
            order_detail_to_return = {
                "order_detail_id" : order_detail.id,
                'order_id':order_detail.order.id,
                'product_name' : order_detail.product.product_name,
                'product_id' : order_detail.product_id,
                'order_date' : order_detail.order.placed_on,
                'product_image_path' : order_detail.product.image_path
            }
            return jsonify({'order_detail' : order_detail_to_return}), 200
    else:
        product_id = request.form.get('product_id')
        rating = request.form.get('rating')
        review = request.form.get('review')
        order_detail = OrderDetailsDAL.get_order_detail_by_id(order_detail_id=int(order_detail_id))
        user_id = current_user['id']
        if order_detail.order.user_id != current_user['id']:
            return jsonify({"message":"You're not authorized to view this"}), 401

        try:
            r_n_r = RatingAndReviewDAL.create(user_id=user_id, product_id=product_id, rating=rating, review=review)
            return jsonify({'message' : 'Review placed successfully'}), 200
        except Exception as e:
            return jsonify({'message': e.args[0]}), 404
        
    
@api.route('/manager/pending_orders', methods=['GET'])
@jwt_required()
@role_required('manager')
@cache.cached(timeout=60)
def get_pending_orders():
    pending_orders = OrderDAL.get_pending_orders()  
    return jsonify({'message': 'fetched successfully', 'pending_orders':[order.to_json() for order in pending_orders]}), 200

@api.route('/manager/pending_orders/<int:order_id>', methods=['GET'])
@jwt_required()
@role_required('manager')
@cache.memoize(timeout=60)
def get_order_details(order_id):
    order = OrderDAL.get_order_by_id(order_id=order_id)
    return jsonify({'order': order.to_json(), 'message':'fetched successfully'}), 200

@api.route('/manager/pending_orders/<int:order_id>', methods=['POST'])
@jwt_required()
@role_required('manager')
def mark_order_as_complete(order_id):
    OrderDAL.mark_order_as_complete(order_id=order_id)
    return jsonify({'message':'order successfully marked as completed'}), 200


@api.route('/static/<file_type>/<filename>', methods=['GET'])
def serve_file(file_type, filename):
    """For serving image files to the frontend"""
    path = create_image_path(file_name=filename, file_type=file_type    )
    return send_file(path, mimetype='image/jpeg')

# region login, register related endpoints
@api.route('/register/<role>', methods=["POST"])
def register(role): 
    """Register a user"""

    # Raise error if the request is for admin
    if role not in ["manager", 'user']:
        jsonify({"message":"invalid user role"}), 400

    # If registeration is for manager, then create a request for admin approval
    data = request.json
    data['role'] = role
    if data['role'] == 'manager':
        req = PendingRequestsDAL.manager_requests_create_request(data)
        return jsonify({'message':"Request submitted", "request":req.to_json()}), 200
    
    # else if registeration is for user role, create the user
    else:
        try:
            user = UserDAL.create(data)
            return jsonify({'message':"Successfully created", "user":user.to_json()}), 200
        except IntegrityError:
            return jsonify({'message':"Username already exists. Please choose a different name."}), 401

@api.route('/login/<role>', methods=['POST'])
def login(role):
    """Logs in the user"""
    username = request.json.get('username', None)
    password = request.json.get('password', None)
    user = UserDAL.get_user_by_username(username)
    if user and checkpw(password.encode('utf-8'), user.password) and role in [role.name for role in user.roles.all()]:
        access_token = create_access_token(identity={'username': user.username, 'role': role, "id":user.id})
        return jsonify({'access_token': access_token, "message":"login successful"}), 200

    return jsonify({'message': 'Invalid credentials'}), 401
# endregion
