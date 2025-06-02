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
    logo_url: Optional[str] = None
    epg_channel_id: Optional[int] = None
    programs: List[ChannelProgram] = []

# EPG and Channel Management Service
class EPGService:
    def __init__(self):
        self.session = None
        # IPTV-org community channel sources
        self.channels_url = "https://iptv-org.github.io/api/channels.json"
        self.guides_url = "https://iptv-org.github.io/api/guides.json"
        # Alternative EPG sources
        self.epg_sources = [
            "https://xmltv.org/",  # XMLTV format
            "https://epg.streamlab.live/",  # Community EPG
        ]
    
    async def get_session(self):
        if self.session is None:
            self.session = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
        return self.session
    
    async def close_session(self):
        if self.session:
            await self.session.aclose()
    
    async def fetch_iptv_channels(self):
        """Fetch channel list from IPTV-org community"""
        session = await self.get_session()
        
        try:
            response = await session.get(self.channels_url)
            if response.status_code == 200:
                channels_data = response.json()
                logger.info(f"Fetched {len(channels_data)} channels from IPTV-org")
                return channels_data[:100]  # Limit to first 100 channels
            else:
                logger.error(f"IPTV-org API error: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Error fetching IPTV channels: {e}")
            return []
    
    async def generate_realistic_epg(self, channel_id: int, channel_name: str):
        """Generate realistic EPG data for a channel with varied timing"""
        programs = []
        
        # Start EPG 3 hours before current time to show recent programs
        now = datetime.now()
        base_time = now - timedelta(hours=3)
        base_time = base_time.replace(minute=0, second=0, microsecond=0)  # Round to hour
        
        # Channel-specific programming templates
        programming_templates = {
            "news": ["Breaking News", "Morning News", "Midday Update", "Evening Headlines", "Night Report", "Weather Update", "Live Coverage", "News Analysis"],
            "sports": ["Sports News", "SportsCenter", "Live Game", "Sports Analysis", "Highlights", "Press Conference", "Sports Talk", "Game Replay"],
            "entertainment": ["Comedy Show", "Movie Premiere", "Drama Series", "Reality Show", "Talk Show", "Comedy Special", "Late Night", "Variety Show"],
            "kids": ["Educational Show", "Morning Cartoons", "Animation Movie", "Kids Game Show", "Learning Time", "Bedtime Stories", "Adventure Time", "Family Movie"],
            "documentary": ["Wildlife Special", "Nature Documentary", "History Special", "Science Explorer", "Travel Guide", "Biography", "Investigation", "Planet Earth"],
            "lifestyle": ["Morning Show", "Cooking Show", "Home Improvement", "Fashion Week", "Health & Wellness", "DIY Projects", "Garden Life", "Design Tips"]
        }
        
        # Determine channel type based on name
        channel_type = "entertainment"  # default
        channel_lower = channel_name.lower()
        
        if any(word in channel_lower for word in ["news", "cnn", "bbc", "fox news", "msnbc"]):
            channel_type = "news"
        elif any(word in channel_lower for word in ["espn", "sports", "fs1", "nfl", "nba"]):
            channel_type = "sports"
        elif any(word in channel_lower for word in ["disney", "nick", "cartoon", "kids"]):
            channel_type = "kids"
        elif any(word in channel_lower for word in ["discovery", "history", "national geographic", "nature"]):
            channel_type = "documentary"
        elif any(word in channel_lower for word in ["food", "hgtv", "lifestyle", "cooking"]):
            channel_type = "lifestyle"
        
        program_titles = programming_templates.get(channel_type, programming_templates["entertainment"])
        
        # Generate programs with realistic start times and durations
        current_time = base_time
        program_index = 0
        
        # Generate 8 hours worth of programming (3 hours past + 5 hours future)
        end_time_limit = base_time + timedelta(hours=8)
        
        while current_time < end_time_limit and program_index < 16:  # Max 16 programs
            # Realistic duration patterns based on channel type
            if channel_type == "news":
                # News: 30 min, 60 min programs
                duration_options = [30, 60] 
                # News often starts at :00 or :30
                minute_starts = [0, 30]
            elif channel_type == "sports":
                # Sports: 30 min, 90 min, 180 min (games can be long)
                duration_options = [30, 90, 120, 180]
                minute_starts = [0, 30]
            elif channel_type == "kids":
                # Kids: 15 min, 30 min, 60 min
                duration_options = [15, 30, 60]
                minute_starts = [0, 15, 30, 45]
            elif channel_type == "entertainment":
                # Entertainment: 30 min, 60 min, 120 min (movies)
                duration_options = [30, 60, 90, 120]
                minute_starts = [0, 30]
            else:
                # Documentary/Lifestyle: 30 min, 60 min, 90 min
                duration_options = [30, 60, 90]
                minute_starts = [0, 30]
            
            # Choose duration for this program
            duration = duration_options[program_index % len(duration_options)]
            
            # Adjust start time to realistic TV scheduling
            if program_index == 0:
                # First program starts at the base time
                start_time = current_time
            else:
                # Subsequent programs start when previous ended, but adjust to realistic minute marks
                preferred_minute = minute_starts[program_index % len(minute_starts)]
                start_time = current_time.replace(minute=preferred_minute)
                
                # If the preferred minute has passed, move to next hour
                if start_time <= current_time:
                    start_time = start_time + timedelta(hours=1)
            
            end_time = start_time + timedelta(minutes=duration)
            
            # Don't exceed our 8-hour window
            if end_time > end_time_limit:
                end_time = end_time_limit
                duration = int((end_time - start_time).total_seconds() / 60)
                if duration < 15:  # Skip very short programs
                    break
            
            title = program_titles[program_index % len(program_titles)]
            
            # Create realistic descriptions
            descriptions = {
                "Breaking News": "Latest breaking news coverage with live reports from correspondents around the world.",
                "SportsCenter": "Comprehensive sports coverage featuring highlights, analysis, and breaking sports news.",
                "Movie Premiere": "Blockbuster movie premiere featuring action, drama, and entertainment for the whole family.",
                "Morning Cartoons": "Fun-filled animated adventures perfect for kids to start their day with laughter.",
                "Nature Documentary": "Explore the wonders of the natural world with stunning wildlife photography and expert narration.",
                "Cooking Show": "Learn culinary techniques and delicious recipes from professional chefs and cooking experts.",
                "Comedy Show": "Hilarious comedy entertainment featuring stand-up performances and comedic sketches.",
                "Live Game": "Live sports coverage with expert commentary and in-depth analysis of the game.",
                "Reality Show": "Unscripted reality television featuring real people in dramatic and entertaining situations."
            }
            
            description = descriptions.get(title, f"Watch {title} on {channel_name}. Quality programming with engaging content.")
            
            program = ChannelProgram(
                id=f"epg_{channel_id}_{program_index}",
                title=title,
                episode=f"Season {2024 + (program_index % 3)} Episode {program_index + 1}" if channel_type in ["entertainment", "kids"] else None,
                start_time=start_time,
                end_time=end_time,
                description=description,
                image=None,  # Will be populated with real images
                rating="TV-14" if channel_type in ["news", "documentary"] else "TV-PG",
                channel_id=channel_id,
                genre=channel_type.title()
            )
            programs.append(program)
            
            # Move to next program start time
            current_time = end_time
            program_index += 1
        
        return programs

