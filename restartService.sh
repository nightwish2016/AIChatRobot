#!/bin/bash
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

pyenv shell myenv3.12  # 或用 source activate

cd /root/myai/0727/AICHATROBOT || exit
git pull
pkill -f gunicorn
sleep 2

nohup gunicorn -w 4 -b 0.0.0.0:5000 \
  --timeout 120 \
  --error-logfile /root/myai/gunicorn/err.log \
  --access-logfile /root/myai/gunicorn/gunicorn.log \
  "app:create_app" \
  --log-level debug > /dev/null 2>&1 &
