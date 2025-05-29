import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import './App.css';

const App = () => {
  // Navigation state
  const [focusedSection, setFocusedSection] = useState('sidebar'); // 'sidebar', 'grid'
  const [sidebarFocus, setSidebarFocus] = useState(0);
  const [gridFocus, setGridFocus] = useState({ channel: 0, program: 0 });
  
  // Data state
  const [channels] = useState([
    { id: 1, number: '2.1', name: 'FOX', logo: '🦊', programs: [] },
    { id: 2, number: '4.1', name: 'NBC', logo: '🦚', programs: [] },
    { id: 3, number: '7.1', name: 'ABC', logo: '🔷', programs: [] },
    { id: 4, number: '11.1', name: 'CBS', logo: '👁️', programs: [] },
    { id: 5, number: '13.1', name: 'PBS', logo: '📚', programs: [] },
    { id: 6, number: '24.1', name: 'ESPN', logo: '⚽', programs: [] },
    { id: 7, number: '32.1', name: 'CNN', logo: '📺', programs: [] }
  ]);
  
  const [currentTime] = useState(new Date());
  const [selectedProgram, setSelectedProgram] = useState(null);
  const [loading, setLoading] = useState(true);

  const sidebarItems = [
    'All', 'Recent', 'Favorites ❤️', 'Sports', 'Kids', 'Movies', 'TV Shows'
  ];

  const iconBarIcons = ['🔍', '🏠', '📺', '▶️', '⚙️', '💾', '🔄'];

  // Generate sample program data with realistic times
  const generatePrograms = useCallback(() => {
    const programs = [];
    const baseTime = new Date();
    baseTime.setMinutes(0, 0, 0); // Round to hour
    
    for (let i = 0; i < 6; i++) { // 6 hours of programming
      const startTime = new Date(baseTime.getTime() + (i * 60 * 60 * 1000));
      programs.push({
        id: `prog-${i}`,
        title: i === 0 ? 'The Jennifer Hudson Show' : `Program ${i + 1}`,
        episode: i === 0 ? 'S3 E98' : `S1 E${i + 1}`,
        startTime: startTime,
        endTime: new Date(startTime.getTime() + (60 * 60 * 1000)), // 1 hour duration
        description: i === 0 ? 
          'Award-winning daytime talk show featuring celebrity interviews, musical performances, and inspiring human interest stories.' :
          `Description for program ${i + 1}. Lorem ipsum dolor sit amet, consectetur adipiscing elit.`,
        image: i === 0 ? 'https://via.placeholder.com/120x80/1976D2/FFFFFF?text=JH' : 
               `https://via.placeholder.com/120x80/333333/FFFFFF?text=P${i + 1}`,
        rating: i === 0 ? 'R' : null
      });
    }
    return programs;
  }, []);

  useEffect(() => {
    // Initialize program data for all channels
    const updatedChannels = channels.map(channel => ({
      ...channel,
      programs: generatePrograms()
    }));
    
    // Set initial selected program
    setSelectedProgram(updatedChannels[0].programs[0]);
    setLoading(false);
  }, [channels, generatePrograms]);

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
    return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  };

  const getTimeHeaders = () => {
    const headers = ['Today'];
    const baseTime = new Date();
    baseTime.setMinutes(0, 0, 0);
    
    for (let i = 0; i < 6; i++) {
      const time = new Date(baseTime.getTime() + (i * 60 * 60 * 1000));
      headers.push(formatTime(time));
    }
    return headers;
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="loading-text">Loading TV Guide...</div>
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
                <img src={selectedProgram.image} alt={selectedProgram.title} />
              </div>
              <div className="program-details">
                <h1 className="program-title">{selectedProgram.title}</h1>
                <div className="program-meta">
                  {selectedProgram.episode} | {selectedProgram.title} | {formatTime(selectedProgram.startTime)} - {formatTime(selectedProgram.endTime)}
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
                  <span className="channel-logo">{channel.logo}</span>
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
                      }`}
                    >
                      <div className="program-title">{program.title}</div>
                      {program.rating && <div className="program-rating">⬛</div>}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;