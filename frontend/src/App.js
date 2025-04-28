import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import styled from "styled-components";
import html2canvas from "html2canvas";
import ChatMessage from "./components/ChatMessage";
import MessageInput from "./components/MessageInput";
import GameHeader from "./components/GameHeader";
import GameControls from "./components/GameControls";

// 创建axios实例
const api = axios.create({
  baseURL: "/", // 使用相对路径，连接到提供前端的同一服务器
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
  const [currentSender, setCurrentSender] = useState("doctor");
  const [diagnosis, setDiagnosis] = useState("");
  const [error, setError] = useState("");

  const chatContainerRef = useRef(null);
  const gameInitializedRef = useRef(false);

  // 创建新游戏
  const startNewGame = async () => {
    try {
      setIsLoading(true);
      setError("");

      const response = await api.post("/api/new_game");

      setGameId(response.data.game_id);
      setMessages(response.data.messages);
      // 确保current_sender存在，否则默认为doctor
      setCurrentSender(response.data.current_sender || "doctor");
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

      // 立即将currentSender设置为patient，表示等待病人回复
      setCurrentSender("patient");

      const response = await api.post("/api/send_message", {
        game_id: gameId,
        message: message,
      });

      // 更新状态
      setMessages(response.data.messages);
      // 确保current_sender存在，否则默认为doctor
      setCurrentSender(response.data.current_sender || "doctor");
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

  // 保存对话为文本
  const saveConversation = async () => {
    if (!gameId) return;

    try {
      setIsLoading(true);
      setError("");

      const response = await api.post(`/api/save_conversation/${gameId}`);

      // 创建Blob对象
      const blob = new Blob([response.data.conversation_text], {
        type: "text/plain;charset=utf-8",
      });

      // 创建临时下载链接
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.style.display = "none";
      a.href = url;

      // 设置文件名 - 使用日期时间
      const now = new Date();
      const fileName = `AI问诊记录_${now.getFullYear()}${(now.getMonth() + 1)
        .toString()
        .padStart(2, "0")}${now.getDate().toString().padStart(2, "0")}_${now
        .getHours()
        .toString()
        .padStart(2, "0")}${now.getMinutes().toString().padStart(2, "0")}.txt`;
      a.download = fileName;

      // 添加到DOM、点击并移除
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      alert(`对话已保存并开始下载: ${fileName}`);
    } catch (err) {
      setError("保存对话失败，请重试！");
      console.error("保存对话失败:", err);
    } finally {
      setIsLoading(false);
    }
  };

  // 保存对话为图片
  const saveConversationAsImage = async () => {
    if (!gameId) return;

    try {
      setIsLoading(true);
      setError("");

      // 获取要截图的元素
      const chatContainer = document.querySelector(".chat-container");
      if (!chatContainer) {
        throw new Error("找不到聊天容器元素");
      }

      // 创建一个临时容器，用于截图
      const tempContainer = document.createElement("div");
      tempContainer.style.position = "absolute";
      tempContainer.style.left = "-9999px";
      tempContainer.style.width = "500px"; // 与原容器宽度相同
      tempContainer.style.backgroundColor = "#ededed";
      tempContainer.style.padding = "16px";

      // 添加标题
      const title = document.createElement("div");
      title.style.textAlign = "center";
      title.style.fontSize = "18px";
      title.style.fontWeight = "bold";
      title.style.marginBottom = "16px";
      title.style.padding = "10px";
      title.style.backgroundColor = "#07c160";
      title.style.color = "white";
      title.style.borderRadius = "4px";
      title.innerText = "AI问诊对话记录";
      tempContainer.appendChild(title);

      // 复制聊天内容
      const chatContent = chatContainer.cloneNode(true);
      tempContainer.appendChild(chatContent);

      // 添加时间戳
      const timestamp = document.createElement("div");
      timestamp.style.textAlign = "right";
      timestamp.style.fontSize = "12px";
      timestamp.style.color = "#999";
      timestamp.style.marginTop = "16px";
      const now = new Date();
      timestamp.innerText = `保存时间: ${now.getFullYear()}-${(
        now.getMonth() + 1
      )
        .toString()
        .padStart(2, "0")}-${now.getDate().toString().padStart(2, "0")} ${now
        .getHours()
        .toString()
        .padStart(2, "0")}:${now.getMinutes().toString().padStart(2, "0")}`;
      tempContainer.appendChild(timestamp);

      // 添加到DOM
      document.body.appendChild(tempContainer);

      // 使用html2canvas截图
      const canvas = await html2canvas(tempContainer, {
        backgroundColor: "#ededed",
        scale: 2, // 提高清晰度
        logging: false,
        useCORS: true,
      });

      // 移除临时容器
      document.body.removeChild(tempContainer);

      // 转换为图片并下载
      const imgData = canvas.toDataURL("image/png");
      const link = document.createElement("a");
      link.href = imgData;
      link.download = `AI问诊记录_${now.getFullYear()}${(now.getMonth() + 1)
        .toString()
        .padStart(2, "0")}${now.getDate().toString().padStart(2, "0")}_${now
        .getHours()
        .toString()
        .padStart(2, "0")}${now.getMinutes().toString().padStart(2, "0")}.png`;
      link.click();

      alert(`对话已保存为图片并开始下载`);
    } catch (err) {
      setError("保存对话为图片失败，请重试！");
      console.error("保存对话为图片失败:", err);
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
    // 防止在严格模式下重复初始化游戏
    if (!gameInitializedRef.current) {
      gameInitializedRef.current = true;
      startNewGame();
    }
  }, []);

  // 处理新游戏按钮点击
  const handleNewGame = () => {
    // 允许创建新游戏
    startNewGame();
  };

  return (
    <Container>
      <GameHeader
        gameOver={gameOver}
        diagnosis={diagnosis}
        isLoading={isLoading}
        currentSender={currentSender}
      />

      <ChatContainer ref={chatContainerRef} className="chat-container">
        {messages.map((message, index) => (
          <ChatMessage
            key={index}
            sender={message.sender}
            content={message.content}
            isLatest={index === messages.length - 1}
          />
        ))}

        {isLoading && (
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
        onNewGame={handleNewGame}
        onSaveConversation={saveConversation}
        onSaveAsImage={saveConversationAsImage}
        gameOver={gameOver}
        disabled={isLoading}
      />
    </Container>
  );
}

export default App;
