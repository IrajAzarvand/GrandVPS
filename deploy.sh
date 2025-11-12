#!/bin/bash

# GrandVPS Production Deployment Script
# This script sets up the production environment using Docker

set -e

echo "🚀 Starting GrandVPS production deployment..."

# Check if .env.production exists
if [ ! -f .env.production ]; then
    echo "❌ .env.production file not found!"
    echo "📝 Please copy .env.production.example to .env.production and configure your settings."
    exit 1
fi

# Create SSL directory if it doesn't exist
mkdir -p ssl

# Check if SSL certificates exist
if [ ! -f ssl/grandvps.crt ] || [ ! -f ssl/grandvps.key ]; then
    echo "⚠️  SSL certificates not found in ssl/ directory."
    echo "📝 Please place your SSL certificate (grandvps.crt) and private key (grandvps.key) in the ssl/ directory."
    echo "🔄 Continuing without SSL for now..."
fi

# Build and start services
echo "🐳 Building Docker images..."
docker-compose build

echo "🚀 Starting services..."
docker-compose up -d

# Wait for services to be healthy
echo "⏳ Waiting for services to be ready..."
sleep 30

# Run database migrations
echo "🗄️ Running database migrations..."
docker-compose exec web python manage.py migrate

# Collect static files
echo "📁 Collecting static files..."
docker-compose exec web python manage.py collectstatic --noinput

# Create superuser (optional)
echo "👤 Do you want to create a superuser? (y/n)"
read -r create_superuser
if [ "$create_superuser" = "y" ] || [ "$create_superuser" = "Y" ]; then
    docker-compose exec web python manage.py createsuperuser
fi

# Restart services to apply changes
echo "🔄 Restarting services..."
docker-compose restart

echo "✅ Deployment completed successfully!"
echo "🌐 Your application should be available at https://yourdomain.com"
echo ""
echo "📊 To check service status: docker-compose ps"
echo "📜 To view logs: docker-compose logs -f"
echo "🛑 To stop services: docker-compose down"