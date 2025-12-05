from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
from datetime import datetime, date
import json
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
import os
import tempfile

app = Flask(__name__)
CORS(app)

# MongoDB connection
connection_string = "mongodb+srv://kandhalshakil_db_user:ZTYYDRunhuBTz8sn@cluster0.omdl2yo.mongodb.net/"
client = MongoClient(connection_string)
db = client.grocery_shop
items_collection = db.items
invoices_collection = db.invoices

# Create indexes for better performance
items_collection.create_index("item_name")
invoices_collection.create_index("invoice_id")
invoices_collection.create_index("customer_name")

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
        invoice = invoices_collection.find_one({"invoice_id": invoice_id})
        if not invoice:
            return jsonify({"success": False, "error": "Invoice not found"}), 404
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
        temp_filename = temp_file.name
        temp_file.close()
        
        # Generate PDF
        c = canvas.Canvas(temp_filename, pagesize=letter)
        
        shop_name = "SHAKIL'S GROCERY SHOP"
        shop_address = "Satellite Road, Ahmedabad, Gujarat - 380015"
        shop_contact = "+91 9725845511"
        shop_email = "kandhalshakil@shakil.com"
        shop_gst = "24ABCDE1234F2Z5"
        
        # Shop Info Header
        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(colors.darkblue)
        c.drawString(50, 750, shop_name)
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.black)
        c.drawString(470, 750, invoice['order_date'].strftime("%d/%m/%Y"))
        c.line(50, 740, 550, 740)
        
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, 725, "From: Kandhal Shakil")
        c.drawString(50, 710, f"Shop Address: {shop_address}")
        c.drawString(50, 695, f"Contact Number: {shop_contact}")
        c.drawString(50, 680, f"Shop Email: {shop_email}")
        
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
        # Footer
        c.setFont("Helvetica", 8)
        c.drawString(50, 50, "Thank you for your business!")
        
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
    app.run(debug=False, host='0.0.0.0', port=5000)