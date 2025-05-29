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
        
        logger.info(f"Fetched {len(schedule_entries)} schedule entries from TVmaze")
        
        # Get base channel data
        channels = generate_channels_data()
        
        if schedule_entries and len(schedule_entries) > 0:
            # Process real TVmaze data
            channel_programs = await convert_schedule_to_programs(schedule_entries)
            
            # Populate programs for each channel
            for channel in channels:
                if channel.id in channel_programs and len(channel_programs[channel.id]) > 0:
                    # Sort programs by start time and limit to 6 hours
                    programs = sorted(channel_programs[channel.id], key=lambda p: p.start_time)
                    channel.programs = programs[:6]
                    logger.info(f"Channel {channel.name} assigned {len(channel.programs)} real programs")
                else:
                    # If no real data for this channel, assign some real shows from other channels
                    all_real_programs = []
                    for ch_programs in channel_programs.values():
                        all_real_programs.extend(ch_programs)
                    
                    if all_real_programs:
                        # Take programs and modify them for this channel
                        selected_programs = all_real_programs[:(6)]
                        channel.programs = []
                        for i, prog in enumerate(selected_programs):
                            # Create new program for this channel
                            new_program = ChannelProgram(
                                id=f"adapted_{channel.id}_{i}",
                                title=prog.title,
                                episode=prog.episode,
                                start_time=prog.start_time,
                                end_time=prog.end_time,
                                description=prog.description,
                                image=prog.image,
                                rating=prog.rating,
                                channel_id=channel.id,
                                genre=prog.genre
                            )
                            channel.programs.append(new_program)
                        logger.info(f"Channel {channel.name} assigned {len(channel.programs)} adapted real programs")
                    else:
                        # Last resort: generate sample programs with real-looking data
                        channel.programs = generate_realistic_programs(channel.id, channel.name)
                        logger.info(f"Channel {channel.name} assigned {len(channel.programs)} realistic sample programs")
        else:
            logger.warning("No real data from TVmaze, using realistic sample data")
            # Generate realistic sample data for each channel
            for channel in channels:
                channel.programs = generate_realistic_programs(channel.id, channel.name)
        
        return channels
        
    except Exception as e:
        logger.error(f"Error getting channels: {e}")
        # Return channels with realistic sample data as fallback
        channels = generate_channels_data()
        for channel in channels:
            channel.programs = generate_realistic_programs(channel.id, channel.name)
        return channels

async def convert_schedule_to_programs(schedule_entries) -> Dict[int, List[ChannelProgram]]:
    """Convert TVmaze schedule entries to channel programs"""
    channel_programs = {}
    
    # Network to channel mapping
    network_mapping = {
        "FOX": 1, "Fox": 1, "FOX Broadcasting Company": 1,
        "NBC": 2, "National Broadcasting Company": 2,
        "ABC": 3, "American Broadcasting Company": 3,
        "CBS": 4, "Columbia Broadcasting System": 4,
        "PBS": 5, "Public Broadcasting Service": 5,
        "ESPN": 6,
        "CNN": 7, "Cable News Network": 7,
        "TNT": 8, "Turner Network Television": 8,
        "TBS": 9, "Turner Broadcasting System": 9,
        "USA": 10, "USA Network": 10
    }
    
    for entry in schedule_entries:
        try:
            # Extract show information
            show_info = entry.get('show', {})
            network_info = show_info.get('network', {}) or show_info.get('webChannel', {})
            network_name = network_info.get('name', 'Unknown') if network_info else 'Unknown'
            
            # Determine channel based on network
            channel_id = None
            for network, ch_id in network_mapping.items():
                if network.lower() in network_name.lower():
                    channel_id = ch_id
                    break
            
            if not channel_id:
                # Distribute unknown networks across channels
                channel_id = (hash(network_name) % 10) + 1
            
            # Parse air time
            airstamp = entry.get('airstamp')
            if airstamp:
                try:
                    # Parse the airstamp (ISO format)
                    air_datetime = datetime.fromisoformat(airstamp.replace('Z', '+00:00'))
                    air_datetime = air_datetime.replace(tzinfo=pytz.UTC)
                    
                    # Convert to Eastern time (common for US TV)
                    eastern_tz = pytz.timezone('America/New_York')
                    local_time = air_datetime.astimezone(eastern_tz)
                    
                    # Calculate end time
                    runtime = entry.get('runtime') or show_info.get('runtime') or 60
                    end_time = local_time + timedelta(minutes=runtime)
                    
                    # Get image URL
                    image_info = entry.get('image') or show_info.get('image', {})
                    image_url = None
                    if image_info:
                        image_url = image_info.get('medium') or image_info.get('original')
                    
                    # Clean up summary
                    summary = entry.get('summary') or show_info.get('summary', '')
                    if summary:
                        # Remove HTML tags
                        import re
                        summary = re.sub(r'<[^>]+>', '', summary)
                        summary = summary.strip()
                    else:
                        summary = f"Watch {entry.get('name', 'this program')} on {network_name}."
                    
                    # Create program
                    program = ChannelProgram(
                        id=f"tvmaze_{entry.get('id', 'unknown')}",
                        title=entry.get('name', 'Unknown Show'),
                        episode=f"S{entry.get('season', 1)} E{entry.get('number', 1)}" if entry.get('season') and entry.get('number') else None,
                        start_time=local_time,
                        end_time=end_time,
                        description=summary,
                        image=image_url,
                        rating=None,  # TVmaze doesn't provide content ratings consistently
                        channel_id=channel_id,
                        genre=show_info.get('genres', ['General'])[0] if show_info.get('genres') else 'General'
                    )
                    
                    if channel_id not in channel_programs:
                        channel_programs[channel_id] = []
                    
                    channel_programs[channel_id].append(program)
                    
                except Exception as parse_error:
                    logger.error(f"Error parsing schedule entry {entry.get('id')}: {parse_error}")
                    continue
            
        except Exception as e:
            logger.error(f"Error processing schedule entry: {e}")
            continue
    
    logger.info(f"Mapped programs to {len(channel_programs)} channels")
    return channel_programs

