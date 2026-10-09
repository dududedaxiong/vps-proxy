#!/bin/bash
# Nezha Agent 一键安装脚本 (NeoHeberg IPv6-only VPS)
# 用法: curl -sL https://cdn.jsdelivr.net/gh/dududedaxiong/vps-proxy/install.sh | bash
set -e
echo "=== Nezha Agent 一键安装 ==="
echo "[1/6] 安装依赖..."
apt-get update -qq
apt-get install -y -qq python3 golang-go nodejs npm curl > /dev/null 2>&1
npm install -g pm2 > /dev/null 2>&1
echo "依赖安装完成"
echo "[2/6] 编译 Nezha Agent (需要几分钟)..."
mkdir -p /opt/nezha
if [ ! -f /opt/nezha/nezha-agent ]; then
    go install -p 1 github.com/nezhahq/agent/cmd/agent@latest > /dev/null 2>&1
    cp /root/go/bin/agent /opt/nezha/nezha-agent
    chmod +x /opt/nezha/nezha-agent
fi
echo "Agent 就绪"
echo "[3/6] 下载代理脚本..."
curl -sL https://cdn.jsdelivr.net/gh/dududedaxiong/vps-proxy/p.py -o /opt/nezha/p.py
python3 -m py_compile /opt/nezha/p.py && echo "代理脚本 OK"
echo "[4/6] 配置..."
if [ -z "$NEZHA_UUID" ]; then
    read -p "输入 Agent UUID (面板上添加服务器时生成): " NEZHA_UUID
fi
if [ -z "$NEZHA_SECRET" ]; then
    read -p "输入 Client Secret (面板设置里): " NEZHA_SECRET
fi
cat > /opt/nezha/config.yml << 'CFGEOF'
client_secret: $NEZHA_SECRET
server: 127.0.0.1:18008
tls: false
uuid: $NEZHA_UUID
CFGEOF
echo "配置已写入 (注意: 需手动替换 config.yml 中的变量为实际值)"
echo "[5/6] 配置 Cloudflare Token..."
if [ -z "$TID" ]; then
    read -p "输入 CF-Access-Client-Id: " TID
fi
if [ -z "$TSEC" ]; then
    read -p "输入 CF-Access-Client-Secret: " TSEC
fi
export TID TSEC
echo "[6/6] PM2 启动..."
pm2 delete nezha-proxy nezha-agent 2>/dev/null || true
cd /opt/nezha
pm2 start p.py --name nezha-proxy --interpreter python3
pm2 start ./nezha-agent --name nezha-agent -- -c config.yml
pm2 save
pm2 startup systemd -u root --hp /root > /dev/null 2>&1 || true
echo ""
echo "=== 安装完成 ==="
pm2 list
