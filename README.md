# GrandVPS - Cloud VPS Management Platform

A comprehensive Django-based platform for managing cloud VPS instances with integrated billing, wallet management, and payment processing.

## Features

- 🖥️ VPS Provisioning & Management
- 💰 Wallet & Payment System (Zarinpal integration)
- 📊 Billing & Invoice Management
- 👤 User Dashboard & Profile Management
- 🔒 Secure Authentication & Authorization
- 📱 Responsive Web Interface
- 🐳 Docker Containerization
- 🚀 Production Ready Deployment

## Quick Start

### Development Setup

1. **Clone the repository**

   ```bash
   git clone https://github.com/yourusername/grandvps.git
   cd grandvps
   ```

2. **Create virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Run migrations**

   ```bash
   python manage.py migrate
   ```

6. **Create superuser**

   ```bash
   python manage.py createsuperuser
   ```

7. **Run development server**

   ```bash
   python manage.py runserver
   ```

## Production Deployment

### Using Docker Compose

1. **Prepare environment**

   ```bash
   cp .env.production.example .env.production
   # Edit .env.production with your production settings
   ```

2. **SSL Certificates**
   Place your SSL certificate and private key in the `ssl/` directory:

   ```
   ssl/grandvps.crt
   ssl/grandvps.key
   ```

3. **Deploy**

   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

### Manual Deployment

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt gunicorn
   ```

2. **Configure production settings**

   ```bash
   export DJANGO_SETTINGS_MODULE=grandvps.settings_production
   ```

3. **Run migrations and collect static files**

   ```bash
   python manage.py migrate
   python manage.py collectstatic
   ```

4. **Start services**

   ```bash
   # Using systemd or supervisor
   gunicorn grandvps.wsgi:application --bind 0.0.0.0:8000
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Required |
| `DEBUG` | Debug mode | False |
| `DATABASE_URL` | PostgreSQL connection URL | Required |
| `REDIS_URL` | Redis connection URL | redis://localhost:6379 |
| `EMAIL_HOST` | SMTP server | Required |
| `DOPRAX_API_KEY` | Doprax API key | Required |

### Services

- **Django Application**: Main web application
- **PostgreSQL**: Primary database
- **Redis**: Cache and message broker
- **Nginx**: Web server and reverse proxy
- **Celery**: Background task processing

## API Documentation

### VPS Management

- `GET /vps/dashboard/` - List user's VPS instances
- `POST /vps/create/` - Create new VPS instance
- `POST /vps/{id}/start/` - Start VPS instance
- `POST /vps/{id}/stop/` - Stop VPS instance

### Wallet Management

- `GET /wallet/dashboard/` - Wallet balance and transactions
- `POST /wallet/deposit/` - Initiate deposit
- `POST /wallet/withdraw/` - Request withdrawal

### Billing

- `GET /billing/dashboard/` - Billing overview
- `GET /billing/history/` - Invoice history

## Testing

```bash
# Run all tests
python manage.py test

# Run with coverage
pip install coverage
coverage run manage.py test
coverage report
```

## Monitoring

- Health check endpoint: `GET /health/`
- Application logs: `/var/log/django/grandvps.log`
- Nginx logs: `/var/log/nginx/`

## Security

- SSL/TLS encryption
- CSRF protection
- Rate limiting
- Secure headers
- Input validation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:

- Email: <support@yourdomain.com>
- Documentation: [Link to docs]

---

Built with ❤️ using Django, Docker, and modern web technologies.
