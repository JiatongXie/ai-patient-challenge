import React, { useState } from "react";
import styled from "styled-components";
import axios from "axios";

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

const InfoIcon = styled.div`
  position: absolute;
  left: 16px;
  top: 50%;
  transform: translateY(-50%);
  color: white;
  font-size: 18px;
  opacity: 0.9;
  cursor: pointer;
  transition: opacity 0.2s;

  &:hover {
    opacity: 1;
  }
`;

const StatsPopup = styled.div`
  position: absolute;
  top: 100%;
  left: 16px;
  background-color: white;
  color: #333;
  padding: 12px;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  z-index: 100;
  text-align: left;
  min-width: 200px;

  h4 {
    margin: 0 0 8px 0;
    color: #07c160;
  }

  p {
    margin: 4px 0;
    font-size: 14px;
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
  gameId,
}) => {
  const [showStats, setShowStats] = useState(false);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  // 获取当前游戏的疾病统计数据
  const fetchStats = async () => {
    if (!gameId) return;

    try {
      setLoading(true);
      const response = await axios.get(`/api/current_game_stats/${gameId}`);
      setStats(response.data);
    } catch (error) {
      console.error("获取统计数据失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 处理信息图标点击
  const handleInfoClick = () => {
    if (showStats) {
      setShowStats(false);
    } else {
      setShowStats(true);
      fetchStats();
    }
  };

  // 点击其他地方关闭统计弹窗
  const handleClickOutside = (e) => {
    if (
      showStats &&
      !e.target.closest(".stats-popup") &&
      !e.target.closest(".info-icon")
    ) {
      setShowStats(false);
    }
  };

  // 添加点击事件监听器
  React.useEffect(() => {
    if (showStats) {
      document.addEventListener("click", handleClickOutside);
    }
    return () => {
      document.removeEventListener("click", handleClickOutside);
    };
  }, [showStats]);

  return (
    <HeaderContainer>
      <Title>AI问诊小游戏</Title>

      {gameStarted && (
        <InfoIcon
          onClick={handleInfoClick}
          className="info-icon"
          title="查看统计数据"
        >
          <i className="fas fa-info-circle"></i>
        </InfoIcon>
      )}

      {showStats && (
        <StatsPopup className="stats-popup">
          <h4>当前疾病全服统计</h4>
          {loading ? (
            <p>加载中...</p>
          ) : stats ? (
            <>
              <p>今日尝试次数: {stats.attempts}</p>
              <p>正确回答次数: {stats.correct}</p>
              <p>正确率: {stats.correct_rate}%</p>
            </>
          ) : (
            <p>暂无统计数据</p>
          )}
        </StatsPopup>
      )}

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