# EPG.PW API Service
class EPGPWService:
    def __init__(self):
        self.base_url = "https://epg.pw/api"
        self.session = None
    
    async def get_session(self):
        if self.session is None:
            self.session = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
                headers={
                    'User-Agent': 'TV-EPG-App/1.0'
                }
            )
        return self.session
    
    async def close_session(self):
        if self.session:
            await self.session.aclose()
    
    async def get_epg_data(self, channel_id: int, date: str = None) -> str:
        """Get EPG XML data for a specific channel and date from epg.pw"""
        session = await self.get_session()
        
        if date is None:
            date = datetime.now().strftime("%Y%m%d")
        
        try:
            url = f"{self.base_url}/epg.xml"
            params = {
                "lang": "en",
                "date": date,
                "channel_id": channel_id
            }
            
            response = await session.get(url, params=params)
            
            if response.status_code == 200:
                xml_data = response.text
                logger.info(f"Fetched XML EPG data for channel {channel_id} on {date}")
                return xml_data
            else:
                logger.error(f"EPG.PW API error: {response.status_code} for channel {channel_id}")
                return ""
                
        except Exception as e:
            logger.error(f"Error fetching EPG XML data for channel {channel_id}: {e}")
            return ""
    
    async def convert_epg_to_programs(self, xml_data: str, channel_id: int) -> List[ChannelProgram]:
        """Convert EPG.PW XML data to ChannelProgram objects"""
        programs = []
        
        if not xml_data:
            return programs
        
        try:
            import xml.etree.ElementTree as ET
            
            # Parse XML
            root = ET.fromstring(xml_data)
            
            # Find all programme elements
            programmes = root.findall('programme')
            
            for programme in programmes:
                try:
                    # Get start and stop times
                    start_str = programme.get('start', '')  # "20250529000000 +0000"
                    stop_str = programme.get('stop', '')    # "20250529003000 +0000"
                    
                    # Get title and description
                    title_elem = programme.find('title')
                    desc_elem = programme.find('desc')
                    
                    title = title_elem.text if title_elem is not None else 'Unknown Program'
                    description = desc_elem.text if desc_elem is not None else 'No description available'
                    
                    if start_str and stop_str:
                        # Parse start time "20250529000000 +0000"
                        start_datetime_part = start_str.split(' ')[0]  # Get "20250529000000"
                        start_year = int(start_datetime_part[:4])
                        start_month = int(start_datetime_part[4:6])
                        start_day = int(start_datetime_part[6:8])
                        start_hour = int(start_datetime_part[8:10])
                        start_minute = int(start_datetime_part[10:12])
                        start_second = int(start_datetime_part[12:14])
                        
                        # Parse stop time "20250529003000 +0000"
                        stop_datetime_part = stop_str.split(' ')[0]  # Get "20250529003000"
                        stop_year = int(stop_datetime_part[:4])
                        stop_month = int(stop_datetime_part[4:6])
                        stop_day = int(stop_datetime_part[6:8])
                        stop_hour = int(stop_datetime_part[8:10])
                        stop_minute = int(stop_datetime_part[10:12])
                        stop_second = int(stop_datetime_part[12:14])
                        
                        # Create datetime objects in UTC then convert to Eastern
                        start_time_utc = datetime(start_year, start_month, start_day, start_hour, start_minute, start_second, tzinfo=pytz.UTC)
                        stop_time_utc = datetime(stop_year, stop_month, stop_day, stop_hour, stop_minute, stop_second, tzinfo=pytz.UTC)
                        
                        start_time = start_time_utc.astimezone(pytz.timezone('America/New_York'))
                        end_time = stop_time_utc.astimezone(pytz.timezone('America/New_York'))
                        
                        # Clean up title
                        if 'Live:' in title:
                            title = title.replace('Live: ', '')
                        
                        # Create program
                        program = ChannelProgram(
                            id=f"epgpw_{channel_id}_{start_str}",
                            title=title,
                            episode=None,
                            start_time=start_time,
                            end_time=end_time,
                            description=description,
                            image=None,  # EPG.PW doesn't provide images in XML
                            rating=None,
                            channel_id=channel_id,
                            genre='News' if 'news' in title.lower() else 'General'
                        )
                        programs.append(program)
                        
                except Exception as e:
                    logger.error(f"Error processing XML programme entry: {e}")
                    continue
            
            logger.info(f"Parsed {len(programs)} programs from XML for channel {channel_id}")
            
        except Exception as e:
            logger.error(f"Error parsing EPG XML data: {e}")
        
        return programs

