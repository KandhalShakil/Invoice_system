# Security Best Practices - Grocery Shop Invoice System

## ✅ Implemented Security Measures

### 1. Environment Variables (.env)
All sensitive credentials are now stored in `.env` file:
- MongoDB connection string
- SMTP email credentials
- Flask secret key
- Server configuration

**Benefits:**
- Credentials separated from code
- Easy to change without code modification
- Not committed to version control
- Different configs for dev/staging/production

### 2. .gitignore Protection
`.env` file is listed in `.gitignore` to prevent accidental commits of sensitive data.

### 3. Password Security
- Passwords are hashed using SHA-256 before storage
- No plaintext passwords in database
- Password must be minimum 6 characters

### 4. Email Verification
- OTP-based email verification during signup
- 6-digit random OTP with 10-minute expiration
- Prevents fake account creation

### 5. Session Management
- 24-hour session expiration
- Secure session tokens (32-byte random)
- Session verification on protected routes
- Automatic session cleanup on expiry

### 6. CORS Configuration
- CORS enabled with credentials support
- Protects against unauthorized cross-origin requests

### 7. HTTP Security Headers
- Session cookies set to HttpOnly
- SameSite cookie policy (Lax)

## 🔒 Additional Security Recommendations

### For Production Deployment:

#### 1. Use HTTPS
```python
# Force HTTPS in production
if not app.debug:
    from flask_talisman import Talisman
    Talisman(app)
```

#### 2. Stronger Password Hashing
Replace SHA-256 with bcrypt or Argon2:
```python
# Install: pip install bcrypt
import bcrypt

# Hashing
password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

# Verification
bcrypt.checkpw(password.encode(), stored_hash)
```

#### 3. Rate Limiting
Prevent brute force attacks:
```python
# Install: pip install flask-limiter
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: request.remote_addr)

@app.route('/api/auth/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    # ...
```

#### 4. Input Validation
Add comprehensive input validation for all endpoints.

#### 5. SQL/NoSQL Injection Prevention
- Already using PyMongo's built-in query protection
- Always use parameterized queries

#### 6. Environment-Specific Configs
```bash
# Development
.env.development

# Production
.env.production

# Load based on environment
from dotenv import load_dotenv
import os

env = os.getenv('FLASK_ENV', 'development')
load_dotenv(f'.env.{env}')
```

#### 7. Secrets Management
For production, use proper secret management:
- **AWS**: AWS Secrets Manager
- **Azure**: Azure Key Vault
- **GCP**: Google Secret Manager
- **Docker**: Docker Secrets
- **Kubernetes**: Kubernetes Secrets

#### 8. Security Headers
Add comprehensive security headers:
```python
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response
```

#### 9. Database Connection Security
- Use connection pooling
- Enable MongoDB authentication
- Restrict database user permissions
- Use IP whitelisting in MongoDB Atlas

#### 10. Logging & Monitoring
- Log all authentication attempts
- Monitor for suspicious activity
- Set up alerts for failed login attempts
- Never log sensitive data (passwords, tokens)

## 📋 Security Checklist

- [x] Environment variables for sensitive data
- [x] .gitignore configured
- [x] Password hashing implemented
- [x] Email verification enabled
- [x] Session management with expiration
- [x] CORS properly configured
- [x] HttpOnly cookies
- [ ] HTTPS enforcement (production)
- [ ] Rate limiting
- [ ] Strong password hashing (bcrypt/Argon2)
- [ ] Input validation & sanitization
- [ ] Security headers
- [ ] Error handling (no sensitive info in errors)
- [ ] Logging & monitoring
- [ ] Regular security audits
- [ ] Dependency updates

## 🚨 Important Warnings

1. **Never commit `.env` file** - It contains sensitive credentials
2. **Rotate credentials regularly** - Change passwords and tokens periodically
3. **Use strong passwords** - For database, email, and Flask secret key
4. **Different credentials per environment** - Dev, staging, and production should use separate credentials
5. **Monitor for vulnerabilities** - Keep dependencies updated
6. **Backup encryption keys** - Store Flask secret key securely

## 🔄 Credential Rotation Procedure

### When to Rotate:
- Every 90 days (recommended)
- When employee leaves
- After security incident
- If credentials are suspected to be compromised

### How to Rotate:

1. **MongoDB Password:**
   - Generate new password in MongoDB Atlas
   - Update `.env` file
   - Restart application

2. **Gmail App Password:**
   - Revoke old app password in Google Account
   - Generate new app password
   - Update `.env` file
   - Restart application

3. **Flask Secret Key:**
   ```python
   import secrets
   print(secrets.token_hex(32))
   ```
   - Copy new key to `.env`
   - Restart application
   - All users will need to re-login

## 📞 Security Contact

If you discover a security vulnerability:
1. Do NOT create a public GitHub issue
2. Contact the development team privately
3. Provide details about the vulnerability
4. Allow time for fix before public disclosure

## 📚 Additional Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Flask Security Best Practices](https://flask.palletsprojects.com/en/2.3.x/security/)
- [MongoDB Security Checklist](https://docs.mongodb.com/manual/administration/security-checklist/)
- [Python Security Best Practices](https://python.readthedocs.io/en/stable/library/security_warnings.html)
