# 📋 Invoice Management System

A professional invoice management system with inventory tracking, customer management, and automated email delivery.

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com)

## 🌐 Live Deployment

- **Frontend (Vercel)**: https://kandhal-invoice-system.vercel.app
- **Backend API (Render)**: https://invoice-system-vpmz.onrender.com

## ✨ Features

- 🏪 **Multi-Store Management** - Manage multiple shops from one account
- 📦 **Inventory Management** - Track items, stock, and prices
- 👥 **Customer Database** - Store customer information and purchase history
- 📄 **Invoice Generation** - Create professional invoices with PDF export
- 📧 **Email Delivery** - Send invoices directly via EmailJS
- 📊 **Sales Dashboard** - View real-time statistics and insights
- 🔐 **Secure Authentication** - Email-based OTP verification
- 📱 **Responsive Design** - Works seamlessly on all devices
- 🎨 **Modern UI** - Beautiful gradient design with smooth animations

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- MongoDB Atlas account
- EmailJS account (for email functionality)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/KandhalShakil/Invoice_system.git
   cd Invoice_system
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # Windows
   source .venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   
   Create a `.env` file in the root directory:
   ```env
   MONGODB_URI=your_mongodb_connection_string
   MONGODB_DATABASE=grocery_shop
   FLASK_SECRET_KEY=your_secret_key_here
   FLASK_ENV=development
   FLASK_DEBUG=True
   FLASK_HOST=0.0.0.0
   FLASK_PORT=5000
   ```

5. **Run the application**
   ```bash
   python app.py
   ```

6. **Access the app**
   - Open browser: http://localhost:5000/static/index.html

## 🌍 Deployment

### Deploy Backend to Render

