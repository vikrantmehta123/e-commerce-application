from application.models import *
import bcrypt
import pandas as pd
from sqlalchemy.exc import IntegrityError
import os
from .utils import *

# region CRUD on user
class UserDAL:
    @staticmethod
    def create(user_data: dict, hash=True):
        # Create hash for the password
        if hash:
            password = bcrypt.hashpw(password=user_data.get('password').encode('utf-8'), salt=bcrypt.gensalt())
        else:
            password = user_data.get('password')

        # Add use to database
        user = User(
            username=user_data.get('username'),
            password=password,
            contact=user_data.get('contact'),
            address=user_data.get('address'),
            name=user_data.get('name'), 
            email=user_data.get("email")
        )

        # Add role
        role = Role.query.filter_by(name=user_data['role']).first()
        if role not in user.roles:
            user.roles.append(role)
        try:
            print(user)

            db.session.add(user)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise IntegrityError
        return user

    @staticmethod
    def get_user_by_id(user_id:int) -> User:
        user = User.query.get(user_id)
        if not user.is_deleted:
            return user
        
    @staticmethod
    def get_user_by_username(username:str) -> User:
        user = User.query.filter_by(username= username).first()
        if user and not user.is_deleted:
            return user

    # Marks the user as deleted
    @staticmethod
    def delete(user_id:int):
        user = UserDAL.get_user_by_id(user_id=user_id)
        user.is_deleted = True
        user.deleted_on = datetime.now()
        db.session.commit()

    # Gets the users who have not placed an order today
    @staticmethod
    def get_users_with_no_orders_today():
        from sqlalchemy import func, and_
        today = date.today()

        # Query to find users who have not placed an order today
        users_without_order_today = db.session.query(User)\
            .join(User.roles)\
            .filter(Role.name == 'user').filter(User.is_deleted == False).outerjoin(Order, and_(User.id == Order.user_id, Order.placed_on == today)).filter(Order.id == None).all()
        return users_without_order_today
    
    # Gets all active users
    @staticmethod
    def get_all_users() -> list['User']:
        users_with_role_user = db.session.query(User)\
            .join(User.roles)\
            .filter(Role.name == 'user').filter(User.is_deleted == False)\
            .all()
        return users_with_role_user

# endregion

# region operations on Product
class ProductDAL:
    @staticmethod
    def create(product_data:dict) -> Product:
        product = Product(
            product_name = product_data['product_name'], description = product_data['description'], price = product_data['price'], 
            brand=product_data['brand'], unit=product_data['unit'], category_id=product_data['category_id'], 
            image_path=product_data['image_path'] if 'image_path' in product_data else None          
                          )
        try:
            db.session.add(product)
            db.session().commit()
        except Exception as e:
            raise e
        return product
    
    @staticmethod
    def update(product:Product, name=None, desc=None, price=None, brand=None, unit=None, img_path=None):
        
        if name:
            product.product_name = name
        if desc:
            product.description = desc
        if price:
            product.price = price
        if brand:
            product.brand = brand
        if unit:
            product.unit = unit
        if img_path:
            # Delete old file if it exists
            if product.image_path:
                old_storage_path = create_image_path(product.image_path, "products")
                if os.path.exists(old_storage_path):
                    os.remove(old_storage_path)
            product.image_path = img_path
        try:
            db.session.commit()
        except Exception as e:
            raise e
        return product

    @staticmethod
    def delete(product_id:int):
        product = ProductDAL.get_product_from_id(product_id=product_id)
        if not product:
            return None

        # Mark the product as deleted
        product.is_deleted = True
        product.deleted_on = datetime.now()
        db.session.commit()

        # Delete the image associated with it
        path_to_category_image = create_image_path(product.image_path, "products")
        if os.path.exists(path=path_to_category_image):
            os.remove(path_to_category_image)

        return product

    @staticmethod
    def get_top_x_products(x:int) -> list["Product"]:
        try:
            top_x_products = Product.query.filter_by(is_deleted=False) \
                                        .order_by(Product.created_on.desc()) \
                                        .limit(x) \
                                        .all()
            return top_x_products
        except Exception as e:
            return str(e)
        
    @staticmethod
    def get_products() -> list["Product"]:
        return Product.query.filter_by(is_deleted=False).order_by(Product.created_on.desc()).all()

    @staticmethod
    def get_product_from_id(product_id:int) -> Product:
        product = Product.query.get(product_id)
        product.category_name = CategoryDAL.get_category_by_id(product.category_id).category_name if product else None
        return product if not product.is_deleted else None

    # Useful reporting stats

    # Current Available stock
    @staticmethod
    def get_available_stock(product:Product) -> float:
        available_stock = sum(stock.quantity if stock.type == "IN" else -stock.quantity for stock in product.stocks)
        return available_stock

    # Total Order qty
    @staticmethod
    def get_total_order_qty(product:Product) -> float:
        total_order_qty = sum([order_detail.quantity for order_detail in product.order_details])
        return total_order_qty

    # Total Sale qty
    @staticmethod
    def get_total_sale_qty(product:Product) -> float:
        return sum(stock.quantity if stock.type != "IN" else 0 for stock in product.stocks)

