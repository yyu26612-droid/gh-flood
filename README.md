# gh-flood

小工具仓库。`runner_blast.py` 是零依赖压测脚本，`.github/workflows/run.yml` 是
20 个并行 job 的调度入口，每个 job 从不同的云出口发压。

## 手动跑

```
python3 runner_blast.py -c 100 -n 600 --mode mix
```

## 在 Actions 里跑

Actions → run → Run workflow，填 conc / dur / mode 即可。
`mode` 可选 `loginsub` `index` `sendsms` `login` `regsub` `mix`。
