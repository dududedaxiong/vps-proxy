#!/bin/bash
# 一键安装 cloudflared 并接入 Tunnel
# 用法: curl -sL https://cdn.jsdelivr.net/gh/dududedaxiong/vps-proxy/setup-tunnel.sh | bash -s "<TOKEN>"
set -e
TOKEN="$1"
if [ -z "$TOKEN" ]; then echo "用法: bash -s <TOKEN>"; exit 1; fi

# 安装 cloudflared (从 Go 代理下载源码包编译，绕开 go install 限制)
if ! command -v cloudflared >/dev/null 2>&1; then
  echo "正在安装 cloudflared..."
  VER=$(curl -sL "https://proxy.golang.org/github.com/cloudflare/cloudflared/@v/list" | sort -V | tail -1)
  echo "版本: $VER"
  rm -rf /tmp/cfbuild && mkdir -p /tmp/cfbuild && cd /tmp/cfbuild
  curl -sL "https://proxy.golang.org/github.com/cloudflare/cloudflared/@v/${VER}.zip" -o cf.zip
  unzip -q cf.zip
  cd "github.com/cloudflare/cloudflared@${VER}"
  go build -o /usr/local/bin/cloudflared ./cmd/cloudflared
  chmod +x /usr/local/bin/cloudflared
  cd / && rm -rf /tmp/cfbuild
fi
cloudflared --version

# PM2 启动
pm2 delete cf-tunnel 2>/dev/null || true
pm2 start /usr/local/bin/cloudflared --name cf-tunnel -- tunnel --no-autoupdate run --token "$TOKEN"
pm2 save

sleep 10
pm2 logs cf-tunnel --lines 5 --nostream | grep -i "registered\|error" || pm2 logs cf-tunnel --lines 5 --nostream
echo "完成，检查 https://s.mick.cc.cd 是否可访问"
