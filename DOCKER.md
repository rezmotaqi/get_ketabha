# 🐳 Docker Deployment Guide for Telegram LibGen Bot

This guide provides comprehensive instructions for deploying the Telegram LibGen Bot using Docker and Docker Compose.

## 📋 Prerequisites

- Docker Engine 20.10+ 
- Docker Compose 2.0+
- Git (to clone the repository)
- A Telegram Bot Token from [@BotFather](https://t.me/BotFather)

## 🚀 Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd get_ketabha

# Copy environment template
cp env.template .env

# Edit .env file with your bot token
nano .env
```

### 2. Configure Environment

Edit the `.env` file and set your bot token:

```bash
# Required: Get from @BotFather
TELEGRAM_BOT_TOKEN=your_actual_bot_token_here

# Optional: Customize other settings
LOG_LEVEL=INFO
LIBGEN_MAX_RESULTS=100
BOT_BOOKS_PER_PAGE=3
```

### 3. Run with Docker Compose

```bash
# Production deployment
docker-compose up -d

# Development with hot reload
docker-compose --profile dev up -d

# Alpine variant (smaller image)
docker-compose --profile alpine up -d
```

## 🏗️ Docker Images

### Multi-Stage Build

The Dockerfile includes three stages:

1. **`base`** - Common dependencies and system packages
2. **`development`** - Development tools and hot reload
3. **`production`** - Optimized production image
4. **`alpine`** - Minimal Alpine Linux variant

### Image Variants

| Variant | Size | Use Case | Command |
|---------|------|----------|---------|
| **Production** | ~500MB | Production deployment | `docker-compose up -d` |
| **Development** | ~600MB | Development with hot reload | `docker-compose --profile dev up -d` |
| **Alpine** | ~200MB | Resource-constrained environments | `docker-compose --profile alpine up -d` |

## 📊 Docker Compose Services

### Main Services

- **`libgen-bot`** - Production bot service
- **`libgen-bot-dev`** - Development service with hot reload
- **`libgen-bot-alpine`** - Alpine variant for smaller footprint
- **`log-aggregator`** - Optional log aggregation with Fluentd

### Service Profiles

```bash
# Production (default)
docker-compose up -d

# Development
docker-compose --profile dev up -d

# Alpine
docker-compose --profile alpine up -d

# With logging
docker-compose --profile logging up -d

# All profiles
docker-compose --profile dev --profile alpine --profile logging up -d
```

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TELEGRAM_BOT_TOKEN` | **Required** | Bot token from @BotFather |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LIBGEN_MAX_RESULTS` | `100` | Maximum search results (Docker optimized) |
| `BOT_BOOKS_PER_PAGE` | `3` | Books per page (Docker optimized) |
| `LIBGEN_SEARCH_TIMEOUT` | `20` | Search timeout in seconds |
| `BOT_DOWNLOAD_LINKS_TIMEOUT` | `8` | Download links timeout |
| `FEATURE_SEND_FILES` | `false` | Enable file sending feature |
| `FILE_MIN_SIZE_MB` | `0.1` | Minimum file size to send |
| `FILE_MAX_SIZE_MB` | `50` | Maximum file size to send |
| `HTTP_PROXY` | - | HTTP proxy URL (optional) |
| `HTTPS_PROXY` | - | HTTPS proxy URL (optional) |

### Resource Limits

```yaml
# Production service
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
    reservations:
      memory: 256M
      cpus: '0.25'

# Alpine service
deploy:
  resources:
    limits:
      memory: 256M
      cpus: '0.25'
    reservations:
      memory: 128M
      cpus: '0.1'
```

## 🔧 Management Commands

### Basic Operations

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f libgen-bot

# View logs with timestamps
docker-compose logs -f -t libgen-bot
```

### Development Commands

```bash
# Start development environment
docker-compose --profile dev up -d

# View development logs
docker-compose logs -f libgen-bot-dev

# Rebuild development image
docker-compose build libgen-bot-dev

# Execute commands in container
docker-compose exec libgen-bot-dev python simple_search.py "python programming"
```

### Maintenance Commands

```bash
# Update images
docker-compose pull
docker-compose up -d

# Rebuild images
docker-compose build --no-cache
docker-compose up -d

# Clean up unused images
docker system prune -a

# View resource usage
docker stats

# View container health
docker-compose ps
```

## 📁 Volume Mounts

### Persistent Data

```yaml
volumes:
  # Persist logs
  - ./logs:/app/logs
  
  # Mount .env file
  - ./.env:/app/.env:ro
```

### Log Files

- `./logs/bot.log` - General application logs
- `./logs/errors.log` - Error logs only

## 🔍 Monitoring and Health Checks

### Health Check

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import requests; requests.get('https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe', timeout=5)"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### Monitoring Commands

```bash
# Check service health
docker-compose ps

# View health check logs
docker inspect telegram-libgen-bot | jq '.[0].State.Health'

# Monitor resource usage
docker stats telegram-libgen-bot

# View real-time logs
docker-compose logs -f --tail=100 libgen-bot
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. Bot Token Issues

```bash
# Check if token is set
docker-compose exec libgen-bot env | grep TELEGRAM_BOT_TOKEN

# Validate token
docker-compose exec libgen-bot python -c "
import requests
import os
token = os.getenv('TELEGRAM_BOT_TOKEN')
response = requests.get(f'https://api.telegram.org/bot{token}/getMe')
print(response.json())
"
```

#### 2. Network Issues

```bash
# Test network connectivity
docker-compose exec libgen-bot ping -c 3 8.8.8.8

# Test LibGen access
docker-compose exec libgen-bot python -c "
import requests
response = requests.get('https://libgen.la', timeout=10)
print(f'LibGen status: {response.status_code}')
"
```

#### 3. Permission Issues

```bash
# Fix log directory permissions
sudo chown -R 1000:1000 logs/

# Recreate container with correct permissions
docker-compose down
docker-compose up -d
```

#### 4. Memory Issues

```bash
# Check memory usage
docker stats telegram-libgen-bot

# Increase memory limits in docker-compose.yml
# Or use Alpine variant for lower memory usage
docker-compose --profile alpine up -d
```

### Debug Mode

```bash
# Enable debug logging
echo "LOG_LEVEL=DEBUG" >> .env
docker-compose restart

# View debug logs
docker-compose logs -f libgen-bot
```

## 🔒 Security Considerations

### Container Security

- **Non-root user**: Bot runs as `botuser` (UID 1000)
- **Read-only mounts**: `.env` file mounted read-only
- **Resource limits**: Memory and CPU limits configured
- **Health checks**: Automatic health monitoring

### Network Security

- **Isolated network**: Services run in `libgen-network`
- **Proxy support**: Optional HTTP/HTTPS proxy configuration
- **TLS verification**: HTTPS requests with proper certificate validation

## 📈 Performance Optimization

### For Production

```yaml
# Optimize for production
environment:
  - LIBGEN_MAX_RESULTS=50
  - BOT_BOOKS_PER_PAGE=3
  - LIBGEN_SEARCH_TIMEOUT=15
  - BOT_DOWNLOAD_LINKS_TIMEOUT=5
```

### For Development

```yaml
# Optimize for development
environment:
  - LOG_LEVEL=DEBUG
  - LIBGEN_MAX_RESULTS=10
  - BOT_BOOKS_PER_PAGE=2
```

## 🚀 Deployment Examples

### Single Server Deployment

```bash
# Clone and setup
git clone <repository-url>
cd get_ketabha
cp docker.env .env

# Configure
nano .env  # Set TELEGRAM_BOT_TOKEN

# Deploy
docker-compose up -d

# Verify
docker-compose ps
docker-compose logs -f libgen-bot
```

### Multi-Environment Deployment

```bash
# Production
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Staging
docker-compose -f docker-compose.yml -f docker-compose.staging.yml up -d
```

### Cloud Deployment

```bash
# AWS ECS, Google Cloud Run, or Azure Container Instances
# Use the production image with appropriate environment variables
```

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [LibGen Project](https://libgen.is/)

## 🤝 Support

If you encounter issues:

1. Check the logs: `docker-compose logs -f libgen-bot`
2. Verify configuration: `docker-compose exec libgen-bot env`
3. Test connectivity: `docker-compose exec libgen-bot python simple_search.py "test"`
4. Check health status: `docker-compose ps`

---

**Happy Dockerizing! 🐳📚**
