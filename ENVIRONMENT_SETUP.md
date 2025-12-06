# Environment Configuration Guide

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` file and add your credentials:
   - **MONGODB_URI**: Your MongoDB connection string
   - **SMTP_EMAIL**: Your Gmail address
   - **SMTP_PASSWORD**: Gmail App Password (not regular password)
   - **FLASK_SECRET_KEY**: Generate using Python:
     ```python
     import secrets
     print(secrets.token_hex(32))
     ```

### 3. Gmail App Password Setup

To send OTP emails, you need a Gmail App Password:

1. Go to [Google Account Settings](https://myaccount.google.com/)
2. Enable 2-Factor Authentication (if not already enabled)
3. Go to [App Passwords](https://myaccount.google.com/apppasswords)
4. Select "Mail" and your device
5. Copy the 16-character password
6. Add it to `.env` as `SMTP_PASSWORD`

### 4. MongoDB Setup

1. Create a free account at [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a cluster
3. Create a database user
4. Get the connection string
5. Add it to `.env` as `MONGODB_URI`

### 5. Run the Application

```bash
python app.py
```

Access at: http://127.0.0.1:5000/login.html

## Security Notes

- ✅ Never commit `.env` file to version control
- ✅ `.env` is already in `.gitignore`
- ✅ Use strong, unique passwords
- ✅ Rotate credentials periodically
- ✅ Use environment-specific `.env` files for development/production
- ✅ For production, use proper secret management (AWS Secrets Manager, Azure Key Vault, etc.)

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| MONGODB_URI | Yes | - | MongoDB connection string |
| MONGODB_DATABASE | No | grocery_shop | Database name |
| SMTP_SERVER | No | smtp.gmail.com | SMTP server address |
| SMTP_PORT | No | 587 | SMTP server port |
| SMTP_EMAIL | Yes | - | Email address for sending OTPs |
| SMTP_PASSWORD | Yes | - | Email app password |
| FLASK_SECRET_KEY | No | auto-generated | Flask secret key for sessions |
| FLASK_DEBUG | No | False | Enable/disable debug mode |
| FLASK_HOST | No | 0.0.0.0 | Server host address |
| FLASK_PORT | No | 5000 | Server port number |

## Troubleshooting

### Email not sending?
- Verify SMTP credentials in `.env`
- Check if Gmail App Password is correct
- Ensure 2FA is enabled on Gmail account

### Database connection error?
- Verify MongoDB URI is correct
- Check if your IP is whitelisted in MongoDB Atlas
- Ensure database user has proper permissions

### Server not starting?
- Check if port 5000 is available
- Verify all required environment variables are set
- Check console for error messages