def generate_realistic_programs(channel_id: int, channel_name: str) -> List[ChannelProgram]:
    """Generate realistic programs based on channel type"""
    programs = []
    base_time = datetime.now().replace(minute=0, second=0, microsecond=0)
    
    # Channel-specific programming
    channel_programming = {
        1: {  # FOX
            "programs": ["FOX & Friends", "The Five", "Tucker Carlson Tonight", "Hannity", "The Ingraham Angle", "Fox News @ Night"],
            "genres": ["News", "Talk", "News", "News", "News", "News"]
        },
        2: {  # NBC
            "programs": ["Today Show", "NBC Nightly News", "The Tonight Show", "Saturday Night Live", "Meet the Press", "Dateline NBC"],
            "genres": ["News", "News", "Talk", "Comedy", "News", "Documentary"]
        },
        3: {  # ABC
            "programs": ["Good Morning America", "World News Tonight", "The Bachelor", "Dancing with the Stars", "20/20", "Nightline"],
            "genres": ["News", "News", "Reality", "Reality", "Documentary", "News"]
        },
        4: {  # CBS
            "programs": ["CBS This Morning", "CBS Evening News", "60 Minutes", "NCIS", "The Big Bang Theory", "Late Show"],
            "genres": ["News", "News", "Documentary", "Drama", "Comedy", "Talk"]
        },
        5: {  # PBS
            "programs": ["PBS NewsHour", "Nature", "NOVA", "Masterpiece", "Antiques Roadshow", "American Experience"],
            "genres": ["News", "Documentary", "Documentary", "Drama", "Reality", "Documentary"]
        },
        6: {  # ESPN
            "programs": ["SportsCenter", "NBA Tonight", "NFL Live", "College GameDay", "Baseball Tonight", "ESPN Films"],
            "genres": ["Sports", "Sports", "Sports", "Sports", "Sports", "Sports"]
        },
        7: {  # CNN
            "programs": ["CNN Newsroom", "Anderson Cooper 360", "The Situation Room", "CNN Tonight", "New Day", "State of the Union"],
            "genres": ["News", "News", "News", "News", "News", "News"]
        },
        8: {  # TNT
            "programs": ["NBA on TNT", "Law & Order", "The Closer", "Major Crimes", "Castle", "Supernatural"],
            "genres": ["Sports", "Drama", "Drama", "Drama", "Drama", "Drama"]
        },
        9: {  # TBS
            "programs": ["Conan", "The Big Bang Theory", "Friends", "Family Guy", "American Dad", "Full Frontal"],
            "genres": ["Talk", "Comedy", "Comedy", "Comedy", "Comedy", "Comedy"]
        },
        10: {  # USA
            "programs": ["WWE Monday Night Raw", "Suits", "Mr. Robot", "Queen of the South", "The Sinner", "Temptation Island"],
            "genres": ["Sports", "Drama", "Drama", "Drama", "Drama", "Reality"]
        }
    }
    
    # Get programming for this channel or default
    channel_info = channel_programming.get(channel_id, {
        "programs": ["Morning Show", "Afternoon Movie", "Evening News", "Prime Time Drama", "Late Night Talk", "Overnight Movies"],
        "genres": ["Talk", "Movie", "News", "Drama", "Talk", "Movie"]
    })
    
    program_titles = channel_info["programs"]
    program_genres = channel_info["genres"]
    
    for i in range(6):  # 6 hours of programming
        start_time = base_time + timedelta(hours=i)
        end_time = start_time + timedelta(hours=1)
        
        title = program_titles[i % len(program_titles)]
        genre = program_genres[i % len(program_genres)]
        
        # Create more realistic descriptions
        descriptions = {
            "News": f"Stay informed with the latest breaking news, weather updates, and in-depth analysis on {title}.",
            "Talk": f"Join the conversation on {title} featuring celebrity interviews, current events, and entertainment.",
            "Sports": f"Catch all the action and highlights on {title} with expert commentary and analysis.",
            "Drama": f"Watch the latest episode of {title}, the critically acclaimed drama series.",
            "Comedy": f"Laugh along with {title}, featuring the best in comedy entertainment.",
            "Reality": f"Don't miss {title}, the reality show that's got everyone talking.",
            "Documentary": f"Explore fascinating stories and learn something new on {title}.",
            "Movie": f"Enjoy {title}, a blockbuster movie presentation."
        }
        
        description = descriptions.get(genre, f"Watch {title} on {channel_name}.")
        
        program = ChannelProgram(
            id=f"realistic_{channel_id}_{i}",
            title=title,
            episode=f"Season {2024 - channel_id} Episode {i + 1}" if genre in ["Drama", "Comedy"] else None,
            start_time=start_time,
            end_time=end_time,
            description=description,
            image=None,  # No fake images
            rating="TV-14" if genre in ["Drama", "News"] else "TV-PG",
            channel_id=channel_id,
            genre=genre
        )
        programs.append(program)
    
    return programs

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