# Initialize EPG.PW service
epg_pw_service = EPGPWService()

# Initialize EPG service
epg_service = EPGService()

# Channel data generation
def generate_channels_data() -> List[Channel]:
    """Generate realistic channel data with logos, epg.pw channel IDs, and categories"""
    channels_data = [
        # Broadcast Networks
        {"id": 1, "number": "2.1", "name": "FOX", "logo": "📺", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/Fox_Broadcasting_Company_Logo.svg/200px-Fox_Broadcasting_Company_Logo.svg.png", "epg_channel_id": 403858, "category": "General"},
        {"id": 2, "number": "4.1", "name": "NBC", "logo": "🦚", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/NBC_logo.svg/200px-NBC_logo.svg.png", "epg_channel_id": 403619, "category": "General"},
        {"id": 3, "number": "7.1", "name": "ABC", "logo": "🔵", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/ABC-2021-LOGO.svg/200px-ABC-2021-LOGO.svg.png", "epg_channel_id": 403805, "category": "General"},
        {"id": 4, "number": "11.1", "name": "CBS", "logo": "👁️", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/CBS_logo.svg/200px-CBS_logo.svg.png", "epg_channel_id": 403849, "category": "General"},
        {"id": 5, "number": "13.1", "name": "PBS", "logo": "📚", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/19/PBS_logo.svg/200px-PBS_logo.svg.png", "epg_channel_id": 403469, "category": "General"},
        
        # Sports Channels
        {"id": 6, "number": "24.1", "name": "ESPN", "logo": "⚽", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/ESPN_wordmark.svg/200px-ESPN_wordmark.svg.png", "epg_channel_id": 403793, "category": "Sports"},
        {"id": 13, "number": "52.1", "name": "ESPN2", "logo": "⚽", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/ESPN_wordmark.svg/200px-ESPN_wordmark.svg.png", "epg_channel_id": 403821, "category": "Sports"},
        {"id": 21, "number": "84.1", "name": "FS1", "logo": "🏈", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Fox_Sports_1_logo.svg/200px-Fox_Sports_1_logo.svg.png", "epg_channel_id": 403574, "category": "Sports"},
        {"id": 22, "number": "88.1", "name": "NFL Network", "logo": "🏈", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/NFL_Network_logo.svg/200px-NFL_Network_logo.svg.png", "epg_channel_id": 403577, "category": "Sports"},
        
        # News Channels
        {"id": 7, "number": "32.1", "name": "CNN", "logo": "📰", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/b/b1/CNN.svg/200px-CNN.svg.png", "epg_channel_id": 403819, "category": "News"},
        {"id": 11, "number": "45.1", "name": "Fox News", "logo": "📰", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/67/Fox_Broadcasting_Company_Logo.svg/200px-Fox_Broadcasting_Company_Logo.svg.png", "epg_channel_id": 403903, "category": "News"},
        {"id": 12, "number": "48.1", "name": "MSNBC", "logo": "📰", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3f/NBC_logo.svg/200px-NBC_logo.svg.png", "epg_channel_id": 403470, "category": "News"},
        
        # Kids Channels
        {"id": 14, "number": "56.1", "name": "Disney Channel", "logo": "🏰", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/Disney_Channel_logo.svg/200px-Disney_Channel_logo.svg.png", "epg_channel_id": 403788, "category": "Kids"},
        {"id": 15, "number": "60.1", "name": "Nickelodeon", "logo": "🧽", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7a/Nickelodeon_2009_logo.svg/200px-Nickelodeon_2009_logo.svg.png", "epg_channel_id": 403620, "category": "Kids"},
        {"id": 16, "number": "64.1", "name": "Cartoon Network", "logo": "🎨", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/80/Cartoon_Network_2010_logo.svg/200px-Cartoon_Network_2010_logo.svg.png", "epg_channel_id": 403461, "category": "Kids"},
        {"id": 23, "number": "92.1", "name": "Disney Junior", "logo": "🧸", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/da/Disney_Channel_logo.svg/200px-Disney_Channel_logo.svg.png", "epg_channel_id": 403512, "category": "Kids"},
        
        # Entertainment/TV Shows
        {"id": 8, "number": "35.1", "name": "TNT", "logo": "💥", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/TNT_Logo_2016.svg/200px-TNT_Logo_2016.svg.png", "epg_channel_id": 403615, "category": "TV Shows"},
        {"id": 9, "number": "39.1", "name": "TBS", "logo": "😄", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/de/TBS_logo_2016.svg/200px-TBS_logo_2016.svg.png", "epg_channel_id": 403640, "category": "TV Shows"},
        {"id": 10, "number": "42.1", "name": "USA", "logo": "🇺🇸", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d7/USA_Network_logo_%282016%29.svg/200px-USA_Network_logo_%282016%29.svg.png", "epg_channel_id": 403626, "category": "TV Shows"},
        {"id": 24, "number": "96.1", "name": "FX", "logo": "🎭", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4d/FX_International_logo.svg/200px-FX_International_logo.svg.png", "epg_channel_id": 403550, "category": "TV Shows"},
        {"id": 25, "number": "100.1", "name": "AMC", "logo": "🎬", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/16/AMC_logo_2016.svg/200px-AMC_logo_2016.svg.png", "epg_channel_id": 403558, "category": "TV Shows"},
        
        # Movies Channels
        {"id": 26, "number": "104.1", "name": "HBO", "logo": "🎭", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/de/HBO_logo.svg/200px-HBO_logo.svg.png", "epg_channel_id": 403800, "category": "Movies"},
        {"id": 27, "number": "108.1", "name": "Showtime", "logo": "🎬", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/22/Showtime.svg/200px-Showtime.svg.png", "epg_channel_id": 403801, "category": "Movies"},
        {"id": 28, "number": "112.1", "name": "Starz", "logo": "⭐", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/11/Starz_2016.svg/200px-Starz_2016.svg.png", "epg_channel_id": 403802, "category": "Movies"},
        
        # Documentary/Educational
        {"id": 17, "number": "68.1", "name": "Discovery", "logo": "🔬", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/27/Discovery_Channel_logo.svg/200px-Discovery_Channel_logo.svg.png", "epg_channel_id": 403564, "category": "Documentary"},
        {"id": 18, "number": "72.1", "name": "History", "logo": "🏛️", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/01/History_%282021%29.svg/200px-History_%282021%29.svg.png", "epg_channel_id": 403795, "category": "Documentary"},
        {"id": 19, "number": "76.1", "name": "National Geographic", "logo": "🌍", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/13/National_Geographic_Channel.svg/200px-National_Geographic_Channel.svg.png", "epg_channel_id": 403578, "category": "Documentary"},
        
        # Lifestyle
        {"id": 20, "number": "80.1", "name": "Food Network", "logo": "🍳", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d9/Food_Network_logo.svg/200px-Food_Network_logo.svg.png", "epg_channel_id": 403509, "category": "Lifestyle"},
        {"id": 29, "number": "116.1", "name": "HGTV", "logo": "🏠", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c5/HGTV_US_Logo_2015.svg/200px-HGTV_US_Logo_2015.svg.png", "epg_channel_id": 403518, "category": "Lifestyle"},
        {"id": 30, "number": "120.1", "name": "Bravo", "logo": "💃", "logo_url": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/64/Bravo_logo.svg/200px-Bravo_logo.svg.png", "epg_channel_id": 403555, "category": "Lifestyle"}
    ]
    
    return [Channel(**channel) for channel in channels_data]

# In-memory storage for user preferences (in production, use database)
user_favorites = set()  # Set of channel IDs
user_recent = []  # List of channel IDs in order of recent access

def get_recent_channels():
    """Get recently viewed channels (last 8 channels)"""
    all_channels = generate_channels_data()
    channel_dict = {ch.id: ch for ch in all_channels}
    
    recent_channels = []
    for channel_id in user_recent[-8:]:  # Last 8 recent channels
        if channel_id in channel_dict:
            recent_channels.append(channel_dict[channel_id])
    
    return recent_channels

def get_favorite_channels():
    """Get user's favorite channels"""
    all_channels = generate_channels_data()
    return [ch for ch in all_channels if ch.id in user_favorites]

def add_to_recent(channel_id: int):
    """Add channel to recent list"""
    global user_recent
    # Remove if already exists
    if channel_id in user_recent:
        user_recent.remove(channel_id)
    # Add to beginning
    user_recent.insert(0, channel_id)
    # Keep only last 20 entries
    user_recent = user_recent[:20]

def toggle_favorite(channel_id: int) -> bool:
    """Toggle channel favorite status. Returns True if now favorite, False if removed"""
    global user_favorites
    if channel_id in user_favorites:
        user_favorites.remove(channel_id)
        return False
    else:
        user_favorites.add(channel_id)
        return True

def get_channels_by_category(category: str):
    """Get channels filtered by category"""
    all_channels = generate_channels_data()
    
    if category == "Sports":
        sports_channels = [ch for ch in all_channels if ch.name in ["ESPN", "ESPN2", "FS1", "NFL Network"]]
        return sports_channels
    elif category == "Kids":
        kids_channels = [ch for ch in all_channels if ch.name in ["Disney Channel", "Nickelodeon", "Cartoon Network"]]
        return kids_channels
    elif category == "Movies":
        movie_channels = [ch for ch in all_channels if ch.name in ["HBO", "Showtime", "Starz", "AMC", "TNT", "TBS"]]
        return movie_channels
    elif category == "TV Shows":
        tv_channels = [ch for ch in all_channels if ch.name in ["FOX", "NBC", "ABC", "CBS", "USA", "FX", "Bravo"]]
        return tv_channels
    else:
        return all_channels

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
    """Get all channels with their current programming from EPG.PW"""
    try:
        # Get today's date for EPG data
        today = datetime.now().strftime("%Y%m%d")
        
        # Get base channel data with EPG channel IDs
        channels = generate_channels_data()
        
        # Fetch real EPG data for each channel
        for channel in channels:
            if channel.epg_channel_id:
                logger.info(f"Fetching EPG data for {channel.name} (ID: {channel.epg_channel_id})")
                
                # Get EPG data from epg.pw (XML format)
                xml_data = await epg_pw_service.get_epg_data(channel.epg_channel_id, today)
                
                if xml_data:
                    # Convert EPG XML data to programs
                    programs = await epg_pw_service.convert_epg_to_programs(xml_data, channel.id)
                    
                    if programs:
                        # Sort programs by start time and limit to next 8 hours
                        now = datetime.now(pytz.timezone('America/New_York'))
                        future_programs = [p for p in programs if p.end_time > now]
                        sorted_programs = sorted(future_programs, key=lambda p: p.start_time)
                        channel.programs = sorted_programs[:12]  # Next 12 programs (about 8-12 hours)
                        
                        logger.info(f"Loaded {len(channel.programs)} real programs for {channel.name}")
                    else:
                        # Fallback to realistic sample data
                        channel.programs = generate_realistic_programs(channel.id, channel.name)
                        logger.info(f"Using fallback data for {channel.name}")
                else:
                    # Fallback to realistic sample data
                    channel.programs = generate_realistic_programs(channel.id, channel.name)
                    logger.info(f"No EPG data found, using fallback for {channel.name}")
            else:
                # No EPG channel ID, use sample data
                channel.programs = generate_realistic_programs(channel.id, channel.name)
                logger.info(f"No EPG channel ID for {channel.name}, using sample data")
        
        return channels
        
    except Exception as e:
        logger.error(f"Error getting channels with EPG data: {e}")
        # Return channels with realistic sample data as fallback
        channels = generate_channels_data()
        for channel in channels:
            channel.programs = generate_realistic_programs(channel.id, channel.name)
        return channels

@api_router.post("/channels/{channel_id}/favorite")
async def toggle_channel_favorite(channel_id: int):
    """Toggle favorite status for a channel"""
    try:
        is_favorite = toggle_favorite(channel_id)
        return {
            "channel_id": channel_id,
            "is_favorite": is_favorite,
            "message": f"Channel {'added to' if is_favorite else 'removed from'} favorites"
        }
    except Exception as e:
        logger.error(f"Error toggling favorite for channel {channel_id}: {e}")
        raise HTTPException(status_code=500, detail="Error updating favorites")

@api_router.post("/channels/{channel_id}/recent")
async def mark_channel_recent(channel_id: int):
    """Mark a channel as recently viewed"""
    try:
        add_to_recent(channel_id)
        return {
            "channel_id": channel_id,
            "message": "Channel added to recent list"
        }
    except Exception as e:
        logger.error(f"Error adding channel {channel_id} to recent: {e}")
        raise HTTPException(status_code=500, detail="Error updating recent channels")

@api_router.get("/favorites")
async def get_user_favorites():
    """Get list of user's favorite channel IDs"""
    return {
        "favorite_channels": list(user_favorites),
        "count": len(user_favorites)
    }

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
    await epg_pw_service.close_session()
    client.close()
    logger.info("TV EPG API shutting down...")