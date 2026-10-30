"""Instrumented, checked workload; loaded only by the benchmark simulator."""
from dataclasses import asdict
import hashlib
import json
import os
import resource
import time
import cocotb
from cocotb.triggers import RisingEdge, ReadOnly
from cocotb.utils import get_sim_time
from bfm import StreamConfig, captured_signals, send, sink, reset, drain, data_sequence
from evidence import session
from verification_evidence.model import dump
from verification_evidence.core import summarize


@cocotb.test()
async def benchmark(dut):
    entered = time.perf_counter()
    directory, model = session()
    tx, rx = StreamConfig.bind(dut, 'tx', 'tx'), StreamConfig.bind(dut, 'rx', 'rx')
    variant = os.environ['BENCH_VARIANT']
    metrics = dict(monitor_seconds=0., checking_seconds=0., monitor_wakeups=0)
    names = ('reset', 'valid', 'ready', 'data')
    handles = [[getattr(dut, 's_reset' if n == 'reset' else f's_{c.channel}_{n}') for n in names] for c in (tx, rx)]

    async def monitor():
        while True:
            await RisingEdge(tx.clock)
            await ReadOnly()
            started = time.perf_counter()
            tick = int(get_sim_time(units='ps'))
            if variant == 'cached':
                samples = [dict(zip(names, [str(h.value).lower() for h in group])) for group in handles]
            else:
                samples = [captured_signals(c) for c in (tx, rx)]
            metrics['monitor_seconds'] += time.perf_counter() - started
            metrics['monitor_wakeups'] += 1
            started = time.perf_counter()
            for channel, signals in zip(('tx', 'rx'), samples):
                model.sample(channel, tick, signals)
            metrics['checking_seconds'] += time.perf_counter() - started

    values = data_sequence(count=int(os.environ['BENCH_TRANSACTIONS']))
    (directory / 'stimulus.json').write_text(json.dumps(values))
    tasks = [cocotb.start_soon(monitor()), cocotb.start_soon(sink(rx))]
    error = None
    start = time.perf_counter()
    try:
        await reset(tx)
        for value in values:
            await send(tx, value)
        await drain(tx)
    except Exception as exc:
        error = str(exc)
    finally:
        metrics['loop_seconds'] = time.perf_counter() - start
        for task in tasks:
            try:
                if task.done():
                    task.result()
            except Exception as exc:
                error = str(exc)
            task.kill()
    lanes = int(os.environ['BENCH_LANES'])
    expected = (int(dut.load_steps.value) * lanes * (lanes + 1) // 2) & 0xffffffff
    metrics['rtl_load_checked'] = int(dut.load_checksum.value) == expected
    if not metrics['rtl_load_checked']:
        error = 'synthetic RTL checksum mismatch'
    start = time.perf_counter()
    bundle = model.finish(int(get_sim_time(units='ps')), error)
    metrics['finalize_seconds'] = time.perf_counter() - start
    start = time.perf_counter()
    result = summarize(bundle)
    metrics['summary_seconds'] = time.perf_counter() - start
    start = time.perf_counter()
    dump(bundle, directory / 'bundle.json')
    metrics['write_seconds'] = time.perf_counter() - start
    metrics['gate'] = result['gate']
    metrics['failed'] = sorted({c.obligation_id for c in bundle.runs[0].checks if c.outcome == 'fail'})
    run = bundle.runs[0]
    semantic = {k: [asdict(v) for v in getattr(run, k)] for k in ('events', 'checks', 'coverage')}
    for event in semantic['events']:
        event.pop('run_id')
    semantic['finalization'] = asdict(run.finalization)
    metrics['semantic_sha256'] = hashlib.sha256(json.dumps(semantic, sort_keys=True).encode()).hexdigest()
    metrics['stimulus_sha256'] = hashlib.sha256(json.dumps(values).encode()).hexdigest()
    metrics['record_counts'] = run.finalization.record_counts
    metrics['peak_rss_kib'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    metrics['evidence_bytes'] = (directory / 'bundle.json').stat().st_size
    metrics['body_seconds'] = time.perf_counter() - entered
    metrics['scheduler_driver_rtl_residual_seconds'] = (metrics['loop_seconds'] - metrics['monitor_seconds'] - metrics['checking_seconds'])
    (directory / 'metrics.json').write_text(json.dumps(metrics, indent=2))
    assert result['gate'] == 'pass', 'BENCH_CHECK_FAILURE: ' + str(result['requirements'])
