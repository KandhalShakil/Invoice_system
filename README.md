# 🛒 Grocery Shop Invoice System

A comprehensive web-based invoice management system for grocery shops with MongoDB integration, email verification, and PDF invoice generation.

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![Flask](https://img.shields.io/badge/Flask-3.0.0-green.svg)
![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 📋 Features

### 🔐 Authentication & Security
- **Email Verification** - OTP-based email verification during signup
- **Password Authentication** - Secure password-based login system
- **Forgot Password** - OTP-based password reset via email
- **Session Management** - 24-hour session tokens with automatic expiry
- **Environment Variables** - Secure credential management with `.env`

### 📦 Inventory Management
- Add, edit, and delete items
- Real-time stock tracking
- Unit support (kg, liters, pieces, etc.)
- Search functionality
- Stock alerts and management

### 🧾 Invoice Generation
- Create detailed invoices with multiple items
- Automatic calculations (subtotal, tax, discount)
- Customer information management
- Invoice history and tracking
- PDF invoice generation and download

### 📊 Dashboard & Analytics
- Sales statistics and trends
- Revenue tracking
- Top customers analysis
- Daily sales charts
- Inventory overview

### 📄 PDF Generation
- Professional invoice PDFs
- Dynamic shop details
- Indian Rupee (Rs) formatting
- Download and email support

## 🚀 Quick Start

### Prerequisites
- Python 3.11 or higher
- MongoDB Atlas account
- Gmail account with App Password enabled

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/KandhalShakil/Invoice_system.git
cd Invoice_system
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure environment variables**
```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
# - MongoDB connection string
# - Gmail email and app password
# - Flask secret key
```

4. **Run the application**
```bash
python app.py
```

5. **Access the application**
- Login: http://127.0.0.1:5000/login.html
- Main App: http://127.0.0.1:5000/index.html

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the root directory:

```env
# MongoDB Configuration
MONGODB_URI=your_mongodb_connection_string
MONGODB_DATABASE=grocery_shop

# SMTP Email Configuration
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your_email@gmail.com
SMTP_PASSWORD=your_app_password

# Flask Configuration
FLASK_SECRET_KEY=your_secret_key_here
FLASK_DEBUG=False
FLASK_HOST=0.0.0.0
FLASK_PORT=5000
```

### Gmail App Password Setup

1. Enable 2-Factor Authentication in your Google Account
2. Go to [App Passwords](https://myaccount.google.com/apppasswords)
3. Generate a new app password for "Mail"
4. Copy the 16-character password to `.env`

See [ENVIRONMENT_SETUP.md](ENVIRONMENT_SETUP.md) for detailed setup instructions.

## 📁 Project Structure

```
Invoice_system/
│
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (not in git)
├── .env.example               # Environment template
├── .gitignore                 # Git ignore rules
│
├── static/
│   ├── index.html             # Main application interface
│   └── login.html             # Authentication interface
│
├── ENVIRONMENT_SETUP.md       # Environment setup guide
├── SECURITY.md                # Security best practices
└── README.md                  # This file
```

## 🎨 Screenshots

### Authentication
- **Signup** - Email verification with OTP
- **Login** - Password-based authentication
- **Forgot Password** - OTP-based password reset

### Dashboard
- Real-time statistics
- Sales overview
- Inventory status
- Quick actions

### Invoice Management
- Create new invoices
- View invoice history
- Download PDF invoices
- Customer management

## 🔒 Security Features

- ✅ Password hashing (SHA-256)
- ✅ Email verification with OTP
- ✅ Session token authentication
- ✅ Environment variable protection
- ✅ CORS configuration
- ✅ HttpOnly cookies
- ✅ Session expiration
- ✅ Input validation

See [SECURITY.md](SECURITY.md) for comprehensive security documentation.

## 📚 API Endpoints

### Authentication
- `POST /api/auth/send-signup-otp` - Send signup verification OTP
- `POST /api/auth/verify-signup` - Verify OTP and create account
- `POST /api/auth/login` - Login with email and password
- `POST /api/auth/forgot-password` - Send password reset OTP
- `POST /api/auth/reset-password` - Reset password with OTP
- `POST /api/auth/verify-session` - Verify session token
- `POST /api/auth/logout` - Logout and clear session

### Items (Inventory)
- `GET /api/items` - Get all items
- `POST /api/items` - Add new item
- `PUT /api/items/<id>` - Update item
- `DELETE /api/items/<id>` - Delete item
- `GET /api/items/search?q=term` - Search items

### Invoices
- `GET /api/invoices` - Get all invoices
- `POST /api/invoices` - Create new invoice
- `GET /api/invoices/<id>` - Get specific invoice
- `GET /api/invoices/<id>/pdf` - Download invoice PDF
- `DELETE /api/invoices/<id>` - Delete invoice

### Analytics
- `GET /api/stats` - Get sales statistics and dashboard data

## 🛠️ Technologies Used

- **Backend**: Flask 3.0.0, Python 3.11+
- **Database**: MongoDB Atlas
- **PDF Generation**: ReportLab
- **Email**: SMTP (Gmail)
- **Frontend**: HTML5, CSS3, Vanilla JavaScript
- **Authentication**: Session-based with OTP verification
- **Security**: python-dotenv, hashlib

## 📖 Usage Guide

### First Time Setup

1. **Create Account**
   - Click "Create Account" on login page
   - Fill in shop details and create password
   - Verify email with OTP sent to your inbox
   - Login with your credentials

2. **Add Inventory**
   - Navigate to "Manage Items"
   - Click "Add New Item"
   - Enter item details (name, price, stock, unit)
   - Click "Add Item"

3. **Create Invoice**
   - Go to "Create Invoice"
   - Enter customer details
   - Add items to invoice
   - Set tax and discount (optional)
   - Click "Generate Invoice"
   - Download PDF or view online

4. **View Analytics**
   - Check dashboard for sales overview
   - View top customers
   - Monitor daily sales trends
   - Track inventory levels

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 👨‍💻 Author

**Kandhal Shakil**
- GitHub: [@KandhalShakil](https://github.com/KandhalShakil)
- Email: kandhalshakil@gmail.com

## 🙏 Acknowledgments

- Flask framework and community
- MongoDB Atlas for cloud database
- ReportLab for PDF generation
- Bootstrap & modern CSS for UI inspiration

## 📞 Support

For support, email kandhalshakil@gmail.com or create an issue in the repository.

## 🔄 Version History

- **v1.0.0** (December 2025)
  - Initial release
  - Email verification system
  - Password-based authentication
  - Invoice management
  - PDF generation
  - Dashboard analytics
  - Environment variable security

## 🚧 Future Enhancements

- [ ] Multi-language support
- [ ] Dark mode theme
- [ ] Export data to Excel
- [ ] SMS notifications
- [ ] Payment gateway integration
- [ ] Mobile app (React Native)
- [ ] Advanced reporting
- [ ] Barcode scanner integration
- [ ] Multi-store support
- [ ] Role-based access control

---

⭐ **Star this repository if you find it helpful!**