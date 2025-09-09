# LibGen Dashboard

A modern, full-stack web application for searching and downloading books from LibGen mirrors with user authentication and a beautiful interface.

## 🚀 Features

### 🔐 **Authentication System**
- User registration and login with JWT tokens
- Secure password hashing with bcrypt
- Protected routes and API endpoints
- Session management with auto-refresh

### 📚 **Book Search**
- Search across multiple LibGen mirrors
- Real-time search with instant results
- Advanced filtering (format, language, year, size)
- Sort by relevance, title, author, year
- Download links with multiple mirror support
- Search history tracking

### 👤 **User Management**
- Personal dashboard with statistics
- Bookmark favorite books
- Search history management
- User profile customization
- Preferences and settings

### 🎨 **Modern UI/UX**
- Responsive design with Tailwind CSS
- Vue.js 3 with Composition API
- TypeScript for type safety
- Dark/light theme support
- Toast notifications
- Loading states and error handling

### ⚡ **Performance**
- FastAPI backend with async support
- Efficient database queries with SQLAlchemy
- Client-side caching with Pinia stores
- Lazy loading and code splitting
- Docker containerization

## 🏗️ Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - Database ORM
- **PostgreSQL** - Primary database
- **JWT** - Authentication tokens
- **Pydantic** - Data validation
- **Uvicorn** - ASGI server

### Frontend
- **Vue.js 3** - Progressive JavaScript framework
- **TypeScript** - Type-safe JavaScript
- **Vite** - Fast build tool and dev server
- **Pinia** - State management
- **Vue Router** - Client-side routing
- **Tailwind CSS** - Utility-first CSS
- **Heroicons** - Beautiful SVG icons

### DevOps
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration
- **Nginx** - Reverse proxy and static file serving
- **PostgreSQL** - Database
- **Redis** - Caching (optional)

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Node.js 18+ (for local development)
- Python 3.11+ (for local development)

### 1. Clone the Repository
```bash
git clone <repository-url>
cd libgen-dashboard
```

### 2. Environment Setup
```bash
# Backend environment
cp backend/env.example backend/.env
# Edit backend/.env with your settings

# Frontend environment (optional)
cp frontend/.env.example frontend/.env
# Edit frontend/.env if needed
```

### 3. Docker Development Setup
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### 4. Access the Application
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## 🛠️ Development

### Backend Development
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

### Database Management
```bash
# Create database migration
cd backend
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Downgrade migration
alembic downgrade -1
```

## 📁 Project Structure

```
libgen-dashboard/
├── backend/                 # FastAPI backend
│   ├── main.py             # Main application file
│   ├── auth.py             # Authentication utilities
│   ├── models.py           # Database models
│   ├── schemas.py          # Pydantic schemas
│   ├── database.py         # Database configuration
│   ├── libgen_service.py   # LibGen integration
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile          # Backend container
├── frontend/               # Vue.js frontend
│   ├── src/
│   │   ├── components/     # Reusable components
│   │   ├── views/          # Page components
│   │   ├── stores/         # Pinia stores
│   │   ├── services/       # API services
│   │   ├── types/          # TypeScript types
│   │   └── assets/         # Static assets
│   ├── package.json        # Node.js dependencies
│   └── Dockerfile          # Frontend container
├── docker-compose.yml      # Development orchestration
└── README.md              # This file
```

## 🔧 Configuration

### Backend Environment Variables
```env
# Database
DATABASE_URL=postgresql://user:password@localhost/libgen_dashboard

# JWT
JWT_SECRET_KEY=your-super-secret-jwt-key
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# LibGen Settings
LIBGEN_SEARCH_MIRRORS=https://libgen.la,https://libgen.li
LIBGEN_MAX_RESULTS=200
LIBGEN_SEARCH_TIMEOUT=30
```

### Frontend Environment Variables
```env
# API Configuration
VITE_API_BASE_URL=http://localhost:8000

# App Configuration
VITE_APP_TITLE=LibGen Dashboard
VITE_APP_DESCRIPTION=Search and download books
```

## 📡 API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login
- `GET /auth/me` - Get current user info

### Books
- `POST /search` - Search books
- `GET /book/{md5}/download-links` - Get download links
- `GET /books/popular` - Get popular books

### User Data
- `GET /bookmarks` - Get user bookmarks
- `POST /bookmarks` - Create bookmark
- `GET /search-history` - Get search history
- `GET /stats` - Get dashboard statistics

## 🐳 Production Deployment

### Using Docker Compose
```bash
# Production build
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# With SSL/Nginx
docker-compose --profile production up -d
```

### Environment Setup
1. Set up PostgreSQL database
2. Configure environment variables
3. Set up SSL certificates (for HTTPS)
4. Configure domain and DNS
5. Set up backup strategy

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### Frontend Tests
```bash
cd frontend
npm run test
```

## 📝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

- Create an issue for bug reports
- Check existing issues before creating new ones
- Provide detailed information for better support

## 🔄 Updates

The application integrates with your existing LibGen Telegram bot and shares the same search functionality. Updates to the LibGen mirrors and search logic will benefit both applications.

---

**Built with ❤️ for the academic community**
