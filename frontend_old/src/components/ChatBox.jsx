import React, { useEffect, useRef } from 'react';
import './ChatBox.css';

const ChatBox = ({ messages, aiState }) => {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, aiState]);

  return (
    <div className="chatbox-container">
      <div className="messages-area">
        {messages.map((msg) => (
          <div key={msg.id} className={`message-row ${msg.sender}`}>
            <div className="message-bubble">
              <span className="sender-label">{msg.sender === 'user' ? 'YOU' : 'AI'}</span>
              <p className="message-text">{msg.text}</p>
            </div>
          </div>
        ))}
        {aiState === 'thinking' && (
          <div className="message-row ai">
            <div className="message-bubble typing">
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="chatbox-footer">
        <div className="live-indicator">
          <span className={`signal-dot ${aiState !== 'idle' ? 'active' : ''}`}></span>
          {aiState === 'idle' ? 'Disconnected' : 'Live Transcript'}
        </div>
      </div>
    </div>
  );
};

export default ChatBox;
