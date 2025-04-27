import React, { useState } from "react";
import styled from "styled-components";

const InputContainer = styled.div`
  display: flex;
  padding: 10px;
  background-color: #f5f5f5;
  border-top: 1px solid #e0e0e0;
`;

const TextArea = styled.textarea`
  flex: 1;
  padding: 10px;
  border-radius: 4px;
  border: 1px solid #e0e0e0;
  resize: none;
  font-family: inherit;
  font-size: 16px;
  height: 42px;
  max-height: 120px;
  outline: none;
  transition: border-color 0.3s;

  &:focus {
    border-color: #07c160;
  }

  &:disabled {
    background-color: #f9f9f9;
    cursor: not-allowed;
  }
`;

const SendButton = styled.button`
  background-color: #07c160;
  color: white;
  border: none;
  border-radius: 4px;
  padding: 0 16px;
  margin-left: 10px;
  font-size: 16px;
  cursor: pointer;
  transition: opacity 0.3s;

  &:hover {
    opacity: 0.9;
  }

  &:disabled {
    background-color: #9fd6b8;
    cursor: not-allowed;
  }
`;

const MessageInput = ({ onSendMessage, disabled }) => {
  const [message, setMessage] = useState("");

  const handleSubmit = (e) => {
    e.preventDefault();
    if (message.trim() && !disabled) {
      onSendMessage(message);
      setMessage("");
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <InputContainer>
      <TextArea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={disabled ? "等待病人回复..." : "输入诊断或提问..."}
        disabled={disabled}
      />
      <SendButton onClick={handleSubmit} disabled={disabled || !message.trim()}>
        发送
      </SendButton>
    </InputContainer>
  );
};

export default MessageInput;
