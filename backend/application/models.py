from sqlalchemy import Column, Integer, String, Float, Date, Boolean, ForeignKey, TIMESTAMP, Text
from sqlalchemy.orm import relationship
from datetime import date, datetime
from flask_login import UserMixin
from flask_security import RoleMixin
from . import db

# Many-To-Many table for Users and their Roles
class RolesUsers(db.Model):
    __tablename__ = 'roles_users'
    id = Column(Integer(), primary_key=True, autoincrement=True)
    user_id = Column(Integer(),ForeignKey('user.id')) 
    role_id = Column(Integer(),ForeignKey('role.id'))

# Model for Role
class Role(RoleMixin, db.Model ):
    id = Column(Integer(), primary_key=True)
    name = Column(String(80), unique=True)

    def __str__(self):
        return f"{self.id}, {self.name}"

    def to_json(self):
        return {
            "id" : self.id, 
            "name" : self.name
        }

class User(UserMixin, db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(200), nullable=False)  
    contact = Column(String(10), nullable=False)
    address = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    active = Column(Boolean(), default=True)
    created_on = Column(TIMESTAMP, default=datetime.now(), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_on = Column(TIMESTAMP)
    roles = relationship('Role', secondary='roles_users', backref='users', lazy='dynamic')
    
    # One-to-many relationship with Order
    orders = relationship('Order', backref='user', lazy=True)
    reviews = relationship("RatingAndReview", back_populates="user")

    def __str__(self):
        return f"{self.username}, {self.roles}"
    
    def to_json(self):
        return {
            'id' : self.id, 
            'username' : self.username, 
            'name' : self.name,
            'email' : self.email, 
            'roles' : [ role.to_json() for role in self.roles.all()]
        }

# Model for Category
class Category(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    category_name = Column(String(100), nullable=False, unique=True)
    category_description = Column(String(200), nullable=False)
    category_image_path = Column(String)
    created_on = Column(TIMESTAMP, default=datetime.now(), nullable=False)
    is_deleted = Column(Boolean, default=False)
    deleted_on = Column(TIMESTAMP, nullable=True)
    products = relationship('Product', backref='category', lazy=True)

    def to_json(self):
        products = [ ]
        for product in self.products:
            if not product.is_deleted:
                products.append(product.to_json())

        return {
            'id': self.id,
            'category_name': self.category_name,
            'category_description': self.category_description,
            'image_path': self.category_image_path,
            'created_on': self.created_on.strftime('%Y-%m-%d %H:%M:%S') if self.created_on else None,
            "products" : products
        }
    
# Model for Product
class Product(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    product_name = Column(String(100), nullable=False, unique=True)
    description = Column(String(255))
    price = Column(Float, nullable=False)
    brand = Column(String(100), nullable=False)
    unit = Column(String, nullable=False)
    image_path = Column(String)  
    created_on = Column(TIMESTAMP, default=datetime.now(), nullable=False)
    category_id = Column(Integer, ForeignKey('category.id'), nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_on = Column(TIMESTAMP)
    stocks = relationship('Stock', backref='product', lazy=True)
    order_details = relationship('OrderDetails', back_populates='product')
    reviews = relationship("RatingAndReview", back_populates='product')

    def to_json(self):
        return {
            'id': self.id,
            'product_name': self.product_name,
            'description': self.description,
            'price': self.price,
            'brand': self.brand,
            'unit': self.unit,
            'image_path': self.image_path,
            'created_on': self.created_on.strftime('%Y-%m-%d %H:%M:%S') if self.created_on else None,
            'category_id': self.category_id,
            'is_deleted': self.is_deleted,
            'deleted_on': self.deleted_on.strftime('%Y-%m-%d %H:%M:%S') if self.deleted_on else None,
            'stocks': [stock.to_json() for stock in self.stocks],  # Serializing stocks
            'reviews' : [review.to_json() for review in self.reviews], 
            'available_stock' :sum(stock.quantity if stock.type == "IN" else -stock.quantity for stock in self.stocks)
        }
    
# Model for Ratings and Reviews for products
class RatingAndReview(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('product.id'), nullable=False)
    rating = Column(Integer, nullable=False)
    review =Column(Text)

    product = relationship("Product", back_populates="reviews")
    user = relationship('User', back_populates="reviews")

    def to_json(self):
        return {
            "id" : self.id, 
            "user_id" : self.user_id, 
            "product_id" : self.product_id, 
            "rating" : self.rating, 
            "review" : self.review, 
            "username" : self.user.username
        }

    
# Model for Order
class Order(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    placed_on = Column(Date, default=date.today(), nullable=False)
    order_details = relationship('OrderDetails', backref='order', lazy=True, cascade="all, delete-orphan")
    status = Column(String(20), nullable=False, default="PENDING")  
    completed_on = Column(TIMESTAMP, nullable=True)

    def to_json(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'username':self.user.username,
            'placed_on': self.placed_on.strftime('%Y-%m-%d') if self.placed_on else None,
            'status': self.status,
            'order_details': [detail.to_json() for detail in self.order_details]  # Serializing order_details
        }


# Model for OrderDetails
class OrderDetails(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(Integer, ForeignKey('order.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('product.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    # Many-to-one relationship with Product model
    product = relationship('Product', back_populates='order_details')

    def to_json(self):
        return {
            "id" : self.id, 
            "order_id":self.order_id, 
            "quantity" : self.quantity,
            "price" : self.price, 
            "product_id" : self.product_id, 
            "product": self.product.to_json()
        }

# Model for Stock
class Stock(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    product_id = Column(Integer, ForeignKey('product.id'), nullable=False, index=True)
    mfd_date = Column(Date, nullable=True)
    exp_date = Column(Date, nullable=True)
    quantity = Column(Integer, nullable=False)
    type = Column(String(5), nullable=False) # Should be IN or OUT
    transaction_date = Column(Date, nullable=False, default=date.today())

    def to_json(self):
        return {
            "id" : self.id, 
            "product_id" : self.product_id, 
            "product_name": self.product.product_name,
            "mfd_date": self.mfd_date.strftime('%d-%m-%Y') if self.mfd_date else None,
            "expiry_date" : self.exp_date.strftime('%d-%m-%Y') if self.exp_date else None, 
            "qty" : self.quantity, 
            "transaction_type" : self.type, 
            "transaction_date" : self.transaction_date.strftime('%d-%m-%Y') if self.transaction_date else None, 
        }
    
# Model for Requests for manager's account creation
class PendingManagerRegisterRequests(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    requested_on = Column(TIMESTAMP, default=datetime.now(), nullable=False)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password = Column(String(200), nullable=False)  
    contact = Column(String(10), nullable=False)
    email = Column(String(255), nullable=False, unique=True)
    address = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    approval_status = Column(String(100), default="not approved", nullable=False)
    approved_on = Column(TIMESTAMP)

    def to_json(self):
        return {
            "id" : self.id, 
            "requested_on" : self.requested_on, 
            "username" : self.username, 
            "contact" : self.contact, 
            "email" : self.email, 
            "name" : self.name, 
            "address" : self.address
        }

# Model for requests for category changes
class PendingCategoryRequests(db.Model):
    id = Column(Integer, primary_key=True, autoincrement=True)
    requested_by = Column(Integer, ForeignKey('user.id'), nullable=False)
    requested_on = Column(TIMESTAMP, default=datetime.now(), nullable=False)
    request_type = Column(String(5), nullable=False) # Should be create, delete, update
    approval_status = Column(String, default="not approved", nullable=False) # Can be one of 'not approved', 'rejected', 'approved'
    category_name = Column(String(100), nullable=True, unique=True)
    category_description = Column(String(200), nullable=True)
    category_image_path = Column(String(300), unique=True, nullable=True)
    approved_on = Column(TIMESTAMP)
    category_id = Column(Integer, ForeignKey('category.id'), nullable=True)
    remark = Column(Text, nullable=True)
    category_id = Column(Integer, ForeignKey('category.id'), nullable=True)

    user = relationship("User", backref="pending_category_requests")

    def to_json(self):
        return {
            "id" : self.id, 
            "requested_by" : self.requested_by, 
            'requested_by_username' : self.user.username,
            "requested_on" : self.requested_on, 
            "request_type" : self.request_type, 
            "approval_status" : self.approval_status, 
            "category_name" : self.category_name, 
            "category_description" : self.category_description, 
            "category_img_path" : self.category_image_path, 
            'category_id' : self.category_id, 
            'remark' : self.remark
        }