# endregion

# region Operations on Category
class CategoryDAL:
    @staticmethod
    def create(name, description, image_path):
        new_category = Category(
            category_name=name,
            category_description=description,
            category_image_path=image_path
        )
        try:
            db.session.add(new_category)
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise IntegrityError
        return new_category

    @staticmethod
    def get_all_categories():
        return Category.query.filter_by(is_deleted=False).all()

    @staticmethod
    def get_category_by_id(category_id) -> Category:
        return Category.query.filter(db.and_(Category.id == category_id, Category.is_deleted == False)).first()

    @staticmethod
    def update(category:Category, name=None, description=None, new_image_path=None) -> Category:
        if not category:
            # raise exception here
            return None
        if name:
            category.category_name = name
        if description:
            category.category_description = description
        if new_image_path:
            # Delete old file if it exists
            if category.category_image_path:
                old_storage_path = create_image_path(category.category_image_path, "categories")
                if os.path.exists(old_storage_path):
                    os.remove(old_storage_path)
            category.category_image_path = new_image_path
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            raise IntegrityError
        return category

    @staticmethod
    def delete(category_id) -> Category:
        category = CategoryDAL.get_category_by_id(category_id)
        if not category:
            return None
        
        # Mark the category as deleted
        category.deleted_on = datetime.now()
        category.is_deleted = True

        # Mark all the products as deleted associated with the category
        for product in category.products:
            ProductDAL.delete(product_id=product.id)
        db.session.commit()

        # Delete the image associated with it
        path_to_category_image = create_image_path(category.category_image_path, "categories")
        if os.path.exists(path=path_to_category_image):
            os.remove(path_to_category_image)
        return category

# endregion

