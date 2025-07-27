#!/bin/bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

pyenv shell myenv3.12  # 或用 source activate

# 创建日志目录
mkdir -p /root/myai/uwsgi

git pull

# 停止现有的uWSGI进程
pkill -f uwsgi
sleep 2

# 启动uWSGI
uwsgi --ini uwsgi_streaming.ini &

echo "uWSGI started with streaming support" 