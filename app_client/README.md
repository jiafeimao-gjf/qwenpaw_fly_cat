# App Client

Vue 3 Web 客户端，配合 App Server 使用，供用户与 QwenPaw 进行对话。

## 快速开始

```bash
npm install
npm run dev
```

启动后自动绑定本机局域网 IP，方便手机访问。

## 环境变量

```bash
HOST=0.0.0.0 PORT=3000 API_TARGET=http://localhost:8080 npm run dev
```

## 功能

- 用户登录（JWT 认证）
- 实时消息发送
- AI 响应轮询（5 秒间隔）
- 会话列表和历史消息
- Markdown 渲染支持
- 响应式布局，适配手机和桌面

## 组件结构

```
src/
├── App.vue              # 根组件
├── main.js              # 入口
├── api/client.js        # API 调用封装
├── stores/auth.js       # 认证状态管理
└── components/
    ├── Login.vue         # 登录页
    ├── ChatRoom.vue      # 聊天室
    └── MessageBubble.vue # 消息气泡
```

## 移动端适配

- 响应式布局（桌面/平板/手机）
- 侧边会话栏在移动端变为可滑出抽屉
- 输入框 16px 字体防止 iOS 自动缩放
- 支持安全区域（iPhone Home Indicator）