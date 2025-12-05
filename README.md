# Shakil's Grocery Shop - MongoDB Edition

A modern invoice management system with MongoDB backend and web frontend.

## Features

- 🏪 **Inventory Management**: Add, update, and track items
- 🧾 **Invoice Generation**: Create invoices with automatic PDF generation
- 📊 **Dashboard**: Sales statistics and analytics
- 🔍 **Search**: Find items and invoices quickly
- 📱 **Responsive Design**: Works on desktop and mobile
- 🌐 **Web Interface**: Modern HTML/CSS/JavaScript frontend
- 🐍 **Python Backend**: Flask API with MongoDB integration

## MongoDB Connection

The application connects to MongoDB Atlas cluster:
```
mongodb+srv://kandhalshakil_db_user:ZTYYDRunhuBTz8sn@cluster0.omdl2yo.mongodb.net/
```

Database: `grocery_shop`
Collections: `items`, `invoices`

## Installation

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Run the Flask web server:**
```bash
python app.py
```

3. **Run the console application (optional):**
```bash
python mongodb_invoice_generator.py
```

## Web Interface

After starting the Flask server, open your browser and go to:
- Main interface: `http://localhost:5000/static/index.html`
- API documentation: `http://localhost:5000/`

### Features Available:

1. **Dashboard**: View sales statistics, top customers, and recent sales
2. **Items Management**: Add, update, delete, and search inventory items
3. **Create Invoice**: Generate new invoices with customer details and items
4. **View Invoices**: Browse all invoices and download PDFs

## API Endpoints

- `GET /api/items` - Get all items
- `POST /api/items` - Add new item
- `PUT /api/items/<id>` - Update item
- `DELETE /api/items/<id>` - Delete item
- `GET /api/items/search?q=term` - Search items
- `GET /api/invoices` - Get all invoices
- `POST /api/invoices` - Create invoice
- `GET /api/invoices/<id>` - Get specific invoice
- `GET /api/invoices/<id>/pdf` - Download invoice PDF
- `GET /api/stats` - Get sales statistics

## Console Application

The console application (`mongodb_invoice_generator.py`) provides a command-line interface with the following features:

1. Add items to inventory
2. View all items
3. Update item price or stock
4. Remove items
5. Generate invoices (with PDF)
6. Display sales graphs (matplotlib)
7. View sales reports
8. Find invoices by ID
9. Search items
10. Show all invoices

## File Structure

```
PYTHON_PROJECT_INDIVIDUAL/
│
├── app.py                          # Flask web server
├── mongodb_invoice_generator.py    # Console application
├── requirements.txt                # Python dependencies
├── README.md                       # This file
│
└── static/
    └── index.html                  # Web interface
```

## MongoDB Collections

### Items Collection
```json
{
  "_id": ObjectId,
  "item_name": "string",
  "item_price": "number",
  "stock": "number",
  "created_at": "datetime"
}
```

### Invoices Collection
```json
{
  "_id": ObjectId,
  "invoice_id": "number",
  "customer_name": "string",
  "customer_address": "string",
  "customer_number": "string",
  "items": [
    {
      "item_id": "string",
      "name": "string",
      "quantity": "number",
      "price": "number"
    }
  ],
  "subtotal": "number",
  "tax": "number",
  "discount": "number",
  "total": "number",
  "order_date": "datetime",
  "created_at": "datetime"
}
```

## Business Logic

- **Tax**: 5% of subtotal
- **Discount**: 2% of subtotal
- **Stock Management**: Automatic stock deduction on invoice creation
- **Invoice Numbering**: Sequential auto-increment
- **PDF Generation**: Automatic PDF creation with company branding

## Usage Examples

### Adding Items via Web Interface:
1. Go to "Items" tab
2. Fill in item name, price, and stock
3. Click "Add Item"

### Creating Invoice via Web Interface:
1. Go to "Create Invoice" tab
2. Enter customer information
3. Select items and quantities
4. Click "Generate Invoice"
5. Download PDF if desired

### Using Console Application:
```bash
python mongodb_invoice_generator.py
```
Follow the menu prompts to manage inventory and create invoices.

## Technologies Used

- **Backend**: Python, Flask, PyMongo
- **Database**: MongoDB Atlas
- **PDF Generation**: ReportLab
- **Charts**: Matplotlib
- **Frontend**: HTML5, CSS3, JavaScript
- **Styling**: Custom CSS with responsive design

## Shop Details

- **Name**: Shakil's Grocery Shop
- **Location**: Ahmedabad
- **Contact**: +91 9725845511
- **Email**: kandhalshakil@shakil.com

## License

This project is for educational and business purposes.