# AI Chat Robot - 现代化AI助手平台

一个基于Flask的现代化AI聊天机器人平台，集成了聊天、图像生成和文字转语音功能。

## 🚀 主要功能

### 🤖 AI 聊天
- 支持多种AI模型：DeepSeek、GPT-4O-mini、GPT-4O
- 实时对话界面
- 代码高亮显示
- Markdown渲染支持

### 🎨 AI 图像生成
- 支持DALL-E 2和DALL-E 3模型
- 多种图像尺寸选择
- 大图预览功能
- 一键下载生成图像

### 🔊 文字转语音 (TTS)
- 多种语音选择
- 实时音频生成
- 音频播放和下载功能
- 支持中文文本

### 🎬 视频字幕提取
- 支持多种视频格式
- 内嵌字幕提取
- 外挂字幕识别
- AI语音识别生成字幕
- **Cloudflare R2存储支持** - 文件不存储在本地服务器

## 🎨 现代化UI设计

### 设计特色
- **响应式设计**：完美适配桌面端、平板和手机端
- **现代化界面**：采用渐变背景和毛玻璃效果
- **流畅动画**：丰富的交互动画和过渡效果
- **直观操作**：简洁明了的用户界面

### 技术亮点
- **Flexbox布局**：灵活的响应式布局系统
- **CSS Grid**：现代化的网格布局
- **移动优先**：优先考虑移动端用户体验
- **无障碍设计**：支持键盘导航和屏幕阅读器

## 📱 响应式支持

### 桌面端 (1024px+)
- 完整功能展示
- 多列布局
- 大屏幕优化

### 平板端 (768px - 1024px)
- 适配中等屏幕
- 优化触摸操作
- 保持核心功能

### 手机端 (< 768px)
- 单列布局
- 触摸友好界面
- 优化小屏幕显示

## 🛠️ 技术栈

### 后端
- **Flask** - Python Web框架
- **SQLite** - 轻量级数据库
- **JWT** - 用户认证
- **CORS** - 跨域支持

### 前端
- **HTML5** - 语义化标记
- **CSS3** - 现代化样式
- **JavaScript** - 交互逻辑
- **响应式设计** - 多设备适配

### AI服务
- **OpenAI API** - GPT模型
- **DeepSeek API** - 中文AI模型
- **DALL-E** - 图像生成
- **TTS服务** - 文字转语音
- **Whisper API** - 语音识别

### 存储服务
- **SQLite** - 本地数据库
- **Cloudflare R2** - 对象存储（可选）

## 🚀 快速开始

### 环境要求
- Python 3.7+
- Flask
- 现代浏览器

### 安装步骤
1. 克隆项目
```bash
git clone [项目地址]
cd AIChatRobot
```

2. 安装依赖
```bash
pip install -r requirements.txt
```

3. 配置环境变量
```bash
# 设置OpenAI API密钥
export OPENAI_API_KEY="your-api-key"

# 可选：配置Cloudflare R2存储（用于字幕提取功能）
export CLOUDFLARE_ACCOUNT_ID="your-account-id"
export R2_ACCESS_KEY_ID="your-access-key-id"
export R2_SECRET_ACCESS_KEY="your-secret-access-key"
export R2_BUCKET_NAME="your-bucket-name"
```

4. 运行应用
```bash
python app.py
```

5. 访问应用
```
http://localhost:5000
```

## 📁 项目结构

```
AIChatRobot/
├── app/
│   ├── static/
│   │   ├── css/
│   │   │   ├── common/          # 通用样式
│   │   │   ├── chat/           # 聊天页面样式
│   │   │   └── image/          # 图像页面样式
│   │   ├── js/                 # JavaScript文件
│   │   └── image/              # 静态图片
│   ├── templates/              # HTML模板
│   ├── views/                  # 视图控制器
│   ├── r2_storage.py          # R2存储工具类
│   └── DB/                     # 数据库相关
├── logs/                       # 日志文件
├── uploads/                    # 本地文件上传目录
├── subtitles/                  # 本地字幕文件目录
├── requirements.txt            # 依赖列表
├── r2_config_example.env      # R2配置示例
├── R2_STORAGE_README.md       # R2存储详细说明
└── test_r2_storage.py         # R2存储测试脚本
```

## 🎯 用户体验优化

### 界面改进
- ✅ 现代化渐变背景
- ✅ 毛玻璃效果
- ✅ 圆角设计
- ✅ 阴影效果
- ✅ 流畅动画

### 交互优化
- ✅ 悬停效果
- ✅ 点击反馈
- ✅ 加载动画
- ✅ 错误提示
- ✅ 成功反馈

### 移动端优化
- ✅ 触摸友好按钮
- ✅ 适配小屏幕
- ✅ 优化字体大小
- ✅ 简化导航

## 🔧 自定义配置

### Cloudflare R2存储配置

如果您希望使用Cloudflare R2存储来存储视频和字幕文件（而不是本地存储），请参考以下配置：

1. **创建R2存储桶**：在Cloudflare控制台创建R2存储桶
2. **生成API令牌**：获取访问密钥ID和秘密访问密钥
3. **设置环境变量**：配置必要的环境变量
4. **运行测试**：使用 `python test_r2_storage.py` 验证配置

详细配置说明请参考：[R2_STORAGE_README.md](R2_STORAGE_README.md)

### 主题颜色
可以在CSS文件中修改主色调：
```css
:root {
    --primary-color: #667eea;
    --secondary-color: #764ba2;
    --success-color: #28a745;
    --danger-color: #dc3545;
}
```

### 响应式断点
```css
/* 手机端 */
@media (max-width: 768px) { }

/* 平板端 */
@media (min-width: 769px) and (max-width: 1024px) { }

/* 桌面端 */
@media (min-width: 1025px) { }
```

## 📈 性能优化

- **CSS优化**：使用现代CSS特性
- **JavaScript优化**：异步加载和事件委托
- **图片优化**：响应式图片和懒加载
- **缓存策略**：浏览器缓存优化

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进项目！

## 📄 许可证

MIT License

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交Issue
- 发送邮件

---

**享受现代化的AI聊天体验！** 🎉
