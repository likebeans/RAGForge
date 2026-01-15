#!/bin/bash
# 网络诊断脚本

echo "========== 服务器端诊断 =========="
echo ""

echo "1. 检查端口监听状态："
netstat -tlnp 2>/dev/null | grep 8021 || ss -tlnp 2>/dev/null | grep 8021
echo ""

echo "2. 检查 Docker 容器状态："
docker ps --filter "name=rag_kb" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

echo "3. 测试本机访问："
curl -s -o /dev/null -w "HTTP状态码: %{http_code}, 响应时间: %{time_total}s\n" http://localhost:8021/health
echo ""

echo "4. 检查防火墙规则（需要 sudo）："
echo "请手动执行："
echo "  sudo iptables -L INPUT -n | grep -E '8021|REJECT|DROP'"
echo ""

echo "5. 检查网络接口："
ip addr show | grep -E "inet |UP"
echo ""

echo "========== 客户端诊断命令（在客户端电脑执行） =========="
echo ""
echo "1. 测试端口连通性："
echo "  nc -zv 192.168.1.235 8021"
echo ""
echo "2. 测试 HTTP 访问："
echo "  curl -v --max-time 5 http://192.168.1.235:8021/health"
echo ""
echo "3. 检查路由："
echo "  traceroute 192.168.1.235"
echo ""

echo "========== 可能的解决方案 =========="
echo ""
echo "如果客户端无法访问，尝试："
echo "1. 开放防火墙端口："
echo "   sudo iptables -I INPUT -p tcp --dport 8021 -j ACCEPT"
echo ""
echo "2. 如果使用 firewalld："
echo "   sudo firewall-cmd --add-port=8021/tcp --permanent"
echo "   sudo firewall-cmd --reload"
echo ""
echo "3. 如果使用 ufw："
echo "   sudo ufw allow 8021/tcp"
echo ""
