# 主机续跑交接

最新执行资源调整（2026-09-17，优先于下文旧参数）：用户再次要求加速后，矩阵从8并行提高为 `scripts/formal_run.py --workers 12 --memory-budget-gib 24 --memory-reserve-gib 6`。1007个已保存点及所有已保存stage plan经核验完全保留；仅未完成且未保存的在途任务可能重算。12是上限，保留现有内存成本估算与6GiB实时余量保护；后处理仍8并行，正式计时仍串行。只调整执行资源，不更改冻结协议或研究输入。PID/日志以 `results/formal/desktop_resume.json` 为准，实际检查见 `MONITORING_LOG.md`；自动检查仍每5分钟。

## 主机已验证 Windows 原生执行（2026-09-17 更新）

检查频率更新：按用户要求评估后，主机自动续接检查已从每30分钟缩短为每5分钟。正常时轻量核对、保持安静；5分钟没有日志不代表卡死，仍须结合进程活动和原600秒超时/一次重试判断。矩阵结束到数值后处理的独立轮询间隔本来就是30秒。

最新加速设置：用户要求提高并行度后，改为 `scripts/formal_run.py --workers 8 --memory-budget-gib 22 --memory-reserve-gib 6`。最多8个任务按冻结 workload 大小预留预计内存，并检查实时物理/提交余量；大型任务占用更大预算，短任务填充余量，实际并发可变。此执行层调度不改变实验输入、模型或共同 grid。当前 PID、日志和调度快照路径以 `results/formal/desktop_resume.json` 为准；已启用并更新本主机每30分钟自动续接检查。不得额外启动第二个 runner。

用户要求优先检查原生 Python 后，执行层已补齐 Windows 支持：没有 SIGALRM 时用可终止的 spawn 子进程执行每次 reference，仍保留600秒超时和一次相同重试；后处理使用只读 Windows 进程状态查询，不调用 Windows 的 `os.kill(pid,0)`。冻结 JB1、协议、共同 grid、依赖 commit 和历史缓存均未修改。25项测试通过；新鲜短 trace 的14个请求在所有逐请求指标、最终模拟时间、E/R两种 SLA 判定上与原缓存精确一致，记录见 `results/formal/desktop_host_check.json`。因此下文“必须使用 WSL2”是原交接时的限制，已被本次验证过的执行层适配取代，无需安装 WSL。

PowerShell 设置 `PYTHONUTF8=1`、`PYTHONDONTWRITEBYTECODE=1`，使用 `.venv\Scripts\python.exe` 执行原来的脚本。当前主机是 Python3.12.10（原机3.12.14），差异已通过上述对照核验。新行记录主机来源，旧195行保持原样；正式顺序计时仍全部在主机重新测量。Git 的本仓库 `core.autocrlf=false` 保证冻结文件字节一致。

## 当前是暂停状态

用户要求停止笔记本计算，改到主机继续。笔记本的实验进程、后处理进程、临时防休眠进程均已停止，自动续跑任务已暂停。**不要在笔记本自动恢复。**

已经保存195个完整 reference 运行、390个 SLA 配对点，已记录的失败点为0。断点位于 `results/formal/groups/`，原始指标位于 `results/raw_reference/`，冻结 workload 在 `results/formal/workloads/`。`results/formal/machine_handoff.json` 记录了暂停时的计划、未完成点、缓存索引和机器信息。未完成计算不是 unsafe，恢复时重新计算；成功写入的缓存可直接复用。

## 在主机上准备

只需要本 JournalArticle 仓库即可恢复正式矩阵；当前阶段不需要复制 CA 论文、reviewer 原件或笔记本虚拟环境。依赖从公开仓库的固定 commit 重建。Python 使用3.12；原环境具体为3.12.14。计算使用 CPU，无需 GPU。

当前超时实现依赖 POSIX `SIGALRM`。macOS/Linux 可使用；如果主机是 Windows，请在 WSL2 的 Linux 环境执行以下命令，不要直接用 Windows 原生 Python 跑现有 runner。

```bash
git clone https://github.com/HaochenLv/JournalArticle.git
cd JournalArticle
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/bootstrap.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m unittest discover -s tests -q
```

