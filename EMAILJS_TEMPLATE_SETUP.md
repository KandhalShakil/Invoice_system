# EmailJS Template Setup Guide

## ⚠️ CRITICAL: How to Configure Your EmailJS Template

Your emails are sending but not showing OTP because the EmailJS template needs proper configuration.

## Step-by-Step Setup

### 1. Go to EmailJS Dashboard
- Visit: https://dashboard.emailjs.com/admin/templates
- Click on your template (ID: `template_x9d25fm`)

### 2. Configure Template Settings

Click "Settings" tab and set:

**To Email:**
```
{{to_email}}
```

**From Name:** (Optional)
```
Invoice System
```

**Subject:**
```
{{subject}}
```

### 3. Configure Template Content

In the "Content" editor, **DELETE EVERYTHING** and paste this:

```
{{{html_code}}}
```

**IMPORTANT:** Use **triple braces** `{{{html_code}}}` NOT double braces `{{html_code}}`

### 4. Alternative: Simple Text Template (If HTML doesn't work)

If you prefer a simple text template without HTML:

**Subject:**
```
{{subject}}
```

**Content:**
```
Your OTP Code: {{otp}}

This code will expire in 10 minutes.

If you didn't request this code, please ignore this email.

---
Invoice System
Professional Invoice Management
```

## Why Triple Braces?

- `{{variable}}` - Escapes HTML (shows code as text) ❌
- `{{{variable}}}` - Renders HTML (shows formatted email) ✅

## Test Your Template

1. Click "Test it" in EmailJS dashboard
2. Use these test values:
   ```
   to_email: your-email@example.com
   subject: Test Email
   html_code: <h1 style="color: blue;">Test OTP: 123456</h1>
   otp: 123456
   ```
3. Check your inbox - you should see a formatted email

## Current Template Variables

The system sends these parameters to EmailJS:

- `to_email` - Recipient email address
- `subject` - Email subject line
- `html_code` - Complete HTML email (for invoices and OTP)
- `otp` - Plain text OTP code (backup option)

## Troubleshooting

### Problem: Email shows HTML code as text
**Solution:** Change `{{html_code}}` to `{{{html_code}}}` (triple braces)

### Problem: Email recipient is empty
**Solution:** Set "To Email" field to `{{to_email}}` in template settings

### Problem: OTP not visible
**Solution:** 
1. Use `{{{html_code}}}` for formatted HTML, OR
2. Use `{{otp}}` for plain text code

## Need Help?

If you're still having issues:
1. Make sure you saved the template after editing
2. Try the simple text template with `{{otp}}` first
3. Check EmailJS logs in dashboard for errors
4. Verify your EmailJS account is active and not rate-limited
