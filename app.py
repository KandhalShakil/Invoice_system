from flask import Flask, request, jsonify, send_file, session
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, date, timedelta
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

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
CORS(app, supports_credentials=True)

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
# Create indexes for better performance
items_collection.create_index("item_name")
invoices_collection.create_index("invoice_id")
invoices_collection.create_index("customer_name")
auth_collection.create_index("email")
auth_collection.create_index("expires_at", expireAfterSeconds=0)

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

if not SMTP_EMAIL or not SMTP_PASSWORD:
    print("WARNING: SMTP credentials not found in .env file. Email functionality will not work.")

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

@app.route('/api/items', methods=['GET'])
def get_items():
    """Get all items"""
    try:
        items = list(items_collection.find())
        serialized_items = [serialize_doc(item) for item in items]
        return jsonify({"success": True, "items": serialized_items})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/items', methods=['POST'])
def add_item():
    """Add new item"""
    try:
        data = request.json
        item_name = data.get('item_name')
        item_price = float(data.get('item_price'))
        stock = int(data.get('stock'))
        unit = data.get('unit', 'pcs')  # Default to pieces if not specified
        
        # Check if item already exists
        existing_item = items_collection.find_one({"item_name": item_name})
        if existing_item:
            # Update stock if item exists
            items_collection.update_one(
                {"item_name": item_name},
                {"$inc": {"stock": stock}, "$set": {"unit": unit}}
            )
            updated_item = items_collection.find_one({"item_name": item_name})
            return jsonify({
                "success": True, 
                "message": f"Updated stock for {item_name}",
                "item": serialize_doc(updated_item)
            })
        else:
            # Create new item
            item_doc = {
                "item_name": item_name,
                "item_price": item_price,
                "stock": stock,
                "unit": unit,
                "created_at": datetime.now()
            }
            result = items_collection.insert_one(item_doc)
            item_doc["_id"] = result.inserted_id
            return jsonify({
                "success": True, 
                "message": f"Item {item_name} added successfully",
                "item": serialize_doc(item_doc)
            })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/items/<item_id>', methods=['PUT'])
def update_item(item_id):
    """Update item"""
    try:
        data = request.json
        update_data = {}
        
        if 'item_price' in data:
            update_data['item_price'] = float(data['item_price'])
        if 'stock' in data:
            if data.get('update_type') == 'add':
                items_collection.update_one(
                    {"_id": ObjectId(item_id)},
                    {"$inc": {"stock": int(data['stock'])}}
                )
            else:
                update_data['stock'] = int(data['stock'])
        
        if update_data:
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
def delete_item(item_id):
    """Delete item"""
    try:
        result = items_collection.delete_one({"_id": ObjectId(item_id)})
        if result.deleted_count > 0:
            return jsonify({"success": True, "message": "Item deleted successfully"})
        else:
            return jsonify({"success": False, "error": "Item not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/items/search', methods=['GET'])
def search_items():
    """Search items by name"""
    try:
        search_term = request.args.get('q', '')
        items = list(items_collection.find({"item_name": {"$regex": search_term, "$options": "i"}}))
        serialized_items = [serialize_doc(item) for item in items]
        return jsonify({"success": True, "items": serialized_items})
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
    """Calculate invoice totals using provided rates (in percentages)."""
    subtotal = sum(item["quantity"] * item["price"] for item in items)
    tax = subtotal * (tax_rate / 100)
    discount = subtotal * (discount_rate / 100)
    total = subtotal + tax - discount
    return subtotal, tax, discount, total

@app.route('/api/invoices', methods=['POST'])
def create_invoice():
    """Create new invoice"""
    try:
        data = request.json
        customer_name = data.get('customer_name')
        customer_address = data.get('customer_address')
        customer_number = data.get('customer_number')
        items = data.get('items', [])
        tax_rate = float(data.get('tax_rate', 0))
        discount_rate = float(data.get('discount_rate', 0))
        
        if not items:
            return jsonify({"success": False, "error": "No items provided"}), 400
        
        # Validate and update stock
        for item in items:
            db_item = items_collection.find_one({"_id": ObjectId(item['item_id'])})
            if not db_item:
                return jsonify({"success": False, "error": f"Item not found: {item['item_id']}"}), 400
            
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
            "items": items,
            "subtotal": subtotal,
            "tax": tax,
            "discount": discount,
            "tax_rate": tax_rate,
            "discount_rate": discount_rate,
            "total": total,
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
        return jsonify({
            "success": True,
            "message": "Invoice created successfully",
            "invoice": serialize_doc(invoice_doc)
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/invoices', methods=['GET'])
def get_invoices():
    """Get all invoices"""
    try:
        invoices = list(invoices_collection.find().sort("invoice_id", -1))
        serialized_invoices = [serialize_doc(invoice) for invoice in invoices]
        return jsonify({"success": True, "invoices": serialized_invoices})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/invoices/<int:invoice_id>', methods=['GET'])
def get_invoice(invoice_id):
    """Get specific invoice"""
    try:
        invoice = invoices_collection.find_one({"invoice_id": invoice_id})
        if invoice:
            return jsonify({"success": True, "invoice": serialize_doc(invoice)})
        else:
            return jsonify({"success": False, "error": "Invoice not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/invoices/<int:invoice_id>/pdf', methods=['GET'])
def generate_invoice_pdf(invoice_id):
    """Generate PDF for invoice"""
    try:
        # Get session token from header or query param
        session_token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not session_token:
            session_token = request.args.get('session_token', '')
        
        # Get shop details from auth
        shop_info = auth_collection.find_one({"session_token": session_token})
        
        # Default values if not found
        shop_name = shop_info.get('shop_name', "SHOP") if shop_info else "SHOP"
        shop_address = shop_info.get('shop_address', "") if shop_info else ""
        shop_phone = shop_info.get('shop_phone', "") if shop_info else ""
        owner_email = shop_info.get('email', "") if shop_info else ""
        
        invoice = invoices_collection.find_one({"invoice_id": invoice_id})
        if not invoice:
            return jsonify({"success": False, "error": "Invoice not found"}), 404
        
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
def get_stats():
    """Get sales statistics"""
    try:
        total_invoices = invoices_collection.count_documents({})
        total_revenue = list(invoices_collection.aggregate([
            {"$group": {"_id": None, "total": {"$sum": "$total"}}}
        ]))
        
        # Top customers
        top_customers = list(invoices_collection.aggregate([
            {"$group": {"_id": "$customer_name", "total_spent": {"$sum": "$total"}, "invoice_count": {"$sum": 1}}},
            {"$sort": {"total_spent": -1}},
            {"$limit": 5}
        ]))
        
        # Daily sales for the last 7 days
        daily_sales = list(invoices_collection.aggregate([
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