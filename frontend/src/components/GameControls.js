import React from "react";
import styled from "styled-components";

const ControlsContainer = styled.div`
  display: flex;
  padding: 8px 10px;
  background-color: #f5f5f5;
  border-top: 1px solid #e0e0e0;
  justify-content: space-around;
`;

const Button = styled.button`
  background-color: ${(props) => (props.primary ? "#07c160" : "white")};
  color: ${(props) => (props.primary ? "white" : "#07c160")};
  border: ${(props) => (props.primary ? "none" : "1px solid #07c160")};
  border-radius: 4px;
  padding: 8px 16px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s;
  flex: 1;
  margin: 0 6px;

  &:hover {
    opacity: 0.9;
    transform: translateY(-1px);
  }

  &:active {
    transform: translateY(1px);
  }

  &:disabled {
    background-color: ${(props) => (props.primary ? "#9fd6b8" : "#f9f9f9")};
    color: ${(props) => (props.primary ? "white" : "#aaa")};
    border-color: ${(props) => (props.primary ? "transparent" : "#ddd")};
    cursor: not-allowed;
    transform: none;
  }
`;

const GameControls = ({
  onNewGame,
  onSaveConversation,
  gameOver,
  disabled,
}) => {
  return (
    <ControlsContainer>
      <Button primary onClick={onNewGame} disabled={disabled}>
        新游戏
      </Button>

      <Button onClick={onSaveConversation} disabled={disabled}>
        保存对话
      </Button>
    </ControlsContainer>
  );
};

export default GameControls;