# region Operations on Pending Requests (category and manager)
class PendingRequestsDAL:
    @staticmethod
    def get_pending_category_request_count():
        """Gets count of pending category requests for admin dashboard"""
        return PendingCategoryRequests.query.filter_by(approval_status="not approved").count()
    
    @staticmethod
    def get_pending_manager_approval_request_count():
        """Gets count of pending managerial requests for admin dashboard"""
        return PendingManagerRegisterRequests.query.filter_by(approval_status="not approved").count()

    @staticmethod
    def category_requests_create_request(user_id:int, req_type:str, cat_name:str, cat_desc:str, img_path:str, remark:str, category_id:int=None):
        """Creates a new Category request for admin approval"""
        req = PendingCategoryRequests(
            requested_by = user_id, 
            request_type = req_type, 
            category_name = cat_name, 
            category_description=cat_desc,
            category_image_path = img_path, 
            remark=remark, 
            category_id=category_id
        )
        try:
            db.session.add(req)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
        return req
    

    @staticmethod
    def category_requests_update_approval_status(request_id:int, new_status:str):
        """Updates the approval status after admin approval"""
        request = PendingCategoryRequests.query.get(request_id)
        request.approval_status = new_status
        request.approved_on = datetime.now()
        
        if new_status == 'approved':
            if request.request_type == 'create':
                CategoryDAL.create( name=request.category_name, description=request.category_description, image_path=request.category_image_path)
            elif request.request_type == 'update':
                category = CategoryDAL.get_category_by_id(request.category_id)
                CategoryDAL.update(category, name=request.category_name, description=request.category_description)
            else:
                CategoryDAL.delete(category_id=request.category_id)
        db.session.commit()

    @staticmethod
    def manager_requests_create_request(user_data:dict):
        """Creates a new managerial request for admin approval"""
        password = bcrypt.hashpw(password=user_data.get('password').encode('utf-8'), salt=bcrypt.gensalt())
        req = PendingManagerRegisterRequests(
            username=user_data.get('username'),
            password=password,
            contact=user_data.get('contact'),
            address=user_data.get('address'),
            name=user_data.get('name'), 
            email=user_data.get("email")
        )
        db.session.add(req)
        db.session.commit()
        return req

    @staticmethod
    def manager_requests_update_approval_status(request_id:int, new_status:str):
        """Update the approval status of manager request after admin action"""
        # Mark the request's status as new_status
        request = PendingManagerRegisterRequests.query.get(request_id)

        if request.approval_status == new_status:
            return
        request.approval_status = new_status
        request.approved_on = datetime.now()
        
        if new_status == 'approved':
            user_data = { "username": request.username, "password":request.password, "contact":request.contact, 
                            "email" : request.email, "name" : request.name, "address":request.address, 'role' : 'manager'
                        }
            UserDAL.create(user_data, hash=False)
            from .tasks import send_mail
            send_mail(to=request.email, subject=f"Status update for managerial request", message=f"Dear {request.name}, your request has been {new_status}")
        
        db.session.commit()

    @staticmethod
    def manager_requests_get_pending_requests() -> list[PendingManagerRegisterRequests]:
        """Gets the pending manager registration requests from the database"""
        return PendingManagerRegisterRequests.query.filter_by(approval_status="not approved").all()
    
    @staticmethod
    def category_requests_get_pending_requests() -> list[PendingCategoryRequests]:
        """Gets the pending category requests that are pending approval"""
        return PendingCategoryRequests.query.filter_by(approval_status = "not approved").all()

# endregion

class StockDAL:
    @staticmethod
    def create(product_id:int, qty:int, transaction_type:str,mfd_date:Date=None, exp_date:Date=None ):
        """Creates a stock entry"""
        stock = Stock(product_id=product_id, mfd_date=mfd_date, exp_date=exp_date, quantity=qty, type=transaction_type)
        db.session.add(stock)
        db.session.commit()

    @staticmethod
    def read() -> list['Stock']:
        return Stock.query.all()

class OrderDAL:
    @staticmethod
    def get_order_by_id(order_id:int) -> Order:
        """Gets an Order by its ID"""
        return Order.query.get(order_id)

    @staticmethod
    def get_pending_orders() -> list[Order]:
        """Gets all pending orders"""
        return Order.query.filter(Order.status == "PENDING").all()

    @staticmethod
    def mark_order_as_complete(order_id:int):
        """Marks the order as complete and creates stock transactions to complete the order"""
        order = OrderDAL.get_order_by_id(order_id)  
        if not order:
            return
        try:
            order.status = 'COMPLETE'
            order.completed_on = datetime.now()
        
            for order_detail in order.order_details:
                StockDAL.create(order_detail.product_id, qty=order_detail.quantity, transaction_type='OUT' )
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
        return order

    @staticmethod
    def place_order(user_id:int, cart:list[OrderDetails]) -> Order:
        """Places a customer order"""
        order = Order(user_id = user_id)
        order.order_details = cart
        try:
            db.session.add(order)
            db.session.commit()        
            return order

        except Exception as e:
            db.session.rollback()
            raise e
        
class OrderDetailsDAL:
    @staticmethod
    def get_order_detail_by_id(order_detail_id) -> OrderDetails:
        """Gets the Order Details for the give ID"""
        return OrderDetails.query.get(order_detail_id)
        
class RatingAndReviewDAL:
    @staticmethod
    def create(user_id:int, product_id:int, rating:int, review:str):
        """Create a Rating / Review for a product"""
        r_n_r = RatingAndReview(user_id=user_id, product_id=product_id, rating=rating, review=review)
        try:
            db.session.add(r_n_r)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise e
        return r_n_r

class ReportDAL:
    @staticmethod
    def get_itemwise_stock_report():
        products = ProductDAL.get_products()
        for product in products:
            product.available_stock = ProductDAL.get_available_stock(product)
            product.total_ordered_qty = ProductDAL.get_total_order_qty(product)
            product.total_sale_qty = ProductDAL.get_total_sale_qty(product)
        return products
