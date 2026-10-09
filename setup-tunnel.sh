#!/bin/bash
# 一键安装 cloudflared 并接入 Tunnel
# 用法: curl -sL https://cdn.jsdelivr.net/gh/dududedaxiong/vps-proxy/setup-tunnel.sh | bash -s "<TOKEN>"
set -e
TOKEN="$1"
if [ -z "$TOKEN" ]; then echo "用法: bash -s <TOKEN>"; exit 1; fi

# 安装 cloudflared (Cloudflare apt 源，有 IPv6)
if ! command -v cloudflared >/dev/null 2>&1; then
  echo "正在安装 cloudflared..."
  mkdir -p /usr/share/keyrings
  curl -sL https://pkg.cloudflare.com/cloudflare-main.gpg -o /usr/share/keyrings/cloudflare-main.gpg
  echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared any main" > /etc/apt/sources.list.d/cloudflared.list
  apt-get update -qq 2>&1 | tail -1
  apt-get install -y -qq cloudflared 2>&1 | tail -2
fi
cloudflared --version

# PM2 启动
pm2 delete cf-tunnel 2>/dev/null || true
pm2 start /usr/bin/cloudflared --name cf-tunnel -- tunnel --no-autoupdate run --token "$TOKEN"
pm2 save

sleep 10
pm2 logs cf-tunnel --lines 5 --nostream | grep -i "registered\|error" || pm2 logs cf-tunnel --lines 5 --nostream
echo "完成，检查 https://s.mick.cc.cd 是否可访问"
