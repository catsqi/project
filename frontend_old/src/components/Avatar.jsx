import React from 'react';
import './Avatar.css';

const Avatar = ({ state }) => {
  return (
    <div className="avatar-wrapper">
      <div className={`ai-core ${state}`}>
        <div className="core-inner"></div>
        <div className="ring ring-1"></div>
        <div className="ring ring-2"></div>
        <div className="ring ring-3"></div>
        
        {/* Particle nodes around the core */}
        <div className="particle p1"></div>
        <div className="particle p2"></div>
        <div className="particle p3"></div>
      </div>
    </div>
  );
};

export default Avatar;
