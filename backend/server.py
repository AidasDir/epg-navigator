from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import httpx
import pytz

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# TVmaze API configuration
TVMAZE_API_KEY = os.environ.get('TVMAZE_API_KEY')
TVMAZE_BASE_URL = "https://api.tvmaze.com"

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Pydantic Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class ChannelProgram(BaseModel):
    id: str
    title: str
    episode: Optional[str] = None
    start_time: datetime
    end_time: datetime
    description: Optional[str] = None
    image: Optional[str] = None
    rating: Optional[str] = None
    channel_id: int
    genre: Optional[str] = None

class Channel(BaseModel):
    id: int
    number: str
    name: str
    logo: str
    programs: List[ChannelProgram] = []

# TVmaze API Service
class TVmazeService:
    def __init__(self):
        self.base_url = TVMAZE_BASE_URL
        self.api_key = TVMAZE_API_KEY
        self.session = None
    
    async def get_session(self):
        if self.session is None:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self.session = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                headers=headers,
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self.session
    
    async def close_session(self):
        if self.session:
            await self.session.aclose()
    
    async def get_schedule(self, country: str = "US", date: str = None):
        """Get TV schedule for a specific date and country"""
        session = await self.get_session()
        
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        
        try:
            response = await session.get(f"{self.base_url}/schedule", params={
                "country": country,
                "date": date
            })
            
            if response.status_code == 200:
                schedule_data = response.json()
                return schedule_data[:50]  # Limit to 50 entries
            else:
                logger.error(f"TVmaze API error: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching schedule: {e}")
            return []

# Initialize TVmaze service
tvmaze_service = TVmazeService()

# Channel data generation
def generate_channels_data() -> List[Channel]:
    """Generate realistic channel data with logos"""
    channels_data = [
        {"id": 1, "number": "2.1", "name": "FOX", "logo": "🦊"},
        {"id": 2, "number": "4.1", "name": "NBC", "logo": "🦚"},
        {"id": 3, "number": "7.1", "name": "ABC", "logo": "🔷"},
        {"id": 4, "number": "11.1", "name": "CBS", "logo": "👁️"},
        {"id": 5, "number": "13.1", "name": "PBS", "logo": "📚"},
        {"id": 6, "number": "24.1", "name": "ESPN", "logo": "⚽"},
        {"id": 7, "number": "32.1", "name": "CNN", "logo": "📺"},
        {"id": 8, "number": "35.1", "name": "TNT", "logo": "💥"},
        {"id": 9, "number": "39.1", "name": "TBS", "logo": "😄"},
        {"id": 10, "number": "42.1", "name": "USA", "logo": "🇺🇸"}
    ]
    
    return [Channel(**channel) for channel in channels_data]

def generate_sample_programs(channel_id: int) -> List[ChannelProgram]:
    """Generate sample programs for fallback"""
    programs = []
    base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    
    program_titles = [
        "Morning News", "Talk Show", "Game Show", "Drama Series", 
        "Reality TV", "Comedy Show", "Documentary", "Movie"
    ]
    
    for i in range(6):  # 6 hours of programming
        start_time = base_time + timedelta(hours=i)
        end_time = start_time + timedelta(hours=1)
        
        title = program_titles[i % len(program_titles)]
        if i == 0:  # Make first program special
            title = "The Jennifer Hudson Show"
        
        program = ChannelProgram(
            id=f"sample_{channel_id}_{i}",
            title=title,
            episode=f"S3 E{98 + i}" if i == 0 else f"S1 E{i + 1}",
            start_time=start_time,
            end_time=end_time,
            description=f"Description for {title}. Lorem ipsum dolor sit amet, consectetur adipiscing elit.",
            image=f"https://via.placeholder.com/120x80/1976D2/FFFFFF?text={title[0]}{title.split()[-1][0] if len(title.split()) > 1 else ''}",
            rating="R" if i == 0 else None,
            channel_id=channel_id,
            genre="Talk Show" if i == 0 else "General"
        )
        programs.append(program)
    
    return programs

# API Routes
@api_router.get("/")
async def root():
    return {"message": "TV EPG API"}

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

@api_router.get("/channels", response_model=List[Channel])
async def get_channels():
    """Get all channels with their current programming"""
    try:
        # Get today's schedule from TVmaze
        today = datetime.now().strftime("%Y-%m-%d")
        schedule_entries = await tvmaze_service.get_schedule(country="US", date=today)
        
        # Get base channel data
        channels = generate_channels_data()
        
        # For now, populate with sample data and add some real data if available
        for channel in channels:
            channel.programs = generate_sample_programs(channel.id)
            
            # Try to add some real shows if available
            if schedule_entries:
                real_program = schedule_entries[channel.id % len(schedule_entries)]
                if real_program and 'name' in real_program:
                    # Replace first program with real data
                    real_start = datetime.now().replace(minute=0, second=0, microsecond=0)
                    real_end = real_start + timedelta(hours=1)
                    
                    channel.programs[0] = ChannelProgram(
                        id=f"real_{real_program.get('id', channel.id)}",
                        title=real_program.get('name', 'Unknown Show'),
                        episode=f"S{real_program.get('season', 1)} E{real_program.get('number', 1)}",
                        start_time=real_start,
                        end_time=real_end,
                        description=real_program.get('summary', 'No description available').replace('<p>', '').replace('</p>', ''),
                        image=real_program.get('image', {}).get('medium') if real_program.get('image') else None,
                        rating=None,
                        channel_id=channel.id,
                        genre="Drama"
                    )
        
        return channels
        
    except Exception as e:
        logger.error(f"Error getting channels: {e}")
        # Return channels with sample data as fallback
        channels = generate_channels_data()
        for channel in channels:
            channel.programs = generate_sample_programs(channel.id)
        return channels

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    logger.info("TV EPG API starting up...")

@app.on_event("shutdown")
async def shutdown_event():
    await tvmaze_service.close_session()
    client.close()
    logger.info("TV EPG API shutting down...")
