from application.dal import ProductDAL
from application import app, celery
import smtplib
from email.message import EmailMessage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from .utils import *
from .config import *
from datetime import datetime, timedelta
from sqlalchemy import func
from jinja2 import Template
from .dal import *
import time
from celery import shared_task

PRODUCT_DETAILS_REPORT_PATH = r""
MONTHLY_ACTIVITY_REPORT_PATH = r""

# Send emails to each user
@shared_task(ignore_result=True)
def send_mail(to, subject, message):
    with app.app_context():
        try:
            with smtplib.SMTP(SMTP_SERVER_HOST, 587) as s:
                s.starttls()
                s.login(SENDER_ADDRESS, SENDER_PASSWORD)
                msg = EmailMessage()
                msg['From'] = SENDER_ADDRESS
                msg['To'] = to
                msg["Subject"] = subject
                msg.set_content( message)
                try:    
                    s.send_message(msg)
                    time.sleep(0.15)
                except Exception as e1:
                    print(f"An error occurred while sending email to {to}: {e1}")
                    raise e1
                s.quit()
        except Exception as e:
                # Log the exception and continue with the next user
                print(f"An error occurred: {e}")
                raise e

# Gets all users who haven't made a purchase today
@shared_task(ignore_result=True)
def send_daily_purchase_reminder_mail():
    users = UserDAL.get_users_with_no_orders_today()
    user_emails = [user.email for user in users]
    for email in user_emails:
        send_mail(email, "Daily Purchase Reminder", "You haven't visited/bought anything today. Visit the store's website to avail exciting offers.")

# Sends a report to a user
@shared_task(ignore_result=True)
def send_monthly_report(username, user_email, html_message):
    
    # Set up the email server and MIME object
    with smtplib.SMTP(SMTP_SERVER_HOST, 587) as s:
        s.starttls()
        s.login(SENDER_ADDRESS, SENDER_PASSWORD)
    
        msg = MIMEMultipart('alternative')
        msg['From'] = "your_email_here"
        msg['To'] = user_email
        msg['Subject'] = "Monthly Activity Report for {}".format(username)
    
        # Attach HTML content
        msg.attach(MIMEText(html_message, 'html'))
        
        try:    
            s.send_message(msg)
            time.sleep(0.15)
        except Exception as e1:
            print(f"An error occurred while sending email to {user_email}: {e1}")
            raise e1
        s.quit()

@shared_task(ignore_result=True)
def generate_monthly_activity_report(username, user_id, start_date, end_date):
    # Fetch Orders
    orders = db.session.query(Order).filter(
        Order.user_id == user_id,
        Order.placed_on >= start_date,
        Order.placed_on <= end_date
    ).all()
    total_expenditure=0
    for order in orders:
        for order_detail in order.order_details:
            total_expenditure+= (order_detail.price * order_detail.quantity)

    with open(f"{MONTHLY_ACTIVITY_REPORT_PATH}", 'r', encoding='utf-8') as f:
        template = Template(f.read())
        message = template.render(orders=orders, total_expenditure=total_expenditure, username=username)

    with open(f"{MONTHLY_ACTIVITY_REPORT_PATH}", 'w', encoding='utf-8') as f:
        f.write(message)
    return message

@shared_task(ignore_result=True)
def monthly_activity_report_task():
    users = UserDAL.get_all_users()
    current_date = datetime.now()
    first_day_current_month = current_date.replace(day=1)
    last_day_last_month = first_day_current_month - timedelta(days=1)
    first_day_last_month = last_day_last_month.replace(day=1)
    for user in users:
        message = generate_monthly_activity_report(user.username, user.id, first_day_last_month, last_day_last_month)
        send_monthly_report(user.username, user.email, message)
        time.sleep(0.15)

@celery.task
def generate_product_details_report():
    products = ProductDAL.get_products()
    for product in products:
        product.available_stock = ProductDAL.get_available_stock(product)
        product.total_ordered_qty = ProductDAL.get_total_order_qty(product)
        product.total_sale_qty = ProductDAL.get_total_sale_qty(product)
    
    df = {
        "Product Id" : [ ], 
        "Product Name" : [ ],
        "Description": [ ],
        "Brand": [ ], 
        "Price" : [ ], 
        "Category": [ ], 
        "Is Deleted?" : [ ], 
        "Total Available Stock" : [ ], 
        "Total Order Qty" : [ ], 
        "Total Sale Qty": [ ]
    }

    for product in products:
        df['Product Id'].append(product.id)
        df["Brand"].append(product.brand)
        df['Category'].append(CategoryDAL.get_category_by_id(product.category_id).category_name)
        df['Product Name'].append(product.product_name)
        df['Description'].append(product.description)
        df['Is Deleted?'].append(product.is_deleted)
        df['Total Available Stock'].append(product.available_stock)
        df['Total Order Qty'].append(product.total_ordered_qty)
        df['Total Sale Qty'].append(product.total_sale_qty)
        df['Price'].append(product.price)

    df = pd.DataFrame(df)
    path = f"{PRODUCT_DETAILS_REPORT_PATH}"
    df.to_csv(path)
    return path