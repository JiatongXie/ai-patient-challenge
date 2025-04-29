import React from "react";
import styled from "styled-components";

const HeaderContainer = styled.div`
  padding: 12px 16px;
  background-color: #07c160;
  color: white;
  text-align: center;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  position: relative;
`;

const Title = styled.h1`
  margin: 0;
  font-size: 18px;
  font-weight: 500;
`;

const GithubLink = styled.a`
  position: absolute;
  right: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: white;
  font-size: 20px;
  opacity: 0.9;
  transition: opacity 0.2s;

  &:hover {
    opacity: 1;
  }
`;

const StatusBar = styled.div`
  display: flex;
  justify-content: center;
  margin-top: 4px;
  font-size: 14px;
  opacity: 0.9;
`;

const StatusIndicator = styled.div`
  display: flex;
  align-items: center;
  padding: 4px 8px;
  border-radius: 10px;
  background-color: ${(props) =>
    props.active ? "rgba(255, 255, 255, 0.2)" : "transparent"};
`;

const PulsingDot = styled.div`
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: ${(props) => props.color || "#fff"};
  margin-right: 4px;
  animation: ${(props) => (props.pulsing ? "pulse 1.5s infinite" : "none")};

  @keyframes pulse {
    0% {
      transform: scale(0.8);
      opacity: 0.7;
    }
    50% {
      transform: scale(1.2);
      opacity: 1;
    }
    100% {
      transform: scale(0.8);
      opacity: 0.7;
    }
  }
`;

const DiagnosisText = styled.div`
  margin-top: 6px;
  font-size: 14px;
  font-weight: 500;
  background-color: rgba(255, 255, 255, 0.2);
  padding: 4px 8px;
  border-radius: 4px;
  display: inline-block;
`;

const GameHeader = ({
  gameOver,
  diagnosis,
  isLoading,
  currentSender,
  gameStarted,
}) => {
  return (
    <HeaderContainer>
      <Title>AI问诊小游戏</Title>

      <GithubLink
        href="https://github.com/metrovoc/ai-patient-challenge"
        target="_blank"
        rel="noopener noreferrer"
        title="查看源代码"
      >
        <i className="fab fa-github"></i>
      </GithubLink>

      {!gameStarted ? null : gameOver ? ( // 游戏未开始时不显示状态栏
        <div>
          <StatusBar>
            <StatusIndicator active={true}>
              <PulsingDot color="#ffd700" />
              <span>游戏已结束</span>
            </StatusIndicator>
          </StatusBar>
          {diagnosis && <DiagnosisText>正确诊断: {diagnosis}</DiagnosisText>}
        </div>
      ) : (
        <StatusBar>
          <StatusIndicator active={currentSender === "patient" || isLoading}>
            <PulsingDot pulsing={isLoading} />
            <span>病人{isLoading ? "思考中..." : ""}</span>
          </StatusIndicator>
          <span style={{ margin: "0 8px" }}>•</span>
          <StatusIndicator active={currentSender === "doctor" && !isLoading}>
            <PulsingDot pulsing={currentSender === "doctor" && !isLoading} />
            <span>医生</span>
          </StatusIndicator>
        </StatusBar>
      )}
    </HeaderContainer>
  );
};

export default GameHeader;