已有该仓库时先检查本地改动，再同步最新 main，不要覆盖用户改动。依赖及测试通过后，在目标主机做一个短 trace 的新鲜 reference 对照，核对已保存的逐请求指标和 verdict，记录跨机器一致性；不要为了匹配旧数字改模型。笔记本只做了迁移准备，没有启动新的对照实验。

## 从断点恢复

在目标主机确认没有重复 runner 后执行：

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python scripts/formal_run.py --workers 8
```

runner 复用已完成点和保存的 stage plan，继续共同 grid 的 refinement。不要删除结果、重新生成 workload、重置协议或重跑全部历史实验。并行进程现已显式使用 spawn，以避免 Linux 下在线程中 fork。顺序计时的机器信息采集已兼容 macOS/Linux；这两处迁移准备没有改变冻结 JB1 或实验输入。

矩阵完成后按 `docs/FORMAL_RUNBOOK.md` 运行分析、mismatch、mitigation、核验、绘图、顺序计时。也可在目标主机用 `scripts/formal_followthrough.py --wait-pid <主矩阵进程PID>` 接上后处理；不要复用笔记本 PID。自动续跑保持暂停，只有在主机明确接管后才配置主机的后续检查。

## 研究范围与剩余工作

主线固定：evaluator 判定可靠性 → sampled capacity error → partition decision error → controlled profile mismatch。不是新 optimizer，不做 GPU 部署，也不重新发散方向。

基线审计已结束：使用明确标注的 recovered JB1，不是找回的 CA final source。2051-token ledger和24组轨迹检查通过；raw-progress版本不复现12组已发表边界，只有把旧5ms放回progress才恢复12/12。差异已记录，禁止重新开展历史代码考古。`src/journal_baseline.py` 的冻结 SHA 不得改变。

正式协议为 FI-JB1-v1：6个新seed/window、30/120s trace、76个configuration/regime、5-shift主比较、两种链路及A100控制。所有候选使用同一组refinement点。完整要求以 `docs/FORMAL_EXPERIMENT_PROTOCOL.md` 为准。

剩余工作：完成RQ1–RQ4和六种简单mitigation；检查分母、重复、ties、非单调、censoring、失败/timeout、共同grid和fingerprints；保留负结果。机制分析已有一个完整、逐指标一致的保守分歧追踪，继续选择乐观分歧、大容量误差但winner稳定，以及真实reversal（若存在）。不能可靠归因时明确说明。不要把未完成矩阵当作完成证据。

原始runtime包含笔记本并发负载影响。迁移后区分机器来源，所有正式顺序计时在主机上重新测量，不混合两台机器的wall time计算speedup。

最终更新 CURRENT_STATUS.md、EXPERIMENT_LOG.md、docs/MECHANISM_ANALYSIS.md、docs/CLAIM_BOUNDARY.md，并创建中文 `FORMAL_EVIDENCE_REPORT.md`，依次包含：

1. 一句话结论。
2. Baseline是否可信。
3. RQ1：什么时候判断对/错，给数字。
4. RQ2：容量预测错多少，给数字。
5. RQ3：误差是否导致partition选错，重点分析。
6. RQ4：profile mismatch影响。
7. 主要机制。
8. 意外结果。
9. Practical mitigation是否有必要。
10. 是否足够支撑Future Internet：明确选择 Yes / Almost, missing X / No, reason，不保证录用。
11. 唯一推荐的journal contribution。
12. 最小充分图表集合。
13. 仅真正必要的缺失实验。
14. 下一阶段建议。

只修改JournalArticle。旧CA仓库若在目标机器存在，保持只读。提交前运行 `scripts/check_public.py` 审查staged内容，禁止公开私有材料、凭证、个人路径或依赖目录。完成里程碑自主commit/push。当前不写完整论文或引入复杂优化算法。

## 可直接给主机 Codex 的指令

> 请完整阅读 HANDOFF_TO_DESKTOP.md、CURRENT_STATUS.md 和 docs/FORMAL_EXPERIMENT_PROTOCOL.md，然后在这台主机配置环境、核对断点并继续第二阶段研究。笔记本已暂停，不要在笔记本恢复。沿用冻结JB1和已保存共同grid，不重跑历史代码考古，不重复已完成点。完成正式实验、机制解释与14节FORMAL_EVIDENCE_REPORT.md；普通研究决策自行处理。
