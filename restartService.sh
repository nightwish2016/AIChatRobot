#!/bin/bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

pyenv shell myenv3.12  # 或用 source activate


pkill -f gunicorn
sleep 2

# 使用nohup让进程在后台持续运行，即使SSH断开也不会停止
nohup gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 --error-logfile /root/myai/gunicorn/err.log --log-file /root/myai/gunicorn/gunicorn.log "app:create_app()" --log-level debug > /dev/null 2>&1 &

echo "服务已启动，进程ID: $!"
echo "即使关闭SSH连接，服务也会继续运行"