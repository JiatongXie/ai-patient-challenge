import React, { useState } from "react";
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

const SaveOptionsContainer = styled.div`
  position: absolute;
  bottom: 60px;
  right: 50%;
  transform: translateX(50%);
  background-color: white;
  border: 1px solid #e0e0e0;
  border-radius: 4px;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  z-index: 100;
`;

const SaveOption = styled.button`
  display: block;
  width: 100%;
  padding: 10px 16px;
  text-align: left;
  background-color: white;
  border: none;
  border-bottom: 1px solid #f0f0f0;
  font-size: 14px;
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background-color: #f5f5f5;
  }

  &:last-child {
    border-bottom: none;
  }
`;

const GameControls = ({
  onNewGame,
  onSaveConversation,
  onSaveAsImage,
  gameOver,
  disabled,
}) => {
  const [showSaveOptions, setShowSaveOptions] = useState(false);

  const handleSaveClick = () => {
    setShowSaveOptions(true);
  };

  const handleSaveAsText = () => {
    setShowSaveOptions(false);
    onSaveConversation();
  };

  const handleSaveAsImage = () => {
    setShowSaveOptions(false);
    onSaveAsImage();
  };

  // 点击其他地方关闭保存选项
  const handleClickOutside = () => {
    setShowSaveOptions(false);
  };

  return (
    <ControlsContainer>
      <Button primary onClick={onNewGame} disabled={disabled}>
        新游戏
      </Button>

      <Button onClick={handleSaveClick} disabled={disabled}>
        保存对话
      </Button>

      {showSaveOptions && (
        <>
          <div
            onClick={handleClickOutside}
            style={{
              position: "fixed",
              top: 0,
              left: 0,
              right: 0,
              bottom: 0,
              zIndex: 99,
            }}
          />
          <SaveOptionsContainer>
            <SaveOption onClick={handleSaveAsText}>
              保存为文本 (.txt)
            </SaveOption>
            <SaveOption onClick={handleSaveAsImage}>
              保存为图片 (.png)
            </SaveOption>
          </SaveOptionsContainer>
        </>
      )}
    </ControlsContainer>
  );
};

export default GameControls;
