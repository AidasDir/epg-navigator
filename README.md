# 📺 TV Electronic Program Guide (EPG) Application

A modern, real-time TV Electronic Program Guide interface that replicates professional broadcast EPG systems with authentic TV programming data from EPG.PW.

![TV EPG Interface](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![React](https://img.shields.io/badge/React-18.x-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green)
![EPG.PW](https://img.shields.io/badge/EPG%20Data-EPG.PW%20API-orange)

## 🌟 Features

### 📺 **Authentic TV Experience**
- **30+ Real TV Channels** with authentic EPG data from EPG.PW
- **Category-Based Filtering**: Sports, Kids, Movies, TV Shows, News, Documentary, Lifestyle
- **Real-time Programming**: Live TV schedules with accurate start/end times
- **D-pad Navigation**: Full keyboard control simulating TV remote experience

### ⏰ **Advanced Timeline System**
- **Live Clock**: Real-time clock with seconds precision
- **NOW Timeline**: Red vertical line showing current time position
- **8-Hour Window**: 3 hours past + 5 hours future programming
- **Variable Durations**: 15-minute cartoons to 3-hour movies

### 🎮 **Smart Features**
- **Favorites System**: Mark and track favorite channels
- **Recent Tracking**: Automatically tracks recently viewed channels
- **Live Indicators**: Shows currently airing programs
- **Dynamic Content**: Program details update in real-time

## 🚀 Quick Start

### Prerequisites

- **Node.js** 16+ and **yarn**
- **Python** 3.8+ with **pip**
- **MongoDB** (for user preferences)
- **Supervisor** (for process management)

### Installation

1. **Clone and Setup**
```bash
git clone <repository-url>
cd tv-epg-app
```

2. **Install Dependencies**
```bash
# Frontend dependencies
cd frontend
yarn install

# Backend dependencies
cd ../
pip install -r requirements.txt
```

3. **Environment Configuration**
```bash
# Backend environment
echo 'MONGO_URL="mongodb://localhost:27017"' > backend/.env
echo 'DB_NAME="tv_epg_db"' >> backend/.env
echo 'ENVIRONMENT=development' >> backend/.env

# Frontend environment (already configured)
# REACT_APP_BACKEND_URL=https://your-domain.com
```

### 🏃‍♂️ Running the Application

#### **Method 1: Using Supervisor (Recommended)**
```bash
# Start all services
sudo supervisorctl start all

# Check status
sudo supervisorctl status

# View logs
sudo supervisorctl tail -f backend stdout
sudo supervisorctl tail -f frontend stdout
```

#### **Method 2: Manual Development**
```bash
# Terminal 1: Start MongoDB
mongod

# Terminal 2: Start Backend
cd backend
python -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload

# Terminal 3: Start Frontend
cd frontend
yarn start
```

### 📱 Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🎮 Usage Instructions

### **Navigation Controls**

#### **Keyboard Navigation (TV Remote Simulation)**
- **Arrow Keys**: Navigate through the interface
- **Left/Right**: Switch between sidebar and program grid
- **Up/Down**: Move within sections
- **Enter**: Select categories or mark as recent
- **F Key**: Toggle favorite status for channels

#### **Mouse/Touch Navigation**
- **Click Sidebar Categories**: Switch between All, Sports, Kids, Movies, etc.
- **Click Program Blocks**: Select programs and update detail panel
- **Click Heart Icons**: Add/remove channels from favorites

### **Categories**

#### 🏈 **Sports** (4 channels)
- ESPN, ESPN2, FS1, NFL Network
- Live games, sports news, analysis

#### 👶 **Kids** (4 channels)  
- Disney Channel, Nickelodeon, Cartoon Network, Disney Junior
- Cartoons, educational shows, family content

#### 🎬 **Movies** (3 channels)
- HBO, Showtime, Starz
- Premium movies and original series

#### 📺 **TV Shows** (5 channels)
- TNT, TBS, USA, FX, AMC
- Drama series, comedies, entertainment

#### 📰 **News** (3 channels)
- CNN, Fox News, MSNBC
- 24-hour news coverage

## 🛠️ API Reference

### **Endpoints**

#### **Get Channels**
```bash
GET /api/channels
GET /api/channels?category=Sports
GET /api/channels?category=Kids
```

#### **Favorites Management**
```bash
GET /api/favorites
POST /api/favorites
DELETE /api/favorites/{channel_id}
```

#### **Recent Channels**
```bash
GET /api/recent
POST /api/recent
```

### **EPG.PW Integration**

The application uses EPG.PW XML API for real TV data:
```
https://epg.pw/api/epg.xml?lang=en&date=YYYYMMDD&channel_id=CHANNEL_ID
```

**Channel ID Examples:**
- Fox News: 403903
- ESPN: 403793
- Disney Channel: 403788
- Cartoon Network: 403461

## 🔧 Configuration

### **Backend Configuration**

**Environment Variables** (`backend/.env`):
```env
MONGO_URL="mongodb://localhost:27017"
DB_NAME="tv_epg_db"
ENVIRONMENT=development
```

**Channel Configuration**:
- Located in `backend/server.py` → `generate_channels_data()`
- Each channel has: `epg_channel_id`, `category`, `logo_url`
- Add new channels by extending the array

### **Frontend Configuration**

**Environment Variables** (`frontend/.env`):
```env
REACT_APP_BACKEND_URL=https://your-backend-domain.com
```

**Features Configuration**:
- Timeline settings in `calculateProgramPosition()` and `calculateProgramWidth()`
- Category mappings in sidebar items array
- Visual theme in `App.css`

## 🏗️ Architecture

### **Technology Stack**

#### **Frontend**
- **React 18** with Hooks and Context
- **CSS Grid** for EPG layout
- **Responsive Design** for multiple screen sizes
- **Real-time Updates** with useEffect hooks

#### **Backend**
- **FastAPI** with async/await
- **MongoDB** with Motor (async driver)
- **HTTP Client** for EPG.PW integration
- **Pydantic** for data validation

#### **External Services**
- **EPG.PW** for real TV program data
- **Wikipedia** for channel logos
- **Supervisor** for process management

### **Project Structure**
```
tv-epg-app/
├── frontend/
│   ├── src/
│   │   ├── App.js          # Main React component
│   │   ├── App.css         # EPG styling
│   │   └── index.js        # React entry point
│   ├── package.json        # Dependencies
│   └── .env               # Frontend config
├── backend/
│   ├── server.py          # FastAPI application
│   ├── requirements.txt   # Python dependencies
│   └── .env              # Backend config
└── README.md             # This file
```

## 🐛 Troubleshooting

### **Common Issues**

#### **1. "Cannot connect to backend"**
```bash
# Check backend status
sudo supervisorctl status backend

# Restart backend
sudo supervisorctl restart backend

# Check logs
sudo supervisorctl tail backend stderr
```

#### **2. "No EPG data loading"**
```bash
# Test EPG.PW API directly
curl "https://epg.pw/api/epg.xml?lang=en&date=20250529&channel_id=403903"

# Check backend logs for EPG errors
sudo supervisorctl tail backend stdout
```

#### **3. "Categories not filtering"**
```bash
# Test category API
curl "http://localhost:8000/api/channels?category=Sports"

# Verify MongoDB connection
mongosh tv_epg_db
```

#### **4. "Timeline position incorrect"**
- Verify system time and timezone
- Check `getCurrentTimePosition()` function
- Ensure EPG data has correct timestamps

### **Performance Optimization**

#### **Frontend**
- Use React.memo for program blocks
- Implement virtual scrolling for large channel lists
- Debounce navigation events

#### **Backend**
- Cache EPG.PW responses
- Implement connection pooling
- Add response compression

## 🚀 Deployment

### **Production Setup**

1. **Environment Configuration**
```bash
# Set production environment
echo 'ENVIRONMENT=production' >> backend/.env

# Configure production MongoDB
echo 'MONGO_URL="mongodb://production-host:27017"' >> backend/.env
```

2. **Build Frontend**
```bash
cd frontend
yarn build
```

3. **Process Management**
```bash
# Production supervisor config
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
```

## 📈 Monitoring

### **Health Checks**
```bash
# Backend health
curl http://localhost:8000/api/

# Frontend health  
curl http://localhost:3000

# MongoDB health
mongosh --eval "db.adminCommand('ping')"
```

### **Logs**
```bash
# All service logs
sudo supervisorctl tail -f all

# Specific service logs
sudo supervisorctl tail -f backend stdout
sudo supervisorctl tail -f frontend stdout
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **EPG.PW** for providing free TV program data
- **Wikipedia** for channel logos and brand assets
- **React** and **FastAPI** communities for excellent frameworks

---

**📺 Enjoy your authentic TV EPG experience!** ✨
