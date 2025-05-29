import React, { useState, useEffect, useCallback } from 'react';
import './App.css';

const App = () => {
  // Navigation state
  const [focusedSection, setFocusedSection] = useState('sidebar'); // 'sidebar', 'grid'
  const [sidebarFocus, setSidebarFocus] = useState(0);
  const [gridFocus, setGridFocus] = useState({ channel: 0, program: 0 });
  
  // Data state
  const [channels, setChannels] = useState([]);
  const [currentTime, setCurrentTime] = useState(new Date());
  const [selectedProgram, setSelectedProgram] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const sidebarItems = [
    'All', 'Recent', 'Favorites ❤️', 'Sports', 'Kids', 'Movies', 'TV Shows'
  ];

  const iconBarIcons = ['🔍', '🏠', '📺', '▶️', '⚙️', '💾', '🔄'];

  // Live clock update
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // Fetch channels data from backend
  const fetchChannels = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      
      const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/channels`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const channelsData = await response.json();
      
      // Convert datetime strings to Date objects
      const processedChannels = channelsData.map(channel => ({
        ...channel,
        programs: channel.programs.map(program => ({
          ...program,
          startTime: new Date(program.start_time),
          endTime: new Date(program.end_time)
        }))
      }));
      
      setChannels(processedChannels);
      
      // Set initial selected program
      if (processedChannels.length > 0 && processedChannels[0].programs.length > 0) {
        setSelectedProgram(processedChannels[0].programs[0]);
      }
      
    } catch (error) {
      console.error('Error fetching channels:', error);
      setError('Failed to load TV guide data');
      
      // Fallback to mock data
      const fallbackChannels = generateFallbackChannels();
      setChannels(fallbackChannels);
      if (fallbackChannels.length > 0) {
        setSelectedProgram(fallbackChannels[0].programs[0]);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  // Generate fallback data in case API fails
  const generateFallbackChannels = () => {
    const fallbackData = [
      { id: 1, number: '2.1', name: 'FOX', logo: '🦊' },
      { id: 2, number: '4.1', name: 'NBC', logo: '🦚' },
      { id: 3, number: '7.1', name: 'ABC', logo: '🔷' },
      { id: 4, number: '11.1', name: 'CBS', logo: '👁️' },
      { id: 5, number: '13.1', name: 'PBS', logo: '📚' },
      { id: 6, number: '24.1', name: 'ESPN', logo: '⚽' },
      { id: 7, number: '32.1', name: 'CNN', logo: '📺' }
    ];

    return fallbackData.map(channel => ({
      ...channel,
      programs: generateFallbackPrograms(channel.id)
    }));
  };

  const generateFallbackPrograms = (channelId) => {
    const programs = [];
    const baseTime = new Date();
    baseTime.setMinutes(0, 0, 0);

    const titles = ['Morning News', 'Talk Show', 'Game Show', 'Drama Series', 'Reality TV', 'Comedy Show'];

    for (let i = 0; i < 6; i++) {
      const startTime = new Date(baseTime.getTime() + (i * 60 * 60 * 1000));
      const endTime = new Date(startTime.getTime() + (60 * 60 * 1000));

      programs.push({
        id: `fallback-${channelId}-${i}`,
        title: i === 0 ? 'The Jennifer Hudson Show' : titles[i % titles.length],
        episode: i === 0 ? 'S3 E98' : `S1 E${i + 1}`,
        startTime,
        endTime,
        description: i === 0 ? 
          'Award-winning daytime talk show featuring celebrity interviews, musical performances, and inspiring human interest stories.' :
          `Description for ${titles[i % titles.length]}. Lorem ipsum dolor sit amet.`,
        image: i === 0 ? 
          'https://via.placeholder.com/120x80/1976D2/FFFFFF?text=JH' : 
          `https://via.placeholder.com/120x80/333333/FFFFFF?text=P${i + 1}`,
        rating: i === 0 ? 'R' : null
      });
    }

    return programs;
  };

  useEffect(() => {
    fetchChannels();
  }, [fetchChannels]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyPress = (e) => {
      switch (e.key) {
        case 'ArrowUp':
          e.preventDefault();
          if (focusedSection === 'sidebar') {
            setSidebarFocus(prev => Math.max(0, prev - 1));
          } else if (focusedSection === 'grid') {
            setGridFocus(prev => ({
              ...prev,
              channel: Math.max(0, prev.channel - 1)
            }));
            updateSelectedProgram(Math.max(0, gridFocus.channel - 1), gridFocus.program);
          }
          break;
          
        case 'ArrowDown':
          e.preventDefault();
          if (focusedSection === 'sidebar') {
            setSidebarFocus(prev => Math.min(sidebarItems.length - 1, prev + 1));
          } else if (focusedSection === 'grid') {
            setGridFocus(prev => ({
              ...prev,
              channel: Math.min(channels.length - 1, prev.channel + 1)
            }));
            updateSelectedProgram(Math.min(channels.length - 1, gridFocus.channel + 1), gridFocus.program);
          }
          break;
          
        case 'ArrowLeft':
          e.preventDefault();
          if (focusedSection === 'grid') {
            setGridFocus(prev => ({
              ...prev,
              program: Math.max(0, prev.program - 1)
            }));
            updateSelectedProgram(gridFocus.channel, Math.max(0, gridFocus.program - 1));
          } else {
            setFocusedSection('sidebar');
          }
          break;
          
        case 'ArrowRight':
          e.preventDefault();
          if (focusedSection === 'sidebar') {
            setFocusedSection('grid');
          } else if (focusedSection === 'grid') {
            const maxPrograms = channels[gridFocus.channel]?.programs.length || 0;
            setGridFocus(prev => ({
              ...prev,
              program: Math.min(maxPrograms - 1, prev.program + 1)
            }));
            updateSelectedProgram(gridFocus.channel, Math.min(maxPrograms - 1, gridFocus.program + 1));
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [focusedSection, sidebarFocus, gridFocus, channels]);

  const updateSelectedProgram = (channelIndex, programIndex) => {
    if (channels[channelIndex] && channels[channelIndex].programs[programIndex]) {
      setSelectedProgram(channels[channelIndex].programs[programIndex]);
    }
  };

  const formatTime = (date) => {
    if (!date || !(date instanceof Date)) return '--:--:--';
    return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit', second: '2-digit' });
  };

  const formatTimeSimple = (date) => {
    if (!date || !(date instanceof Date)) return '--:--';
    return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  };

  const getTimeHeaders = () => {
    const headers = ['Today'];
    const baseTime = new Date();
    baseTime.setMinutes(0, 0, 0);
    
    for (let i = 0; i < 6; i++) {
      const time = new Date(baseTime.getTime() + (i * 60 * 60 * 1000));
      headers.push(formatTimeSimple(time));
    }
    return headers;
  };

  const getCurrentTimePosition = () => {
    const now = new Date();
    const baseTime = new Date();
    baseTime.setMinutes(0, 0, 0);
    
    const minutesSinceHour = now.getMinutes();
    const percentage = (minutesSinceHour / 60) * 100;
    
    return percentage;
  };

  const isCurrentlyAiring = (program) => {
    const now = new Date();
    return program.startTime <= now && program.endTime > now;
  };

  const getCurrentChannel = () => {
    return channels[gridFocus.channel] || channels[0];
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-text">Loading TV Guide...</div>
        <div className="loading-subtitle">Fetching real TV data from TVmaze</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-screen">
        <div className="error-text">⚠️ {error}</div>
        <div className="error-subtitle">Using sample data as fallback</div>
        <button onClick={fetchChannels} className="retry-button">
          🔄 Retry
        </button>
      </div>
    );
  }

  return (
    <div className="epg-container">
      {/* Top Left Time and Rating */}
      <div className="top-indicators">
        <div className="current-time">{formatTime(currentTime)}</div>
        <div className="rating-indicator">
          <span className="rating-badge">R</span>
        </div>
      </div>

      {/* Left Icon Bar */}
      <div className="icon-bar">
        {iconBarIcons.map((icon, index) => (
          <div key={index} className="icon-item">
            {icon}
          </div>
        ))}
      </div>

      {/* Left Sidebar */}
      <div className="sidebar">
        <div className="sidebar-categories">
          {sidebarItems.map((item, index) => (
            <div
              key={index}
              className={`sidebar-item ${
                focusedSection === 'sidebar' && sidebarFocus === index ? 'focused' : ''
              }`}
            >
              {item}
            </div>
          ))}
        </div>
        <div className="sidebar-divider"></div>
        <div className="sidebar-options">
          <div className="sidebar-item">Sort by A-Z</div>
          <div className="sidebar-item">Jump To Day</div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="main-content">
        {/* Top Program Detail Panel */}
        <div className="program-detail-panel">
          {selectedProgram && (
            <>
              <div className="program-thumbnail">
                <img 
                  src={selectedProgram.image || `https://images.unsplash.com/photo-1574375927938-d5a98e8ffe85?w=120&h=80&fit=crop&crop=center`} 
                  alt={selectedProgram.title}
                  onError={(e) => {
                    e.target.src = `https://images.unsplash.com/photo-1574375927938-d5a98e8ffe85?w=120&h=80&fit=crop&crop=center`;
                  }}
                />
                {isCurrentlyAiring(selectedProgram) && (
                  <div className="live-indicator">
                    <span className="live-dot"></span>
                    LIVE
                  </div>
                )}
              </div>
              <div className="program-details">
                <div className="channel-info-header">
                  <img 
                    src={getCurrentChannel().logo_url} 
                    alt={getCurrentChannel().name}
                    className="channel-logo-large"
                    onError={(e) => {
                      e.target.style.display = 'none';
                    }}
                  />
                  <span className="channel-name-large">{getCurrentChannel().name}</span>
                  <span className="channel-number-large">{getCurrentChannel().number}</span>
                </div>
                <h1 className="program-title">{selectedProgram.title}</h1>
                <div className="program-meta">
                  {selectedProgram.episode} | {selectedProgram.title} | {formatTime(selectedProgram.startTime)} - {formatTime(selectedProgram.endTime)}
                  {isCurrentlyAiring(selectedProgram) && <span className="live-badge">● LIVE NOW</span>}
                </div>
                <p className="program-description">{selectedProgram.description}</p>
              </div>
            </>
          )}
        </div>

        {/* Program Guide Grid */}
        <div className="program-grid">
          {/* Time Headers */}
          <div className="time-headers">
            {getTimeHeaders().map((time, index) => (
              <div key={index} className="time-header">
                {time}
                {index === 1 && (
                  <div className="current-time-indicator" style={{left: `${getCurrentTimePosition()}%`}}>
                    <div className="time-line"></div>
                    <div className="time-marker">NOW</div>
                  </div>
                )}
              </div>
            ))}
          </div>

          {/* Channel Rows */}
          <div className="channel-grid">
            {channels.map((channel, channelIndex) => (
              <div key={channel.id} className="channel-row">
                {/* Channel Info */}
                <div className="channel-info">
                  <span className="channel-heart">♥</span>
                  <span className="channel-number">{channel.number}</span>
                  <div className="channel-logo-container">
                    <img 
                      src={channel.logo_url} 
                      alt={channel.name}
                      className="channel-logo-image"
                      onError={(e) => {
                        e.target.style.display = 'none';
                        e.target.nextSibling.style.display = 'inline';
                      }}
                    />
                    <span className="channel-logo-fallback" style={{display: 'none'}}>{channel.logo}</span>
                  </div>
                  <span className="channel-name">{channel.name}</span>
                </div>

                {/* Program Blocks */}
                <div className="program-blocks">
                  {channel.programs.map((program, programIndex) => (
                    <div
                      key={program.id}
                      className={`program-block ${
                        focusedSection === 'grid' && 
                        gridFocus.channel === channelIndex && 
                        gridFocus.program === programIndex ? 'focused' : ''
                      } ${isCurrentlyAiring(program) ? 'currently-airing' : ''}`}
                    >
                      <div className="program-title">{program.title}</div>
                      {program.rating && <div className="program-rating">⬛</div>}
                      {isCurrentlyAiring(program) && <div className="live-indicator-small">●</div>}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Data Source Indicator */}
      <div className="data-source">
        <span className="data-badge">📺 Real TV Data from TVmaze</span>
      </div>
    </div>
  );
};

export default App;