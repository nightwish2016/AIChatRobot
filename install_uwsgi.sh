#!/bin/bash

# 激活虚拟环境
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
pyenv shell myenv3.12

# 安装uWSGI
pip install uwsgi

# 验证安装
uwsgi --version

echo "uWSGI installation completed" 