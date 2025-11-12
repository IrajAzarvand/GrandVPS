#!/bin/bash

# SSL Certificate Setup Script for GrandVPS
# This script helps obtain and configure SSL certificates using Let's Encrypt

set -e

DOMAIN=${1:-"yourdomain.com"}
EMAIL=${2:-"admin@yourdomain.com"}

echo "🔐 Setting up SSL certificates for $DOMAIN"

# Check if certbot is installed
if ! command -v certbot &> /dev/null; then
    echo "📦 Installing certbot..."
    # For Ubuntu/Debian
    sudo apt update
    sudo apt install -y certbot python3-certbot-nginx
fi

# Stop nginx temporarily for certificate generation
echo "⏸️ Stopping nginx..."
sudo systemctl stop nginx || true

# Obtain SSL certificate
echo "📜 Obtaining SSL certificate from Let's Encrypt..."
sudo certbot certonly --standalone \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN" \
    -d "www.$DOMAIN"

# Copy certificates to project directory
echo "📋 Copying certificates to project..."
sudo cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ../ssl/grandvps.crt
sudo cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" ../ssl/grandvps.key

# Set proper permissions
sudo chown $(whoami):$(whoami) ../ssl/grandvps.crt ../ssl/grandvps.key
chmod 600 ../ssl/grandvps.key

# Restart nginx
echo "▶️ Starting nginx..."
sudo systemctl start nginx

# Set up auto-renewal
echo "🔄 Setting up certificate auto-renewal..."
sudo crontab -l | grep -v "certbot renew" | { cat; echo "0 12 * * * /usr/bin/certbot renew --quiet && systemctl reload nginx"; } | sudo crontab -

echo "✅ SSL setup completed!"
echo "📄 Certificate location: ssl/grandvps.crt, ssl/grandvps.key"
echo "🔄 Auto-renewal configured for monthly renewal"
echo ""
echo "📝 Next steps:"
echo "1. Update your domain DNS to point to this server"
echo "2. Update ALLOWED_HOSTS in settings_production.py"
echo "3. Run: docker-compose restart nginx"