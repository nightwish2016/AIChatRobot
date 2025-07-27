#!/bin/bash

echo "=== Flask 服务调试工具 ==="

# 检查系统信息
echo "1. 系统信息:"
echo "   OS: $(uname -a)"
echo "   Python 版本: $(python3 --version 2>/dev/null || echo 'Python3 未安装')"
echo "   pip 版本: $(pip --version 2>/dev/null || echo 'pip 未安装')"

# 检查 pyenv
echo "2. pyenv 检查:"
if command -v pyenv &> /dev/null; then
    echo "   pyenv 已安装: $(pyenv --version)"
    echo "   Python 版本列表:"
    pyenv versions
else
    echo "   pyenv 未安装"
fi

# 检查项目目录
echo "3. 项目目录检查:"
PROJECT_DIR="/root/myai/0727/AICHATROBOT"
if [ -d "$PROJECT_DIR" ]; then
    echo "   项目目录存在: $PROJECT_DIR"
    echo "   目录内容:"
    ls -la "$PROJECT_DIR" | head -10
else
    echo "   项目目录不存在: $PROJECT_DIR"
fi

# 检查环境变量
echo "4. 环境变量检查:"
echo "   PRODUCTION_APPID: ${PRODUCTION_APPID:-'未设置'}"
echo "   PRODUCTION_KEY_PATH: ${PRODUCTION_KEY_PATH:-'未设置'}"

# 检查端口占用
echo "5. 端口检查:"
if netstat -tlnp 2>/dev/null | grep -q ":5000 "; then
    echo "   端口 5000 被占用:"
    netstat -tlnp | grep ":5000 "
else
    echo "   端口 5000 未被占用"
fi

# 检查进程
echo "6. 进程检查:"
if pgrep -f gunicorn > /dev/null; then
    echo "   gunicorn 进程正在运行:"
    ps aux | grep gunicorn | grep -v grep
else
    echo "   没有 gunicorn 进程在运行"
fi

# 检查日志文件
echo "7. 日志文件检查:"
LOG_DIR="/root/myai/gunicorn"
if [ -d "$LOG_DIR" ]; then
    echo "   日志目录存在: $LOG_DIR"
    if [ -f "$LOG_DIR/err.log" ]; then
        echo "   最近的错误日志:"
        tail -5 "$LOG_DIR/err.log"
    fi
    if [ -f "$LOG_DIR/gunicorn.log" ]; then
        echo "   最近的访问日志:"
        tail -5 "$LOG_DIR/gunicorn.log"
    fi
else
    echo "   日志目录不存在: $LOG_DIR"
fi

# 测试 Flask 应用
echo "8. Flask 应用测试:"
cd "$PROJECT_DIR" 2>/dev/null && {
    if python -c "from app import app; print('Flask 应用导入成功')" 2>/dev/null; then
        echo "   Flask 应用可以正常导入"
    else
        echo "   Flask 应用导入失败"
        echo "   错误信息:"
        python -c "from app import app" 2>&1
    fi
} || echo "   无法切换到项目目录"

echo "=== 调试完成 ===" 