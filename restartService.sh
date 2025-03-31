git pull
pkill gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 --error-logfile /root/myai/gunicorn/err.log --log-file /root/myai/gunicorn/gunicorn.log "app:create_app()" --log-level debug &