1. Fork/clone this repository to your GitHub account
2. Go to [Render Dashboard](https://dashboard.render.com/)
3. Click "New +" → "Web Service"
4. Connect your GitHub repository
5. Render will automatically detect `render.yaml` and configure deployment
6. Add environment variable:
   - `MONGODB_URI`: Your MongoDB connection string
7. Click "Create Web Service"
8. Your backend will be live at: `https://YOUR-APP-NAME.onrender.com`

### Deploy Frontend to Vercel

1. Go to [Vercel Dashboard](https://vercel.com/dashboard)
2. Click "Add New" → "Project"
3. Import your GitHub repository
4. Vercel will automatically detect `vercel.json` configuration
5. Click "Deploy"
6. Your frontend will be live at: `https://YOUR-APP-NAME.vercel.app`

### Post-Deployment Configuration

After deploying, update the CORS origins in `app.py`:

```python
CORS(app, 
     supports_credentials=True,
     origins=[
         'https://YOUR-VERCEL-APP.vercel.app',  # Add your Vercel URL
         'http://localhost:3000',
         'http://127.0.0.1:5000',
     ],
     ...)
```

Also update the `Access-Control-Allow-Origin` in the `@app.after_request` function.

## 📧 Email Configuration (EmailJS)

1. Create account at [EmailJS](https://www.emailjs.com/)
2. Create email service (Gmail/Outlook/etc.)
3. Create email template with these variables:
   - `{{to_email}}` - Recipient email (⚠️ MUST be set in template's "To Email" field)
   - `{{shop_name}}` - Shop name
   - `{{invoice_id}}` - Invoice number
   - `{{items_list}}` - HTML table of items
   - `{{total}}` - Total amount
   - (See full list in `static/index.html`)
4. Get your credentials:
   - Service ID
   - Template ID
   - Public Key
5. Update in `static/index.html` (lines 4152-4154)

### Important EmailJS Setup

⚠️ **Critical Step**: In your EmailJS template settings:
- Go to: https://dashboard.emailjs.com/admin/templates/YOUR_TEMPLATE_ID
- Edit template → Settings
- **Set "To Email" field to**: `{{to_email}}`
- Save template

Without this, you'll get "The recipients address is empty" error.

## 📂 Project Structure

```
Invoice_system/
├── app.py                  # Flask backend API
├── requirements.txt        # Python dependencies
├── render.yaml            # Render deployment config
├── vercel.json            # Vercel deployment config
├── .env                   # Environment variables (create this)
├── .gitignore             # Git ignore rules
├── static/
│   └── index.html         # Frontend SPA
├── INVOICE_GENERATOR.py   # Legacy invoice generator
└── README.md              # This file
```

## 🔧 Technologies Used

### Backend
- **Flask** - Python web framework
- **PyMongo** - MongoDB driver
- **ReportLab** - PDF generation
- **Gunicorn** - Production WSGI server
- **Flask-CORS** - Cross-origin resource sharing

### Frontend
- **Vanilla JavaScript** - No frameworks, pure JS
- **EmailJS** - Browser-based email service
- **HTML5/CSS3** - Modern responsive design
- **QRCode.js** - QR code generation

### Database
- **MongoDB Atlas** - Cloud database

### Deployment
- **Render** - Backend hosting
- **Vercel** - Frontend hosting
- **GitHub** - Version control

## 🔐 Security Features

- ✅ Password hashing (SHA-256)
- ✅ Email OTP verification
- ✅ Session token authentication (24-hour expiry)
- ✅ Environment variable protection
- ✅ CORS configuration
- ✅ HttpOnly cookies
- ✅ MongoDB Atlas encryption

## 📊 API Endpoints

### Authentication
- `POST /api/auth/send-signup-otp` - Send signup verification OTP
- `POST /api/auth/verify-signup` - Verify OTP and create account
- `POST /api/auth/login` - Login with email/password
- `POST /api/auth/logout` - Logout and invalidate session
- `POST /api/auth/verify-session` - Check if session is valid
- `POST /api/auth/forgot-password` - Request password reset OTP
- `POST /api/auth/reset-password` - Reset password with OTP

### Items Management
- `GET /api/items` - Get all items
- `POST /api/items` - Add new item
- `PUT /api/items/<id>` - Update item
- `DELETE /api/items/<id>` - Delete item
- `GET /api/items/search?q=<query>` - Search items
- `GET /api/items/<id>/qrcode` - Get item QR code

### Customers Management
- `GET /api/customers` - Get all customers
- `POST /api/customers` - Add new customer
- `PUT /api/customers/<id>` - Update customer
- `DELETE /api/customers/<id>` - Delete customer
- `GET /api/customers/search?q=<query>` - Search customers

### Invoices
- `GET /api/invoices` - Get all invoices
- `POST /api/invoices` - Create new invoice
- `GET /api/invoices/<id>` - Get specific invoice
- `GET /api/invoices/<id>/pdf` - Download invoice PDF

### Statistics
- `GET /api/stats` - Get sales statistics
- `GET /api/export/all-data` - Export all data as JSON

### Health
- `GET /health` - Health check endpoint

## 🎯 Usage Guide

### First Time Setup

1. **Sign Up**
   - Enter your shop details
   - Verify email with OTP
   - Login to dashboard

2. **Add Items**
   - Go to "Items" tab
   - Add products with prices
   - Manage stock levels

3. **Add Customers**
   - Go to "Customers" tab
   - Add customer information
   - Track purchase history

4. **Create Invoices**
   - Go to "Create Invoice" tab
   - Select customer and items
   - Set tax/discount rates
   - Generate and send invoice

### Features Walkthrough

- **Dashboard**: View sales statistics and recent activity
- **Items**: Manage inventory with QR codes
- **Customers**: Store and search customer database
- **Create Invoice**: Generate professional invoices
- **View Invoices**: Browse and download past invoices

## 🐛 Troubleshooting

### Render Free Tier Sleeps

Render free tier apps sleep after 15 minutes of inactivity. First request may take 30-60 seconds to wake up.

**Solution**: The frontend automatically pings `/health` endpoint to wake the server.

### Email Not Sending

**Error**: "The recipients address is empty" (422)

**Solution**: Configure EmailJS template:
1. Go to EmailJS Dashboard
2. Edit your template
3. Set "To Email" field to: `{{to_email}}`
4. Save and retry

### CORS Errors

**Error**: "Access-Control-Allow-Origin" blocked

**Solution**: Add your Vercel URL to CORS origins in `app.py`:
```python
origins=[
    'https://your-app.vercel.app',
    ...
]
```

### MongoDB Connection Issues

**Error**: "MongoServerError" or connection timeout

**Solutions**:
- Check MongoDB Atlas IP whitelist (allow 0.0.0.0/0)
- Verify connection string in `.env`
- Ensure database user has read/write permissions

## 📝 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| MONGODB_URI | Yes | - | MongoDB connection string |
| MONGODB_DATABASE | No | grocery_shop | Database name |
| FLASK_SECRET_KEY | No | auto-generated | Flask secret key |
| FLASK_ENV | No | development | Environment (development/production) |
| FLASK_DEBUG | No | False | Debug mode |
| FLASK_HOST | No | 0.0.0.0 | Server host |
| FLASK_PORT | No | 5000 | Server port |

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 👤 Author

**Shakil Kandhal**
- GitHub: [@KandhalShakil](https://github.com/KandhalShakil)
- Email: shakilkandhal@gmail.com

## 🙏 Acknowledgments

- Flask and Python community
- MongoDB for database
- EmailJS for email service
- Render and Vercel for hosting
- All open-source contributors

## 📞 Support

If you encounter any issues or have questions:

1. Check [Troubleshooting](#-troubleshooting) section
2. Open an [Issue](https://github.com/KandhalShakil/Invoice_system/issues)
3. Contact: shakilkandhal@gmail.com

---

Made with ❤️ by Shakil Kandhal | Deployed on [Render](https://render.com) & [Vercel](https://vercel.com)
