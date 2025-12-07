from flask import Flask, request, jsonify, send_file, session
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, date, timedelta
# Invoice Management System - Backend API
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import os
import tempfile
import smtplib
import random
import secrets
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import qrcode
from io import BytesIO
import base64
import threading

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_HTTPONLY'] = True

# Environment detection for CORS settings
is_production = os.getenv('FLASK_ENV') == 'production'
if is_production:
    app.config['SESSION_COOKIE_SAMESITE'] = 'None'
    app.config['SESSION_COOKIE_SECURE'] = True
else:
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False

# CORS configuration - allow all origins for development and production
CORS(app, 
     supports_credentials=True,
     origins=[
         'https://kandhal-invoice-system.vercel.app',
         'http://localhost:3000',
         'http://127.0.0.1:3000',
         'http://127.0.0.1:5000',
         'http://localhost:5000',
     ],
     allow_headers=['Content-Type', 'Authorization'],
     expose_headers=['Content-Type', 'Authorization'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

# Additional CORS handler to ensure headers are always present
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Origin'] = origin if origin != '*' else 'https://kandhal-invoice-system.vercel.app'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response

# Error handler to ensure CORS on errors too
@app.errorhandler(Exception)
def handle_error(error):
    response = jsonify({'error': str(error)})
    response.status_code = 500
    origin = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Origin'] = origin if origin != '*' else 'https://kandhal-invoice-system.vercel.app'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response

# MongoDB connection from environment variables
connection_string = os.getenv('MONGODB_URI')
database_name = os.getenv('MONGODB_DATABASE', 'grocery_shop')

if not connection_string:
    raise ValueError("MONGODB_URI environment variable is not set in .env file")

client = MongoClient(connection_string)
db = client[database_name]
items_collection = db.items
invoices_collection = db.invoices
auth_collection = db.auth_sessions
customers_collection = db.customers

# Global OPTIONS handler for all routes
@app.route('/', defaults={'path': ''}, methods=['OPTIONS'])
@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    response = jsonify({'status': 'ok'})
    origin = request.headers.get('Origin', '*')
    response.headers['Access-Control-Allow-Origin'] = origin if origin != '*' else 'https://kandhal-invoice-system.vercel.app'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response, 200

# Create indexes for better performance
items_collection.create_index("item_name")
invoices_collection.create_index("invoice_id")
invoices_collection.create_index("customer_name")
auth_collection.create_index("email")
auth_collection.create_index("expires_at", expireAfterSeconds=0)
customers_collection.create_index("email")
customers_collection.create_index("phone")
customers_collection.create_index("user_email")

# Migration: Only fix items with truly missing or N/A units
print("Running database migration for units...")
try:
    # Only update items that explicitly have N/A or are completely missing unit field
    result1 = items_collection.update_many(
        {"$or": [{"unit": "N/A"}, {"unit": None}, {"unit": ""}]},
        {"$set": {"unit": "pcs"}}
    )
    
    if result1.modified_count > 0:
        print(f"Updated {result1.modified_count} items with problematic units")
    else:
        print("No items needed unit updates")
except Exception as e:
    print(f"Migration error: {e}")

# SMTP Configuration from environment variables
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_EMAIL = os.getenv('SMTP_EMAIL')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

# Health check endpoint
@app.route('/health', methods=['GET', 'OPTIONS'])
@app.route('/api/health', methods=['GET', 'OPTIONS'])
def health_check():
    """Health check endpoint to wake up the server"""
    try:
        # Check MongoDB connection
        db.command('ping')
        return jsonify({
            'status': 'ok',
            'message': 'Server is running',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'database': 'disconnected',
            'timestamp': datetime.now().isoformat()
        }), 500

if not SMTP_EMAIL or not SMTP_PASSWORD:
    print("⚠️ WARNING: SMTP credentials not found in .env file. Email functionality will not work.")
else:
    print(f"✅ SMTP configured: {SMTP_EMAIL} via {SMTP_SERVER}:{SMTP_PORT}")

# Background email sender function
def send_invoice_email_async(customer_email, invoice_id, invoice_doc, shop_name, shop_address, shop_phone, items, subtotal, tax, discount, total, tax_rate, discount_rate, customer_name, customer_address, customer_number):
    """Send invoice email in background thread"""
    try:
        # Prepare email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'📄 Invoice #{invoice_id} from {shop_name} | Invoice Management System'
        msg['From'] = f'{shop_name} <{SMTP_EMAIL}>'
        msg['To'] = customer_email
        
        # Create items HTML
        items_html = ""
        for item in items:
            items_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">{item['name']}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center;">{item['quantity']} {item.get('unit', 'pcs')}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">Rs {item['price']:.2f}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">Rs {item['quantity'] * item['price']:.2f}</td>
            </tr>
            """
        
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
            <div style="max-width: 700px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
              
              <!-- App Branding -->
              <div style="text-align: center; margin-bottom: 20px; padding: 15px; background: linear-gradient(135deg, #ff9933 0%, #138808 100%); border-radius: 8px;">
                <h3 style="color: white; margin: 0; font-size: 16px; text-shadow: 1px 1px 2px rgba(0,0,0,0.3);">📊 Invoice Management System</h3>
                <p style="color: #f0f0f0; margin: 5px 0 0 0; font-size: 12px;">Professional Invoice Generation & Management</p>
              </div>
              
              <!-- Shop Details -->
              <div style="border-bottom: 3px solid #138808; padding-bottom: 20px; margin-bottom: 30px;">
                <h1 style="color: #138808; margin: 0; font-size: 28px;">🏪 {shop_name}</h1>
                <p style="margin: 5px 0; color: #666; font-size: 14px;">📍 {shop_address}</p>
                <p style="margin: 5px 0; color: #666; font-size: 14px;">📞 {shop_phone}</p>
              </div>
              
              <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 30px;">
                <h2 style="color: #138808; margin: 0 0 15px 0; font-size: 20px;">Invoice #{invoice_id}</h2>
                <p style="margin: 5px 0; color: #333;"><strong>Date:</strong> {invoice_doc['order_date'].strftime('%d %B %Y')}</p>
                <p style="margin: 5px 0; color: #333;"><strong>Customer:</strong> {customer_name}</p>
                <p style="margin: 5px 0; color: #333;"><strong>Address:</strong> {customer_address}</p>
                <p style="margin: 5px 0; color: #333;"><strong>Contact:</strong> {customer_number}</p>
              </div>
              
              <table style="width: 100%; border-collapse: collapse; margin-bottom: 30px;">
                <thead>
                  <tr style="background-color: #138808; color: white;">
                    <th style="padding: 12px; text-align: left;">Item</th>
                    <th style="padding: 12px; text-align: center;">Quantity</th>
                    <th style="padding: 12px; text-align: right;">Price</th>
                    <th style="padding: 12px; text-align: right;">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {items_html}
                </tbody>
              </table>
              
              <div style="border-top: 2px solid #138808; padding-top: 20px;">
                <table style="width: 100%; max-width: 300px; margin-left: auto;">
                  <tr>
                    <td style="padding: 8px; color: #666;">Subtotal:</td>
                    <td style="padding: 8px; text-align: right; font-weight: bold;">Rs {subtotal:.2f}</td>
                  </tr>
                  <tr>
                    <td style="padding: 8px; color: #666;">Tax ({tax_rate}%):</td>
                    <td style="padding: 8px; text-align: right; font-weight: bold;">Rs {tax:.2f}</td>
                  </tr>
                  <tr>
                    <td style="padding: 8px; color: #666;">Discount ({discount_rate}%):</td>
                    <td style="padding: 8px; text-align: right; font-weight: bold; color: #d9534f;">- Rs {discount:.2f}</td>
                  </tr>
                  <tr style="border-top: 2px solid #138808;">
                    <td style="padding: 12px; font-size: 18px; font-weight: bold; color: #138808;">Total Amount:</td>
                    <td style="padding: 12px; text-align: right; font-size: 20px; font-weight: bold; color: #138808;">Rs {total:.2f}</td>
                  </tr>
                </table>
              </div>
              
              <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; color: #999; font-size: 12px;">
                <p style="margin: 5px 0;">🙏 Thank you for your business!</p>
                <p style="margin: 10px 0;">This invoice was generated by <strong style="color: #138808;">Invoice Management System</strong></p>
                <p style="margin: 10px 0;">This is an automated email from <strong>{shop_name}</strong>. Please do not reply.</p>
                <p style="margin: 10px 0;">📧 For any queries, contact us at {shop_phone}</p>
                <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #eee;">
                  <p style="margin: 5px 0; color: #bbb; font-size: 11px;">Powered by Invoice Management System | Professional Business Solutions</p>
                </div>
              </div>
            </div>
          </body>
        </html>
        """
        
        part = MIMEText(html, 'html')
        msg.attach(part)
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ Invoice email sent successfully to {customer_email}")
        print(f"   Shop: {shop_name}")
        print(f"   Invoice ID: {invoice_id}")
        
    except Exception as email_error:
        print(f"❌ Failed to send invoice email to {customer_email}")
        print(f"   Error: {email_error}")
        print(f"   Shop: {shop_name}")
        print(f"   Invoice ID: {invoice_id}")

# Authentication endpoints
@app.route('/api/auth/send-signup-otp', methods=['POST'])
def send_signup_otp():
    """Send OTP for email verification during signup"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()
        shop_name = data.get('shop_name', '').strip()
        shop_address = data.get('shop_address', '').strip()
        shop_phone = data.get('shop_phone', '').strip()
        
        if not all([email, password, shop_name, shop_address, shop_phone]):
            return jsonify({"success": False, "error": "All fields are required"}), 400
        
        # Check if user already exists with confirmed account
        existing_user = auth_collection.find_one({"email": email})
        if existing_user and existing_user.get('password_hash') and existing_user.get('email_verified'):
            return jsonify({"success": False, "error": "Email already registered"}), 400
        
        # Generate 6-digit OTP
        otp = str(random.randint(100000, 999999))
        
        # Hash password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        # Store pending signup data with OTP (10 minute expiration)
        expires_at = datetime.now() + timedelta(minutes=10)
        auth_collection.update_one(
            {"email": email},
            {
                "$set": {
                    "pending_password_hash": password_hash,
                    "pending_shop_name": shop_name,
                    "pending_shop_address": shop_address,
                    "pending_shop_phone": shop_phone,
                    "signup_otp": otp,
                    "signup_otp_expires": expires_at
                }
            },
            upsert=True
        )
        
        # Send verification email with OTP
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Verify Your Email - Grocery Shop'
        msg['From'] = SMTP_EMAIL
        msg['To'] = email
        
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
              <h2 style="color: #138808; text-align: center;">Email Verification</h2>
              <p style="font-size: 16px; color: #333; margin: 20px 0;">Welcome to <strong>{shop_name}</strong>!</p>
              <p style="font-size: 16px; color: #333;">Please verify your email address to complete your account registration.</p>
              <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 30px 0; text-align: center;">
                <p style="margin: 0 0 10px 0; color: #666; font-size: 14px;">Your Verification Code:</p>
                <h1 style="color: #138808; font-size: 42px; margin: 10px 0; letter-spacing: 8px; font-family: 'Courier New', monospace;">{otp}</h1>
              </div>
              <p style="font-size: 14px; color: #666;">This code will expire in <strong>10 minutes</strong>.</p>
              <p style="font-size: 14px; color: #666; margin-top: 30px;">If you didn't request this verification, please ignore this email.</p>
              <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
              <p style="font-size: 12px; color: #999; text-align: center;">Grocery Shop Invoice System</p>
            </div>
          </body>
        </html>
        """
        
        part = MIMEText(html, 'html')
        msg.attach(part)
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        
        return jsonify({
            "success": True,
            "message": "Verification OTP sent to your email"
        })
        
    except Exception as e:
        print(f"Error sending signup OTP: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/auth/verify-signup', methods=['POST'])
def verify_signup():
    """Verify OTP and create account"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        otp = data.get('otp', '').strip()
        
        if not email or not otp:
            return jsonify({"success": False, "error": "Email and OTP are required"}), 400
        
        # Find pending signup
        user = auth_collection.find_one({"email": email})
        
        if not user or not user.get('signup_otp'):
            return jsonify({"success": False, "error": "No pending signup found"}), 404
        
        # Check if OTP is expired
        if datetime.now() > user.get('signup_otp_expires', datetime.now()):
            return jsonify({"success": False, "error": "OTP has expired. Please request a new one."}), 400
        
        # Verify OTP
        if user['signup_otp'] != otp:
            return jsonify({"success": False, "error": "Invalid OTP"}), 401
        
        # Move pending data to actual fields and mark email as verified
        auth_collection.update_one(
            {"email": email},
            {
                "$set": {
                    "password_hash": user['pending_password_hash'],
                    "shop_name": user['pending_shop_name'],
                    "shop_address": user['pending_shop_address'],
                    "shop_phone": user['pending_shop_phone'],
                    "email_verified": True,
                    "created_at": datetime.now()
                },
                "$unset": {
                    "pending_password_hash": "",
                    "pending_shop_address": "",
                    "pending_shop_name": "",
                    "pending_shop_phone": "",
                    "signup_otp": "",
                    "signup_otp_expires": ""
                }
            }
        )
        
        return jsonify({
            "success": True,
            "message": "Email verified! Account created successfully."
        })
        
    except Exception as e:
        print(f"Error verifying signup: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """Login with email and password"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()
        
        if not email or not password:
            return jsonify({"success": False, "error": "Email and password are required"}), 400
        
        # Find user
        user = auth_collection.find_one({"email": email})
        
        if not user or not user.get('password_hash'):
            return jsonify({"success": False, "error": "Invalid email or password"}), 401
        
        # Check if email is verified
        if not user.get('email_verified'):
            return jsonify({"success": False, "error": "Please verify your email first"}), 403
        
        # Verify password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user['password_hash'] != password_hash:
            return jsonify({"success": False, "error": "Invalid email or password"}), 401
        
        # Create session token
        session_token = secrets.token_urlsafe(32)
        session_expires = datetime.now() + timedelta(hours=24)
        
        # Update session
        auth_collection.update_one(
            {"email": email},
            {
                "$set": {
                    "session_token": session_token,
                    "session_expires": session_expires,
                    "last_login": datetime.now()
                }
            }
        )
        
        return jsonify({
            "success": True,
            "message": "Login successful",
            "session_token": session_token,
            "email": email,
            "shop_name": user.get('shop_name', 'Shop'),
            "shop_address": user.get('shop_address', ''),
            "shop_phone": user.get('shop_phone', '')
        })
        
    except Exception as e:
        print(f"Error during login: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/auth/forgot-password', methods=['POST'])
def forgot_password():
    """Send OTP for password reset"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({"success": False, "error": "Email is required"}), 400
        
        # Check if user exists
        user = auth_collection.find_one({"email": email})
        if not user:
            return jsonify({"success": False, "error": "Email not registered"}), 404
        
        # Generate 6-digit OTP
        otp = str(random.randint(100000, 999999))
        
        # Store OTP with 10 minute expiration
        expires_at = datetime.now() + timedelta(minutes=10)
        auth_collection.update_one(
            {"email": email},
            {
                "$set": {
                    "reset_otp": otp,
                    "reset_otp_expires": expires_at
                }
            }
        )
        
        # Send email with OTP
        msg = MIMEMultipart('alternative')
        msg['Subject'] = 'Password Reset OTP - Grocery Shop'
        msg['From'] = SMTP_EMAIL
        msg['To'] = email
        
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
              <h2 style="color: #138808; text-align: center;">🔐 Password Reset</h2>
              <h3 style="color: #333; text-align: center;">OTP Verification</h3>
              <p style="color: #666; font-size: 16px;">Your One-Time Password for password reset is:</p>
              <div style="background: linear-gradient(135deg, #dc3545 0%, #c82333 100%); color: white; font-size: 32px; font-weight: bold; text-align: center; padding: 20px; border-radius: 8px; letter-spacing: 8px; margin: 20px 0;">
                {otp}
              </div>
              <p style="color: #666; font-size: 14px;">This OTP is valid for 10 minutes. Do not share it with anyone.</p>
              <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
              <p style="color: #999; font-size: 12px; text-align: center;">If you didn't request this, please ignore this email.</p>
            </div>
          </body>
        </html>
        """
        
        part = MIMEText(html, 'html')
        msg.attach(part)
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        
        return jsonify({
            "success": True,
            "message": f"Password reset OTP sent to {email}"
        })
        
    except Exception as e:
        print(f"Error sending reset OTP: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/auth/reset-password', methods=['POST'])
def reset_password():
    """Reset password with OTP verification"""
    try:
        data = request.json
        email = data.get('email', '').strip().lower()
        otp = data.get('otp', '').strip()
        new_password = data.get('new_password', '').strip()
        
        if not all([email, otp, new_password]):
            return jsonify({"success": False, "error": "All fields are required"}), 400
        
        # Find user
        user = auth_collection.find_one({"email": email})
        
        if not user:
            return jsonify({"success": False, "error": "Invalid email"}), 401
        
        # Check OTP
        if not user.get('reset_otp') or user['reset_otp'] != otp:
            return jsonify({"success": False, "error": "Invalid OTP"}), 401
        
        # Check if OTP expired
        if user.get('reset_otp_expires', datetime.now()) < datetime.now():
            auth_collection.update_one(
                {"email": email},
                {"$unset": {"reset_otp": "", "reset_otp_expires": ""}}
            )
            return jsonify({"success": False, "error": "OTP expired. Please request a new one."}), 401
        
        # Hash new password
        password_hash = hashlib.sha256(new_password.encode()).hexdigest()
        
        # Update password and clear OTP
        auth_collection.update_one(
            {"email": email},
            {
                "$set": {"password_hash": password_hash},
                "$unset": {"reset_otp": "", "reset_otp_expires": ""}
            }
        )
        
        return jsonify({
            "success": True,
            "message": "Password reset successful"
        })
        
    except Exception as e:
        print(f"Error resetting password: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/auth/verify-session', methods=['POST'])
def verify_session():
    """Verify if session token is valid"""
    try:
        data = request.json
        session_token = data.get('session_token', '').strip()
        
        if not session_token:
            return jsonify({"success": False, "error": "Session token required"}), 401
        
        # Find session in database
        auth_doc = auth_collection.find_one({"session_token": session_token})
        
        if not auth_doc:
            return jsonify({"success": False, "error": "Invalid session"}), 401
        
        # Check if session expired
        if auth_doc.get('session_expires', datetime.now()) < datetime.now():
            auth_collection.update_one(
                {"session_token": session_token},
                {"$unset": {"session_token": "", "session_expires": ""}}
            )
            return jsonify({"success": False, "error": "Session expired"}), 401
        
        return jsonify({
            "success": True,
            "email": auth_doc['email'],
            "shop_name": auth_doc.get('shop_name', 'Shop'),
            "shop_address": auth_doc.get('shop_address', ''),
            "shop_phone": auth_doc.get('shop_phone', '')
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """Logout user and invalidate session"""
    try:
        data = request.json
        session_token = data.get('session_token', '').strip()
        
        if session_token:
            auth_collection.update_one(
                {"session_token": session_token},
                {"$unset": {"session_token": "", "session_expires": ""}}
            )
        
        return jsonify({"success": True, "message": "Logged out successfully"})
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Security middleware to verify session token
def verify_session_token(token):
    """Verify if session token is valid and not expired"""
    if not token:
        return None
    
    auth_doc = auth_collection.find_one({"session_token": token})
    
    if not auth_doc:
        return None
    
    # Check if session expired
    if auth_doc.get('session_expires', datetime.now()) < datetime.now():
        # Clean up expired session
        auth_collection.update_one(
            {"session_token": token},
            {"$unset": {"session_token": "", "session_expires": ""}}
        )
        return None
    
    return auth_doc

def require_auth(f):
    """Decorator to require authentication for routes"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get token from header or query param
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            token = request.args.get('session_token', '')
        
        auth_doc = verify_session_token(token)
        
        if not auth_doc:
            return jsonify({"success": False, "error": "Unauthorized. Please login."}), 401
        
        # Add user email to request context
        request.user_email = auth_doc['email']
        request.user_id = str(auth_doc['_id'])
        
        return f(*args, **kwargs)
    
    return decorated_function

# Test email endpoint (for debugging SMTP configuration)
@app.route('/api/test-email', methods=['POST'])
@require_auth
def test_email():
    """Test email configuration by sending a test email"""
    try:
        data = request.json
        test_email_addr = data.get('email', '')
        
        if not test_email_addr:
            return jsonify({"success": False, "error": "Email address is required"}), 400
        
        if not SMTP_EMAIL or not SMTP_PASSWORD:
            return jsonify({
                "success": False, 
                "error": "SMTP credentials not configured on server"
            }), 500
        
        # Get shop details
        session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        shop_info = auth_collection.find_one({"session_token": session_token})
        shop_name = shop_info.get('shop_name', 'Invoice System') if shop_info else 'Invoice System'
        
        # Prepare test email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'✅ Test Email from {shop_name} - Invoice Management System'
        msg['From'] = f'{shop_name} <{SMTP_EMAIL}>'
        msg['To'] = test_email_addr
        
        html = f"""
        <html>
          <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f4f4;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
              <div style="text-align: center; margin-bottom: 20px; padding: 20px; background: linear-gradient(135deg, #ff9933 0%, #138808 100%); border-radius: 8px;">
                <h1 style="color: white; margin: 0; font-size: 24px;">✅ Email Test Successful!</h1>
              </div>
              <p style="font-size: 16px; color: #333; margin: 20px 0;">Hello!</p>
              <p style="font-size: 16px; color: #333;">This is a test email from <strong>{shop_name}</strong>.</p>
              <p style="font-size: 16px; color: #333;">Your email configuration is working correctly! 🎉</p>
              <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 30px 0;">
                <p style="margin: 5px 0; color: #666;"><strong>SMTP Server:</strong> {SMTP_SERVER}</p>
                <p style="margin: 5px 0; color: #666;"><strong>From:</strong> {SMTP_EMAIL}</p>
                <p style="margin: 5px 0; color: #666;"><strong>Test Date:</strong> {datetime.now().strftime('%d %B %Y, %I:%M %p')}</p>
              </div>
              <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; text-align: center; color: #999; font-size: 12px;">
                <p>Powered by Invoice Management System</p>
              </div>
            </div>
          </body>
        </html>
        """
        
        part = MIMEText(html, 'html')
        msg.attach(part)
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_EMAIL, SMTP_PASSWORD)
            server.send_message(msg)
        
        print(f"✅ Test email sent successfully to {test_email_addr}")
        return jsonify({
            "success": True,
            "message": f"Test email sent successfully to {test_email_addr}"
        })
        
    except smtplib.SMTPAuthenticationError:
        print(f"❌ SMTP Authentication failed")
        return jsonify({
            "success": False,
            "error": "SMTP Authentication failed. Please check email credentials."
        }), 500
    except Exception as e:
        print(f"❌ Failed to send test email: {e}")
        return jsonify({
            "success": False,
            "error": f"Failed to send test email: {str(e)}"
        }), 500

# Custom JSON serialization function
def serialize_doc(doc):
    """Convert MongoDB document to JSON serializable format"""
    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, datetime):
                result[key] = value.isoformat()
            elif isinstance(value, list):
                result[key] = [serialize_doc(item) if isinstance(item, dict) else item for item in value]
            elif isinstance(value, dict):
                result[key] = serialize_doc(value)
            else:
                result[key] = value
        return result
    return doc

def generate_qr_code(data):
    """Generate QR code and return as base64 string"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode()
    return img_str

@app.route('/api/items', methods=['GET'])
@require_auth
def get_items():
    """Get all items - Requires authentication"""
    try:
        user_email = request.user_email
        items = list(items_collection.find({"user_email": user_email}))
        serialized_items = [serialize_doc(item) for item in items]
        return jsonify({"success": True, "items": serialized_items})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/items', methods=['POST'])
@require_auth
def add_item():
    """Add new item - Requires authentication"""
    try:
        data = request.json
        
        # Input validation
        item_name = data.get('item_name', '').strip()
        if not item_name:
            return jsonify({"success": False, "error": "Item name is required"}), 400
        
        try:
            item_price = float(data.get('item_price', 0))
            if item_price < 0:
                return jsonify({"success": False, "error": "Price cannot be negative"}), 400
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Invalid price format"}), 400
        
        try:
            stock = int(data.get('stock', 0))
            if stock < 0:
                return jsonify({"success": False, "error": "Stock cannot be negative"}), 400
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Invalid stock format"}), 400
        
        unit = data.get('unit', 'pcs').strip()
        if not unit:
            unit = 'pcs'
        
        # Check if item already exists for this user
        user_email = request.user_email
        existing_item = items_collection.find_one({"item_name": item_name, "user_email": user_email})
        if existing_item:
            # Update stock if item exists
            items_collection.update_one(
                {"item_name": item_name, "user_email": user_email},
                {"$inc": {"stock": stock}, "$set": {"unit": unit}}
            )
            updated_item = items_collection.find_one({"item_name": item_name, "user_email": user_email})
            return jsonify({
                "success": True, 
                "message": f"Updated stock for {item_name}",
                "item": serialize_doc(updated_item)
            })
        else:
            # Create new item with user_email
            item_doc = {
                "item_name": item_name,
                "item_price": item_price,
                "stock": stock,
                "unit": unit,
                "user_email": user_email,
                "created_at": datetime.now()
            }
            result = items_collection.insert_one(item_doc)
            item_doc["_id"] = result.inserted_id
            
            # Generate QR code for the item
            qr_data = {
                "item_id": str(item_doc["_id"]),
                "item_name": item_name,
                "item_price": item_price,
                "unit": unit
            }
            qr_code = generate_qr_code(json.dumps(qr_data))
            
            return jsonify({
                "success": True, 
                "message": f"Item {item_name} added successfully",
                "item": serialize_doc(item_doc),
                "qr_code": qr_code
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/items/<item_id>', methods=['PUT'])
@require_auth
def update_item(item_id):
    """Update item - Requires authentication"""
    try:
        # Validate ObjectId
        try:
            ObjectId(item_id)
        except:
            return jsonify({"success": False, "error": "Invalid item ID"}), 400
        
        user_email = request.user_email
        
        # Check if item exists and belongs to user
        existing_item = items_collection.find_one({"_id": ObjectId(item_id), "user_email": user_email})
        if not existing_item:
            return jsonify({"success": False, "error": "Item not found or access denied"}), 404
        
        data = request.json
        update_data = {}
        
        # Validate and sanitize inputs
        if 'item_name' in data:
            item_name = data['item_name'].strip()
            if item_name:
                update_data['item_name'] = item_name
        
        if 'item_price' in data:
            try:
                price = float(data['item_price'])
                if price < 0:
                    return jsonify({"success": False, "error": "Price cannot be negative"}), 400
                update_data['item_price'] = price
            except (TypeError, ValueError):
                return jsonify({"success": False, "error": "Invalid price format"}), 400
        
        if 'stock' in data:
            try:
                stock_value = int(data['stock'])
                if stock_value < 0:
                    return jsonify({"success": False, "error": "Stock cannot be negative"}), 400
                    
                if data.get('update_type') == 'add':
                    items_collection.update_one(
                        {"_id": ObjectId(item_id)},
                        {"$inc": {"stock": stock_value}}
                    )
                else:
                    update_data['stock'] = stock_value
            except (TypeError, ValueError):
                return jsonify({"success": False, "error": "Invalid stock format"}), 400
        
        if 'unit' in data:
            unit = data['unit'].strip()
            if unit:
                update_data['unit'] = unit
        
        if update_data:
            update_data['updated_at'] = datetime.now()
            items_collection.update_one(
                {"_id": ObjectId(item_id)},
                {"$set": update_data}
            )
        
        updated_item = items_collection.find_one({"_id": ObjectId(item_id)})
        return jsonify({
            "success": True,
            "message": "Item updated successfully",
            "item": serialize_doc(updated_item)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/items/<item_id>', methods=['DELETE'])
@require_auth
def delete_item(item_id):
    """Delete item - Requires authentication"""
    try:
        # Validate ObjectId
        try:
            ObjectId(item_id)
        except:
            return jsonify({"success": False, "error": "Invalid item ID"}), 400
        
        user_email = request.user_email
        result = items_collection.delete_one({"_id": ObjectId(item_id), "user_email": user_email})
        if result.deleted_count > 0:
            return jsonify({"success": True, "message": "Item deleted successfully"})
        else:
            return jsonify({"success": False, "error": "Item not found or access denied"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/items/<item_id>/qrcode', methods=['GET'])
@require_auth
def get_item_qrcode(item_id):
    """Get QR code for specific item - Requires authentication"""
    try:
        # Validate ObjectId
        try:
            ObjectId(item_id)
        except:
            return jsonify({"success": False, "error": "Invalid item ID"}), 400
        
        user_email = request.user_email
        item = items_collection.find_one({"_id": ObjectId(item_id), "user_email": user_email})
        
        if not item:
            return jsonify({"success": False, "error": "Item not found or access denied"}), 404
        
        # Generate QR code
        qr_data = {
            "item_id": str(item["_id"]),
            "item_name": item["item_name"],
            "item_price": item["item_price"],
            "unit": item.get("unit", "pcs")
        }
        qr_code = generate_qr_code(json.dumps(qr_data))
        
        return jsonify({
            "success": True,
            "qr_code": qr_code,
            "item": serialize_doc(item)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/items/search', methods=['GET'])
@require_auth
def search_items():
    """Search items by name - Requires authentication"""
    try:
        search_term = request.args.get('q', '').strip()
        if not search_term:
            return jsonify({"success": True, "items": []})
        
        # Sanitize search term to prevent NoSQL injection
        search_term = search_term.replace('$', '').replace('{', '').replace('}', '')
        
        user_email = request.user_email
        items = list(items_collection.find({
            "item_name": {"$regex": search_term, "$options": "i"},
            "user_email": user_email
        }))
        serialized_items = [serialize_doc(item) for item in items]
        return jsonify({"success": True, "items": serialized_items})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Customer Management Endpoints
@app.route('/api/customers', methods=['GET'])
@require_auth
def get_customers():
    """Get all customers for current user - Requires authentication"""
    try:
        user_email = request.user_email
        customers = list(customers_collection.find({"user_email": user_email}).sort("created_at", -1))
        serialized_customers = [serialize_doc(customer) for customer in customers]
        return jsonify({"success": True, "customers": serialized_customers})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/customers', methods=['POST'])
@require_auth
def add_customer():
    """Add new customer - Requires authentication"""
    try:
        data = request.json
        user_email = request.user_email
        
        # Input validation
        customer_name = data.get('customer_name', '').strip()
        customer_phone = data.get('customer_phone', '').strip()
        customer_email = data.get('customer_email', '').strip()
        customer_address = data.get('customer_address', '').strip()
        
        if not customer_name:
            return jsonify({"success": False, "error": "Customer name is required"}), 400
        if not customer_phone:
            return jsonify({"success": False, "error": "Customer phone is required"}), 400
        if not customer_email:
            return jsonify({"success": False, "error": "Customer email is required"}), 400
        if not customer_address:
            return jsonify({"success": False, "error": "Customer address is required"}), 400
        
        # Check if customer with same phone already exists for this user
        existing_customer = customers_collection.find_one({
            "customer_phone": customer_phone,
            "user_email": user_email
        })
        
        if existing_customer:
            return jsonify({"success": False, "error": "Customer with this phone number already exists"}), 400
        
        # Create customer document
        customer = {
            "customer_name": customer_name,
            "customer_phone": customer_phone,
            "customer_email": customer_email,
            "customer_address": customer_address,
            "user_email": user_email,
            "total_purchases": 0,
            "total_spent": 0,
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }
        
        result = customers_collection.insert_one(customer)
        customer['_id'] = result.inserted_id
        
        return jsonify({
            "success": True,
            "message": "Customer added successfully",
            "customer": serialize_doc(customer)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/customers/<customer_id>', methods=['PUT'])
@require_auth
def update_customer(customer_id):
    """Update customer information - Requires authentication"""
    try:
        # Validate ObjectId
        try:
            ObjectId(customer_id)
        except:
            return jsonify({"success": False, "error": "Invalid customer ID"}), 400
        
        user_email = request.user_email
        customer = customers_collection.find_one({"_id": ObjectId(customer_id), "user_email": user_email})
        
        if not customer:
            return jsonify({"success": False, "error": "Customer not found or access denied"}), 404
        
        data = request.json
        update_data = {}
        
        if 'customer_name' in data:
            customer_name = data['customer_name'].strip()
            if customer_name:
                update_data['customer_name'] = customer_name
        
        if 'customer_phone' in data:
            customer_phone = data['customer_phone'].strip()
            if customer_phone:
                # Check if phone number is already used by another customer
                existing = customers_collection.find_one({
                    "customer_phone": customer_phone,
                    "user_email": user_email,
                    "_id": {"$ne": ObjectId(customer_id)}
                })
                if existing:
                    return jsonify({"success": False, "error": "Phone number already in use by another customer"}), 400
                update_data['customer_phone'] = customer_phone
        
        if 'customer_email' in data:
            update_data['customer_email'] = data['customer_email'].strip() if data['customer_email'] else None
        
        if 'customer_address' in data:
            update_data['customer_address'] = data['customer_address'].strip() if data['customer_address'] else None
        
        if update_data:
            update_data['updated_at'] = datetime.now()
            customers_collection.update_one(
                {"_id": ObjectId(customer_id)},
                {"$set": update_data}
            )
        
        updated_customer = customers_collection.find_one({"_id": ObjectId(customer_id)})
        return jsonify({
            "success": True,
            "message": "Customer updated successfully",
            "customer": serialize_doc(updated_customer)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/customers/<customer_id>', methods=['DELETE'])
@require_auth
def delete_customer(customer_id):
    """Delete customer - Requires authentication"""
    try:
        # Validate ObjectId
        try:
            ObjectId(customer_id)
        except:
            return jsonify({"success": False, "error": "Invalid customer ID"}), 400
        
        user_email = request.user_email
        result = customers_collection.delete_one({"_id": ObjectId(customer_id), "user_email": user_email})
        
        if result.deleted_count > 0:
            return jsonify({"success": True, "message": "Customer deleted successfully"})
        else:
            return jsonify({"success": False, "error": "Customer not found or access denied"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/customers/search', methods=['GET'])
@require_auth
def search_customers():
    """Search customers by name or phone - Requires authentication"""
    try:
        search_term = request.args.get('q', '').strip()
        if not search_term:
            return jsonify({"success": True, "customers": []})
        
        # Sanitize search term
        search_term = search_term.replace('$', '').replace('{', '').replace('}', '')
        
        user_email = request.user_email
        customers = list(customers_collection.find({
            "$or": [
                {"customer_name": {"$regex": search_term, "$options": "i"}},
                {"customer_phone": {"$regex": search_term, "$options": "i"}}
            ],
            "user_email": user_email
        }))
        serialized_customers = [serialize_doc(customer) for customer in customers]
        return jsonify({"success": True, "customers": serialized_customers})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

def generate_next_invoice_id():
    """Generate next sequential invoice ID"""
    last_invoice = invoices_collection.find().sort("invoice_id", -1).limit(1)
    last_invoice = list(last_invoice)
    
    if last_invoice:
        return last_invoice[0]["invoice_id"] + 1
    else:
        return 1

def calculate_totals(items, tax_rate=0.0, discount_rate=0.0):
    """Calculate invoice totals using provided rates (in percentages) with custom rounding."""
    subtotal = sum(item["quantity"] * item["price"] for item in items)
    tax = subtotal * (tax_rate / 100)
    discount = subtotal * (discount_rate / 100)
    calculated_total = subtotal + tax - discount
    
    # Apply custom rounding logic
    rounded = round(calculated_total)
    last_digit = rounded % 10
    
    if 0 <= last_digit <= 4:
        # Round down to nearest 10
        total = (rounded // 10) * 10
    elif last_digit == 5:
        # Keep as is (ends with 5)
        total = rounded
    else:  # 6 <= last_digit <= 9
        # Round up to nearest 10
        total = ((rounded // 10) + 1) * 10
    
    return subtotal, tax, discount, total

@app.route('/api/invoices', methods=['POST'])
@require_auth
def create_invoice():
    """Create new invoice with tax rate and discount rate - Requires authentication"""
    try:
        data = request.json
        
        # Input validation
        customer_name = data.get('customer_name', '').strip()
        if not customer_name:
            return jsonify({"success": False, "error": "Customer name is required"}), 400
        
        customer_address = data.get('customer_address', '').strip()
        if not customer_address:
            return jsonify({"success": False, "error": "Customer address is required"}), 400
        
        customer_number = data.get('customer_number', '').strip()
        if not customer_number:
            return jsonify({"success": False, "error": "Customer phone number is required"}), 400
        
        customer_email = data.get('customer_email', '').strip()
        items = data.get('items', [])
        
        # Validate tax and discount rates
        try:
            tax_rate = float(data.get('tax_rate', 0))
            if tax_rate < 0 or tax_rate > 100:
                return jsonify({"success": False, "error": "Tax rate must be between 0 and 100"}), 400
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Invalid tax rate"}), 400
        
        try:
            discount_rate = float(data.get('discount_rate', 0))
            if discount_rate < 0 or discount_rate > 100:
                return jsonify({"success": False, "error": "Discount rate must be between 0 and 100"}), 400
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "Invalid discount rate"}), 400
        
        send_email = data.get('send_email', False)
        payment_method = data.get('payment_method', 'cash')
        notes = data.get('notes', '').strip()
        
        if not items or len(items) == 0:
            return jsonify({"success": False, "error": "No items provided"}), 400
        
        # Validate items and check ownership
        user_email = request.user_email
        for item in items:
            # Validate item structure
            if 'item_id' not in item or 'quantity' not in item:
                return jsonify({"success": False, "error": "Invalid item format"}), 400
            
            # Validate ObjectId
            try:
                ObjectId(item['item_id'])
            except:
                return jsonify({"success": False, "error": f"Invalid item ID: {item['item_id']}"}), 400
            
            # Validate quantity
            try:
                quantity = int(item['quantity'])
                if quantity <= 0:
                    return jsonify({"success": False, "error": "Item quantity must be positive"}), 400
            except (TypeError, ValueError):
                return jsonify({"success": False, "error": "Invalid quantity format"}), 400
            
            # Check item exists and belongs to user
            db_item = items_collection.find_one({"_id": ObjectId(item['item_id']), "user_email": user_email})
            if not db_item:
                return jsonify({"success": False, "error": f"Item not found or access denied: {item['item_id']}"}), 400
            
            if item['quantity'] > db_item['stock']:
                return jsonify({
                    "success": False, 
                    "error": f"Not enough stock for {db_item['item_name']}. Available: {db_item['stock']}"
                }), 400
            
            # Update item details with current price
            item['name'] = db_item['item_name']
            item['price'] = db_item['item_price']
        
        # Calculate totals
        subtotal, tax, discount, total = calculate_totals(items, tax_rate, discount_rate)
        
        # Generate invoice ID
        invoice_id = generate_next_invoice_id()
        
        # Create invoice document
        invoice_doc = {
            "invoice_id": invoice_id,
            "customer_name": customer_name,
            "customer_address": customer_address,
            "customer_number": customer_number,
            "customer_email": customer_email,
            "items": items,
            "subtotal": subtotal,
            "tax": tax,
            "discount": discount,
            "tax_rate": tax_rate,
            "discount_rate": discount_rate,
            "total": total,
            "payment_method": payment_method,
            "notes": notes,
            "user_email": user_email,
            "order_date": datetime.now(),
            "created_at": datetime.now()
        }
        
        # Save invoice
        result = invoices_collection.insert_one(invoice_doc)
        
        # Update stock for all items
        for item in items:
            items_collection.update_one(
                {"_id": ObjectId(item['item_id'])},
                {"$inc": {"stock": -item['quantity']}}
            )
        
        invoice_doc["_id"] = result.inserted_id
        
        # Prepare response BEFORE sending email (send email in background)
        response_data = {
            "success": True,
            "message": "Invoice created successfully",
            "invoice": serialize_doc(invoice_doc),
            "email_sent": False  # Will be sent in background
        }
        
        # Send email in background thread if requested
        if send_email and customer_email:
            if not SMTP_EMAIL or not SMTP_PASSWORD:
                print("⚠️ Email requested but SMTP credentials not configured")
                response_data["message"] = "Invoice created successfully. Email not sent - SMTP not configured."
                response_data["email_sent"] = False
            else:
                # Get shop details for email
                session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
                shop_info = auth_collection.find_one({"session_token": session_token})
                
                shop_name = shop_info.get('shop_name', 'Shop') if shop_info else 'Shop'
                shop_address = shop_info.get('shop_address', '') if shop_info else ''
                shop_phone = shop_info.get('shop_phone', '') if shop_info else ''
                
                print(f"📧 Starting email thread to send invoice #{invoice_id} to {customer_email}")
                
                # Start background email thread
                email_thread = threading.Thread(
                    target=send_invoice_email_async,
                    args=(customer_email, invoice_id, invoice_doc, shop_name, shop_address, shop_phone, 
                          items, subtotal, tax, discount, total, tax_rate, discount_rate,
                          customer_name, customer_address, customer_number)
                )
                email_thread.daemon = True
                email_thread.start()
                
                response_data["message"] = "Invoice created successfully. Email is being sent to " + customer_email
                response_data["email_sent"] = True  # Email is being sent
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/invoices', methods=['GET'])
@require_auth
def get_invoices():
    """Get all invoices - Requires authentication"""
    try:
        user_email = request.user_email
        invoices = list(invoices_collection.find({"user_email": user_email}).sort("invoice_id", -1))
        serialized_invoices = [serialize_doc(invoice) for invoice in invoices]
        return jsonify({"success": True, "invoices": serialized_invoices})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/invoices/<int:invoice_id>', methods=['GET'])
@require_auth
def get_invoice(invoice_id):
    """Get specific invoice - Requires authentication"""
    try:
        # Validate invoice_id
        if invoice_id <= 0:
            return jsonify({"success": False, "error": "Invalid invoice ID"}), 400
        
        user_email = request.user_email
        invoice = invoices_collection.find_one({"invoice_id": invoice_id, "user_email": user_email})
        if invoice:
            return jsonify({"success": True, "invoice": serialize_doc(invoice)})
        else:
            return jsonify({"success": False, "error": "Invoice not found or access denied"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/invoices/<int:invoice_id>/pdf', methods=['GET'])
@require_auth
def generate_invoice_pdf(invoice_id):
    """Generate PDF for invoice - Requires authentication"""
    try:
        # Validate invoice_id
        if invoice_id <= 0:
            return jsonify({"success": False, "error": "Invalid invoice ID"}), 400
        
        # Get session token from header or query param
        session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not session_token:
            session_token = request.args.get('session_token', '')
        
        # Verify session again for PDF access
        auth_doc = verify_session_token(session_token)
        if not auth_doc:
            return jsonify({"success": False, "error": "Unauthorized"}), 401
        
        # Get shop details from auth
        shop_info = auth_collection.find_one({"session_token": session_token})
        
        # Default values if not found
        shop_name = shop_info.get('shop_name', "SHOP") if shop_info else "SHOP"
        shop_address = shop_info.get('shop_address', "") if shop_info else ""
        shop_phone = shop_info.get('shop_phone', "") if shop_info else ""
        owner_email = shop_info.get('email', "") if shop_info else ""
        
        # Check invoice exists and belongs to user
        invoice = invoices_collection.find_one({"invoice_id": invoice_id, "user_email": owner_email})
        if not invoice:
            return jsonify({"success": False, "error": "Invoice not found or access denied"}), 404
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        temp_filename = temp_file.name
        temp_file.close()
        
        # Generate PDF
        c = canvas.Canvas(temp_filename, pagesize=letter)
        
        # Shop Info Header with dynamic shop name
        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(colors.HexColor("#138808"))
        c.drawString(50, 750, shop_name.upper())
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.black)
        c.drawString(470, 750, invoice['order_date'].strftime("%d/%m/%Y"))
        c.line(50, 740, 550, 740)
        
        c.setFont("Helvetica", 10)
        c.drawString(50, 725, f"Address: {shop_address}")
        c.drawString(50, 710, f"Phone: {shop_phone}")
        c.drawString(50, 695, f"Email: {owner_email}")
        
        # Invoice ID
        c.setFont("Helvetica-Bold", 14)
        c.drawString(400, 665, f"Invoice ID: {invoice['invoice_id']}")
        
        # Customer Info
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, 650, f"To: {invoice['customer_name']}")
        c.drawString(50, 635, f"Address: {invoice['customer_address']}")
        c.drawString(50, 620, f"Contact: {invoice['customer_number']}")
        
        # Items table
        y = 580
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Item")
        c.drawString(200, y, "Quantity")
        c.drawString(280, y, "Price (Rs)")
        c.drawString(370, y, "Total (Rs)")
        c.line(50, y-5, 420, y-5)
        
        y -= 20
        c.setFont("Helvetica", 10)
        for item in invoice['items']:
            c.drawString(50, y, item["name"])
            c.drawString(200, y, str(item["quantity"]))
            c.drawString(280, y, f"Rs {item['price']:.2f}")
            c.drawString(370, y, f"Rs {item['quantity'] * item['price']:.2f}")
            y -= 15
        
        # Totals
        y -= 10
        c.line(50, y, 420, y)
        y -= 20
        c.setFont("Helvetica-Bold", 10)
        c.drawString(280, y, f"Subtotal: Rs {invoice['subtotal']:.2f}")
        y -= 15
        # Split tax evenly into CGST/SGST for display if applicable
        half_tax = invoice['tax'] / 2
        cgst_rate = (invoice.get('tax_rate', 0) / 2)
        sgst_rate = cgst_rate
        c.drawString(280, y, f"CGST ({cgst_rate:.2f}%): Rs {half_tax:.2f}")
        y -= 15
        c.drawString(280, y, f"SGST ({sgst_rate:.2f}%): Rs {half_tax:.2f}")
        y -= 15
        c.drawString(280, y, f"Discount ({invoice.get('discount_rate', 0):.2f}%): -Rs {invoice['discount']:.2f}")
        y -= 15
        c.line(280, y, 420, y)
        y -= 15
        c.setFont("Helvetica-Bold", 12)
        c.drawString(280, y, f"Total Amount: Rs {invoice['total']:.2f}")
        
        # Footer with branding
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.grey)
        c.drawString(50, 50, "Thank you for your business!")
        
        # Kandhal Invoice System branding at bottom center
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(colors.HexColor("#138808"))
        footer_text = "Kandhal Invoice System"
        text_width = c.stringWidth(footer_text, "Helvetica-Bold", 10)
        c.drawString((letter[0] - text_width) / 2, 30, footer_text)
        c.setFont("Helvetica", 7)
        c.setFillColor(colors.grey)
        powered_text = "Powered by Kandhal Technologies"
        powered_width = c.stringWidth(powered_text, "Helvetica", 7)
        c.drawString((letter[0] - powered_width) / 2, 20, powered_text)
        
        c.save()
        
        return send_file(temp_filename, as_attachment=True, 
                        download_name=f"invoice_{invoice_id}.pdf", 
                        mimetype='application/pdf')
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/stats', methods=['GET'])
@require_auth
def get_stats():
    """Get sales statistics - Requires authentication"""
    try:
        user_email = request.user_email
        
        # Filter by user_email
        total_invoices = invoices_collection.count_documents({"user_email": user_email})
        total_revenue = list(invoices_collection.aggregate([
            {"$match": {"user_email": user_email}},
            {"$group": {"_id": None, "total": {"$sum": "$total"}}}
        ]))
        
        # Top customers for this user
        top_customers = list(invoices_collection.aggregate([
            {"$match": {"user_email": user_email}},
            {"$group": {"_id": "$customer_name", "total_spent": {"$sum": "$total"}, "invoice_count": {"$sum": 1}}},
            {"$sort": {"total_spent": -1}},
            {"$limit": 5}
        ]))
        
        # Daily sales for the last 7 days for this user
        daily_sales = list(invoices_collection.aggregate([
            {"$match": {"user_email": user_email}},
            {
                "$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$order_date"}},
                    "daily_sales": {"$sum": "$total"}
                }
            },
            {"$sort": {"_id": -1}},
            {"$limit": 7}
        ]))
        
        return jsonify({
            "success": True,
            "stats": {
                "total_invoices": total_invoices,
                "total_revenue": total_revenue[0]['total'] if total_revenue else 0,
                "top_customers": top_customers,
                "daily_sales": daily_sales
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/export/all-data', methods=['GET'])
@require_auth
def export_all_data():
    """Export all shop data (items, customers, invoices) as JSON - Requires authentication"""
    try:
        user_email = request.user_email
        
        # Get user's shop information
        user_session = auth_collection.find_one({"email": user_email})
        shop_info = {
            "shop_name": user_session.get("shop_name", "Unknown Shop") if user_session else "Unknown Shop",
            "shop_address": user_session.get("shop_address", "") if user_session else "",
            "shop_phone": user_session.get("shop_phone", "") if user_session else "",
            "export_date": datetime.now().isoformat()
        }
        
        # Get all items for this user
        items = list(items_collection.find({"user_email": user_email}))
        serialized_items = [serialize_doc(item) for item in items]
        
        # Get all customers for this user
        customers = list(customers_collection.find({"user_email": user_email}))
        serialized_customers = [serialize_doc(customer) for customer in customers]
        
        # Get all invoices for this user
        invoices = list(invoices_collection.find({"user_email": user_email}))
        serialized_invoices = [serialize_doc(invoice) for invoice in invoices]
        
        # Calculate statistics
        total_items = len(serialized_items)
        total_stock_value = sum(item.get('item_price', 0) * item.get('stock', 0) for item in serialized_items)
        total_customers = len(serialized_customers)
        total_invoices = len(serialized_invoices)
        total_revenue = sum(invoice.get('total', 0) for invoice in serialized_invoices)
        
        export_data = {
            "shop_info": shop_info,
            "summary": {
                "total_items": total_items,
                "total_stock_value": round(total_stock_value, 2),
                "total_customers": total_customers,
                "total_invoices": total_invoices,
                "total_revenue": round(total_revenue, 2)
            },
            "items": serialized_items,
            "customers": serialized_customers,
            "invoices": serialized_invoices
        }
        
        return jsonify({
            "success": True,
            "data": export_data
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/')
def index():
    """Serve the main HTML page"""
    return '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Shakil's Grocery Shop - MongoDB Edition</title>
    </head>
    <body>
        <h1>Shakil's Grocery Shop - MongoDB Edition</h1>
        <p>API is running! Access the web interface at <a href="/static/index.html">/static/index.html</a></p>
        
        <h2>API Endpoints:</h2>
        <ul>
            <li><strong>GET /api/items</strong> - Get all items</li>
            <li><strong>POST /api/items</strong> - Add new item</li>
            <li><strong>PUT /api/items/&lt;id&gt;</strong> - Update item</li>
            <li><strong>DELETE /api/items/&lt;id&gt;</strong> - Delete item</li>
            <li><strong>GET /api/items/search?q=term</strong> - Search items</li>
            <li><strong>GET /api/invoices</strong> - Get all invoices</li>
            <li><strong>POST /api/invoices</strong> - Create invoice</li>
            <li><strong>GET /api/invoices/&lt;id&gt;</strong> - Get specific invoice</li>
            <li><strong>GET /api/invoices/&lt;id&gt;/pdf</strong> - Download invoice PDF</li>
            <li><strong>GET /api/stats</strong> - Get sales statistics</li>
        </ul>
    </body>
    </html>
    '''

if __name__ == '__main__':
    print("Starting Flask API server...")
    print("MongoDB connection established!")
    
    # Get configuration from environment variables
    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    app.run(debug=debug_mode, host=host, port=port)
