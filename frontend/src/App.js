import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import styled from "styled-components";
import ChatMessage from "./components/ChatMessage";
import MessageInput from "./components/MessageInput";
import GameHeader from "./components/GameHeader";
import GameControls from "./components/GameControls";

// 创建axios实例
const api = axios.create({
  baseURL: "http://localhost:5001",
  withCredentials: false,
});

const Container = styled.div`
  display: flex;
  flex-direction: column;
  height: 100vh;
  background-color: #f5f5f5;
  max-width: 500px;
  margin: 0 auto;
  border-left: 1px solid #e0e0e0;
  border-right: 1px solid #e0e0e0;
`;

const ChatContainer = styled.div`
  flex: 1;
  padding: 16px;
  overflow-y: auto;
  background-color: #ededed;
`;

function App() {
  const [messages, setMessages] = useState([]);
  const [gameId, setGameId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [gameOver, setGameOver] = useState(false);
  const [currentSender, setCurrentSender] = useState("");
  const [diagnosis, setDiagnosis] = useState("");
  const [error, setError] = useState("");

  const chatContainerRef = useRef(null);

  // 创建新游戏
  const startNewGame = async () => {
    try {
      setIsLoading(true);
      setError("");

      const response = await api.post("/api/new_game");

      setGameId(response.data.game_id);
      setMessages(response.data.messages);
      setCurrentSender(response.data.current_sender);
      setGameOver(response.data.game_over);
      setDiagnosis("");
    } catch (err) {
      setError("创建游戏失败，请重试！");
      console.error("创建游戏失败:", err);
    } finally {
      setIsLoading(false);
    }
  };

  // 发送消息
  const sendMessage = async (message) => {
    if (!message.trim() || !gameId || isLoading || gameOver) return;

    try {
      setIsLoading(true);
      setError("");

      // 先添加消息到UI，优化体验
      setMessages((prevMessages) => [
        ...prevMessages,
        { sender: "doctor", content: message },
      ]);

      const response = await api.post("/api/send_message", {
        game_id: gameId,
        message: message,
      });

      // 更新状态
      setMessages(response.data.messages);
      setCurrentSender(response.data.current_sender);
      setGameOver(response.data.game_over);

      if (response.data.game_over && response.data.diagnosis) {
        setDiagnosis(response.data.diagnosis);
      }
    } catch (err) {
      setError("发送消息失败，请重试！");
      console.error("发送消息失败:", err);
    } finally {
      setIsLoading(false);
    }
  };

  // 保存对话
  const saveConversation = async () => {
    if (!gameId) return;

    try {
      setIsLoading(true);
      setError("");

      const response = await api.post(`/api/save_conversation/${gameId}`);

      alert(`对话已保存至: ${response.data.filename}`);
    } catch (err) {
      setError("保存对话失败，请重试！");
      console.error("保存对话失败:", err);
    } finally {
      setIsLoading(false);
    }
  };

  // 自动滚动到最新消息
  useEffect(() => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTop =
        chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // 初始加载时创建新游戏
  useEffect(() => {
    startNewGame();
  }, []);

  return (
    <Container>
      <GameHeader
        gameOver={gameOver}
        diagnosis={diagnosis}
        isLoading={isLoading}
        currentSender={currentSender}
      />

      <ChatContainer ref={chatContainerRef}>
        {messages.map((message, index) => (
          <ChatMessage
            key={index}
            sender={message.sender}
            content={message.content}
            isLatest={index === messages.length - 1}
          />
        ))}

        {isLoading && currentSender === "patient" && (
          <ChatMessage sender="patient" content="..." isLoading={true} />
        )}

        {error && (
          <div style={{ color: "red", textAlign: "center", margin: "10px 0" }}>
            {error}
          </div>
        )}
      </ChatContainer>

      <MessageInput
        onSendMessage={sendMessage}
        disabled={isLoading || gameOver || currentSender !== "doctor"}
      />

      <GameControls
        onNewGame={startNewGame}
        onSaveConversation={saveConversation}
        gameOver={gameOver}
        disabled={isLoading}
      />
    </Container>
  );
}

export default App;
