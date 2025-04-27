import React from "react";
import styled from "styled-components";

const MessageContainer = styled.div`
  display: flex;
  flex-direction: ${(props) => (props.isDoctor ? "row-reverse" : "row")};
  margin-bottom: 16px;
  opacity: ${(props) => (props.isLoading ? 0.7 : 1)};
`;

const Avatar = styled.div`
  width: 40px;
  height: 40px;
  border-radius: 4px;
  background-color: ${(props) => (props.isDoctor ? "#07c160" : "#1677ff")};
  color: white;
  display: flex;
  justify-content: center;
  align-items: center;
  flex-shrink: 0;
  font-weight: bold;
`;

const MessageBubble = styled.div`
  max-width: 70%;
  padding: 10px 12px;
  margin: 0 12px;
  border-radius: 4px;
  background-color: ${(props) => (props.isDoctor ? "#95ec69" : "white")};
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  position: relative;

  &::before {
    content: "";
    position: absolute;
    top: 12px;
    ${(props) => (props.isDoctor ? "right: -6px" : "left: -6px")};
    border-style: solid;
    border-width: 6px;
    border-color: transparent;
    ${(props) =>
      props.isDoctor
        ? "border-left-color: #95ec69"
        : "border-right-color: white"};
  }
`;

const MessageContent = styled.div`
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.5;
`;

const LoadingDots = styled.div`
  display: inline-flex;
  align-items: center;

  &::after {
    content: "...";
    animation: loading 1.5s infinite;
    overflow: hidden;
    display: inline-block;
    vertical-align: bottom;
    width: 24px;
  }

  @keyframes loading {
    0% {
      width: 0;
    }
    25% {
      width: 6px;
    }
    50% {
      width: 12px;
    }
    75% {
      width: 18px;
    }
    100% {
      width: 24px;
    }
  }
`;

const SystemMessage = styled.div`
  text-align: center;
  padding: 8px 12px;
  background-color: rgba(0, 0, 0, 0.05);
  border-radius: 16px;
  font-size: 14px;
  color: #666;
  margin: 12px auto;
  max-width: 80%;
`;

const ChatMessage = ({ sender, content, isLatest, isLoading }) => {
  // 系统消息
  if (sender === "system") {
    return <SystemMessage>{content}</SystemMessage>;
  }

  const isDoctor = sender === "doctor";

  // 角色图标
  const avatarText = isDoctor ? "医" : "患";

  return (
    <MessageContainer isDoctor={isDoctor} isLoading={isLoading}>
      <Avatar isDoctor={isDoctor}>{avatarText}</Avatar>
      <MessageBubble isDoctor={isDoctor}>
        <MessageContent>{isLoading ? <LoadingDots /> : content}</MessageContent>
      </MessageBubble>
    </MessageContainer>
  );
};

export default ChatMessage;
