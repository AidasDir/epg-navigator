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
  const [currentCategory, setCurrentCategory] = useState('All');
  const [favorites, setFavorites] = useState(new Set());

  const sidebarItems = [
    'All', 'Recent', 'Favorites ❤️', 'Sports', 'Kids', 'Movies', 'TV Shows'
  ];

  // Handle sidebar item selection
  const handleSidebarSelection = (item) => {
    const cleanItem = item.replace(' ❤️', ''); // Remove heart emoji for API call
    if (cleanItem === 'Recent' || cleanItem === 'Favorites') {
      // Handle these locally for now
      setCurrentCategory(cleanItem);
    } else {
      // Fetch channels for this category
      fetchChannels(cleanItem);
      setCurrentCategory(cleanItem);
    }
  };

  const iconBarIcons = ['🔍', '🏠', '📺', '▶️', '⚙️', '💾', '🔄'];

  // Live clock update
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentTime(new Date());
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  // Fetch channels data from backend
  const fetchChannels = useCallback(async (category = 'All') => {
    try {
      setLoading(true);
      setError(null);
      
      const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
      const categoryParam = category !== 'All' ? `?category=${encodeURIComponent(category)}` : '';
      const response = await fetch(`${backendUrl}/api/channels${categoryParam}`);
      
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
      
      // Reset grid focus when changing categories
      setGridFocus({ channel: 0, program: 0 });
      
    } catch (error) {
      console.error('Error fetching channels:', error);
      setError(`Failed to load ${category} channels`);
      
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

  // Fetch user favorites
  const fetchFavorites = useCallback(async () => {
    try {
      const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/favorites`);
      
      if (response.ok) {
        const data = await response.json();
        setFavorites(new Set(data.favorite_channels));
      }
    } catch (error) {
      console.error('Error fetching favorites:', error);
    }
  }, []);

  // Toggle favorite status
  const toggleFavorite = async (channelId) => {
    try {
      const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
      const response = await fetch(`${backendUrl}/api/channels/${channelId}/favorite`, {
        method: 'POST',
      });
      
      if (response.ok) {
        const result = await response.json();
        const newFavorites = new Set(favorites);
        
        if (result.is_favorite) {
          newFavorites.add(channelId);
        } else {
          newFavorites.delete(channelId);
        }
        
        setFavorites(newFavorites);
        
        // If we're viewing favorites and removed one, refresh the list
        if (currentCategory === 'Favorites' && !result.is_favorite) {
          fetchChannels('Favorites');
        }
      }
    } catch (error) {
      console.error('Error toggling favorite:', error);
    }
  };

  // Mark channel as recently viewed
  const markAsRecent = async (channelId) => {
    try {
      const backendUrl = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';
      await fetch(`${backendUrl}/api/channels/${channelId}/recent`, {
        method: 'POST',
      });
    } catch (error) {
      console.error('Error marking as recent:', error);
    }
  };

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
    fetchFavorites();
  }, [fetchChannels, fetchFavorites]);

  // Handle tab switching
  const handleTabSwitch = (tabIndex) => {
    const category = sidebarItems[tabIndex];
    let categoryName = category;
    
    // Handle special categories
    if (category === 'Favorites ❤️') {
      categoryName = 'Favorites';
    }
    
    fetchChannels(categoryName);
  };

  // Keyboard navigation
  useEffect(() => {
    const handleKeyPress = (e) => {
      switch (e.key) {
        case 'ArrowUp':
          e.preventDefault();
          if (focusedSection === 'sidebar') {
            setSidebarFocus(prev => Math.max(0, prev - 1));
          } else if (focusedSection === 'grid') {
            const newChannelIndex = Math.max(0, gridFocus.channel - 1);
            setGridFocus(prev => ({
              ...prev,
              channel: newChannelIndex
            }));
            updateSelectedProgram(newChannelIndex, gridFocus.program);
          }
          break;
          
        case 'ArrowDown':
          e.preventDefault();
          if (focusedSection === 'sidebar') {
            setSidebarFocus(prev => Math.min(sidebarItems.length - 1, prev + 1));
          } else if (focusedSection === 'grid') {
            const newChannelIndex = Math.min(channels.length - 1, gridFocus.channel + 1);
            setGridFocus(prev => ({
              ...prev,
              channel: newChannelIndex
            }));
            updateSelectedProgram(newChannelIndex, gridFocus.program);
          }
          break;
          
        case 'ArrowLeft':
          e.preventDefault();
          if (focusedSection === 'grid') {
            const newProgramIndex = Math.max(0, gridFocus.program - 1);
            setGridFocus(prev => ({
              ...prev,
              program: newProgramIndex
            }));
            updateSelectedProgram(gridFocus.channel, newProgramIndex);
          } else {
            setFocusedSection('sidebar');
          }
          break;
          
        case 'ArrowRight':
          e.preventDefault();
          if (focusedSection === 'sidebar') {
            setFocusedSection('grid');
            // Update to current focused program when entering grid
            updateSelectedProgram(gridFocus.channel, gridFocus.program);
          } else if (focusedSection === 'grid') {
            const maxPrograms = channels[gridFocus.channel]?.programs.length || 0;
            const newProgramIndex = Math.min(maxPrograms - 1, gridFocus.program + 1);
            setGridFocus(prev => ({
              ...prev,
              program: newProgramIndex
            }));
            updateSelectedProgram(gridFocus.channel, newProgramIndex);
          }
          break;
          
        case 'Enter':
          e.preventDefault();
          if (focusedSection === 'sidebar') {
            const selectedItem = sidebarItems[sidebarFocus];
            handleSidebarSelection(selectedItem);
          }
          break;
          
        case 'f':
        case 'F':
          e.preventDefault();
          if (focusedSection === 'grid' && channels[gridFocus.channel]) {
            // Toggle favorite for current channel
            toggleFavorite(channels[gridFocus.channel].id);
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [focusedSection, sidebarFocus, gridFocus, channels, sidebarItems]);

  const updateSelectedProgram = (channelIndex, programIndex) => {
    if (channels[channelIndex] && channels[channelIndex].programs[programIndex]) {
      setSelectedProgram(channels[channelIndex].programs[programIndex]);
    }
  };

  // Update selected program when channels change
  useEffect(() => {
    if (channels.length > 0 && gridFocus.channel < channels.length) {
      updateSelectedProgram(gridFocus.channel, gridFocus.program);
    }
  }, [channels, gridFocus.channel, gridFocus.program]);

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
    const now = new Date();
    
    // Start timeline 3 hours before current time to show recent programs
    const startTime = new Date(now.getTime() - (3 * 60 * 60 * 1000));
    startTime.setMinutes(0, 0, 0); // Round down to the hour
    
    // Generate 8 hours of programming with 30-minute intervals (16 slots total)
    // This covers 3 hours past + current time + 5 hours future
    for (let i = 0; i < 16; i++) {
      const time = new Date(startTime.getTime() + (i * 30 * 60 * 1000)); // 30-minute intervals
      headers.push(formatTimeSimple(time));
    }
    return headers;
  };

  const getCurrentTimePosition = () => {
    const now = new Date();
    
    // Calculate base time (3 hours before current time, rounded to hour)
    const baseTime = new Date(now.getTime() - (3 * 60 * 60 * 1000));
    baseTime.setMinutes(0, 0, 0);
    
    const minutesSinceStart = (now - baseTime) / (1000 * 60); // Total minutes since start
    const totalMinutesInView = 8 * 60; // 8 hours = 480 minutes
    
    // Calculate percentage within the 8-hour view
    const percentage = Math.min(Math.max((minutesSinceStart / totalMinutesInView) * 100, 0), 100);
    
    return percentage;
  };

  const getCurrentTimePositionInGrid = () => {
    const now = new Date();
    
    // Calculate base time (3 hours before current time, rounded to hour)
    const baseTime = new Date(now.getTime() - (3 * 60 * 60 * 1000));
    baseTime.setMinutes(0, 0, 0);
    
    const minutesSinceStart = (now - baseTime) / (1000 * 60); // Total minutes since start
    const totalMinutesInView = 8 * 60; // 8 hours = 480 minutes
    
    // Calculate percentage within the program grid area (excluding channel info column)
    const percentage = Math.min(Math.max((minutesSinceStart / totalMinutesInView) * 100, 0), 100);
    
    return percentage;
  };

  const getProgramPosition = (program, baseTime) => {
    const programStart = new Date(program.startTime);
    const programEnd = new Date(program.endTime);
    
    // Calculate minutes from base time
    const startMinutes = Math.max(0, (programStart - baseTime) / (1000 * 60));
    const endMinutes = Math.min(480, (programEnd - baseTime) / (1000 * 60)); // Cap at 8 hours
    
    // Convert to percentage of the 8-hour view
    const startPercent = (startMinutes / 480) * 100;
    const widthPercent = ((endMinutes - startMinutes) / 480) * 100;
    
    return {
      left: `${startPercent}%`,
      width: `${Math.max(widthPercent, 1.5)}%` // Minimum 1.5% width for visibility
    };
  };

  const getGridBaseTime = () => {
    const now = new Date();
    const baseTime = new Date(now.getTime() - (3 * 60 * 60 * 1000));
    baseTime.setMinutes(0, 0, 0);
    return baseTime;
  };

  const isCurrentlyAiring = (program) => {
    const now = new Date();
    return program.startTime <= now && program.endTime > now;
  };

  const calculateProgramWidth = (program) => {
    if (!program.startTime || !program.endTime) return 200; // Default width
    
    const duration = (program.endTime - program.startTime) / (1000 * 60); // Duration in minutes
    const pixelsPerMinute = 4; // 4 pixels per minute (adjustable)
    const minWidth = 60; // Minimum width for readability
    
    return Math.max(duration * pixelsPerMinute, minWidth);
  };

  const calculateProgramPosition = (program) => {
    if (!program.startTime) return 0;
    
    // Calculate base time (3 hours before current time, rounded to hour)
    const baseTime = new Date(new Date().getTime() - (3 * 60 * 60 * 1000));
    baseTime.setMinutes(0, 0, 0);
    
    const minutesFromStart = (program.startTime - baseTime) / (1000 * 60);
    const pixelsPerMinute = 4; // Same as width calculation
    
    return Math.max(minutesFromStart * pixelsPerMinute, 0);
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
                (focusedSection === 'sidebar' && sidebarFocus === index) || 
                (currentCategory === item.replace(' ❤️', '')) ? 'focused' : ''
              }`}
              onClick={() => handleSidebarSelection(item)}
            >
              {item}
              {item === 'Favorites ❤️' && favorites.size > 0 && (
                <span className="favorite-count">({favorites.size})</span>
              )}
            </div>
          ))}
        </div>
        <div className="sidebar-divider"></div>
        <div className="sidebar-options">
          <div className="sidebar-item">Sort by A-Z</div>
          <div className="sidebar-item">Jump To Day</div>
        </div>
        <div className="sidebar-help">
          <div className="help-text">Press F to favorite current channel</div>
          <div className="help-text">Press Enter to select</div>
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
                    src={channels[gridFocus.channel]?.logo_url} 
                    alt={channels[gridFocus.channel]?.name}
                    className="channel-logo-large"
                    onError={(e) => {
                      e.target.style.display = 'none';
                    }}
                  />
                  <span className="channel-name-large">{channels[gridFocus.channel]?.name}</span>
                  <span className="channel-number-large">{channels[gridFocus.channel]?.number}</span>
                </div>
                <h1 className="program-title">{selectedProgram.title}</h1>
                <div className="program-meta">
                  {selectedProgram.episode} | {selectedProgram.title} | {formatTimeSimple(selectedProgram.startTime)} - {formatTimeSimple(selectedProgram.endTime)}
                  {isCurrentlyAiring(selectedProgram) && <span className="live-badge">● LIVE NOW</span>}
                </div>
                <p className="program-description">{selectedProgram.description}</p>
              </div>
            </>
          )}
        </div>

        {/* Program Guide Grid */}
        <div className="program-grid">
          {/* Vertical NOW Line */}
          <div 
            className="vertical-now-line" 
            style={{
              left: `${getCurrentTimePositionInGrid()}%`
            }}
          >
            <div className="now-line-full"></div>
            <div className="now-marker-top">NOW</div>
          </div>

          {/* Time Headers */}
          <div className="time-headers">
            {getTimeHeaders().map((time, index) => (
              <div key={index} className="time-header">
                {time}
              </div>
            ))}
          </div>

          {/* Channel Rows */}
          <div className="channel-grid">
            {channels.map((channel, channelIndex) => (
              <div key={channel.id} className="channel-row">
                {/* Channel Info */}
                <div className="channel-info">
                  <button 
                    className={`channel-heart ${favorites.has(channel.id) ? 'favorited' : ''}`}
                    onClick={() => toggleFavorite(channel.id)}
                    title={favorites.has(channel.id) ? 'Remove from favorites' : 'Add to favorites'}
                  >
                    {favorites.has(channel.id) ? '♥' : '♡'}
                  </button>
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
                  {favorites.has(channel.id) && <span className="favorite-star">⭐</span>}
                </div>

                {/* Program Blocks */}
                <div className="program-blocks-container">
                  {channel.programs.map((program, programIndex) => (
                    <div
                      key={program.id}
                      className={`program-block-positioned ${
                        focusedSection === 'grid' && 
                        gridFocus.channel === channelIndex && 
                        gridFocus.program === programIndex ? 'focused' : ''
                      } ${isCurrentlyAiring(program) ? 'currently-airing' : ''}`}
                      style={{
                        left: `${calculateProgramPosition(program)}px`,
                        width: `${calculateProgramWidth(program)}px`
                      }}
                      onClick={() => {
                        setFocusedSection('grid');
                        setGridFocus({ channel: channelIndex, program: programIndex });
                        updateSelectedProgram(channelIndex, programIndex);
                      }}
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