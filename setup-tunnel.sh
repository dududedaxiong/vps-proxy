#!/bin/bash
# 一键安装 cloudflared 并接入 Tunnel
# 用法: curl -sL https://cdn.jsdelivr.net/gh/dududedaxiong/vps-proxy/setup-tunnel.sh | bash -s "<TOKEN>"
set -e
TOKEN="$1"
if [ -z "$TOKEN" ]; then echo "用法: bash -s <TOKEN>"; exit 1; fi

# 安装 cloudflared (via Go, IPv6 可用)
if ! command -v cloudflared >/dev/null 2>&1; then
  echo "正在安装 cloudflared..."
  go install github.com/cloudflare/cloudflared/cmd/cloudflared@latest
  cp /root/go/bin/cloudflared /usr/local/bin/ && chmod +x /usr/local/bin/cloudflared
fi
cloudflared --version

# PM2 启动
pm2 delete cf-tunnel 2>/dev/null || true
pm2 start /usr/local/bin/cloudflared --name cf-tunnel -- tunnel --no-autoupdate run --token "$TOKEN"
pm2 save

sleep 10
pm2 logs cf-tunnel --lines 5 --nostream | grep -i "registered\|error" || pm2 logs cf-tunnel --lines 5 --nostream
echo "完成，检查 https://s.mick.cc.cd 是否可访问"
