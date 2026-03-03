'use client';

import { useEffect, useRef, useCallback, useState } from 'react';

function getApiBase(): string {
  if (typeof window === 'undefined') return '/api/v1';
  const url = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (url && (url.startsWith('http://') || url.startsWith('https://'))) return `${url.replace(/\/$/, '')}/api/v1`;
  return '/api/v1';
}
const API_BASE = getApiBase();

type ChartCandle = { time: string; open: number; high: number; low: number; close: number };
type ChartData = {
  symbol: string;
  candles: ChartCandle[];
  cpr_pivot: number | null;
  cpr_bottom: number | null;
  cpr_top: number | null;
  prev_day_high: number | null;
  prev_day_low: number | null;
  range_5m_low: number | null;
  range_5m_high: number | null;
  range_15m_low: number | null;
  range_15m_high: number | null;
};

type ChartStatus = 'loading' | 'loaded' | 'error' | 'no-data';

type ExtendedContextProp = {
  chart_candles?: { time: string; open: number; high: number; low: number; close: number }[] | null;
  cpr_pivot?: number | null;
  cpr_bottom?: number | null;
  cpr_top?: number | null;
  prev_day_high?: number | null;
  prev_day_low?: number | null;
  range_5m_low?: number | null;
  range_5m_high?: number | null;
  range_15m_low?: number | null;
  range_15m_high?: number | null;
} | null;

function chartDataFromExtended(ext: ExtendedContextProp, symbol: string): ChartData | null {
  if (!ext?.chart_candles?.length) return null;
  return {
    symbol,
    candles: ext.chart_candles,
    cpr_pivot: ext.cpr_pivot ?? null,
    cpr_bottom: ext.cpr_bottom ?? null,
    cpr_top: ext.cpr_top ?? null,
    prev_day_high: ext.prev_day_high ?? null,
    prev_day_low: ext.prev_day_low ?? null,
    range_5m_low: ext.range_5m_low ?? null,
    range_5m_high: ext.range_5m_high ?? null,
    range_15m_low: ext.range_15m_low ?? null,
    range_15m_high: ext.range_15m_high ?? null,
  };
}

export default function Chart5m({ symbol, extendedContext = null }: { symbol: 'NIFTY' | 'SENSEX'; extendedContext?: ExtendedContextProp }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<{ remove: () => void; applyOptions: (o: { width: number }) => void } | null>(null);
  const cleanupRef = useRef<(() => void) | null>(null);
  const retriedRef = useRef(false);
  const [status, setStatus] = useState<ChartStatus>('loading');
  const [dataAsOf, setDataAsOf] = useState<string | null>(null);

  // lightweight-charts v5: intraday data must use UTCTimestamp (seconds). Backend sends "YYYY-MM-DDTHH:mm" (IST).
  type UTCTimestamp = import('lightweight-charts').UTCTimestamp;
  const timeToUTC = useCallback((timeStr: string): UTCTimestamp => {
    const withTz = timeStr.includes('T') ? `${timeStr}+05:30` : timeStr;
    return Math.floor(new Date(withTz).getTime() / 1000) as UTCTimestamp;
  }, []);

  const renderChart = useCallback(async (data: ChartData) => {
    if (!containerRef.current) return;
    const { createChart, CandlestickSeries, LineSeries } = await import('lightweight-charts');
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }
    const chart = createChart(containerRef.current, {
      layout: { background: { type: 'solid' as unknown as import('lightweight-charts').ColorType, color: 'var(--bg-page)' }, textColor: 'var(--text-secondary)' },
      grid: { vertLines: { color: 'var(--border)' }, horzLines: { color: 'var(--border)' } },
      width: containerRef.current.clientWidth,
      height: 380,
      timeScale: { timeVisible: true, secondsVisible: false },
      rightPriceScale: { borderColor: 'var(--border)' },
    });
    chartRef.current = chart;

    const candlesWithUTC = data.candles.map((c) => ({
      time: timeToUTC(c.time),
      open: c.open,
      high: c.high,
      low: c.low,
      close: c.close,
    }));

    const candlestickSeries = chart.addSeries(CandlestickSeries, {
      upColor: 'var(--positive)',
      downColor: 'var(--negative)',
      borderVisible: true,
      wickUpColor: 'var(--positive)',
      wickDownColor: 'var(--negative)',
    });
    candlestickSeries.setData(candlesWithUTC);
    setDataAsOf(data.candles[data.candles.length - 1].time);

    const firstTime = timeToUTC(data.candles[0].time);
    const lastTime = timeToUTC(data.candles[data.candles.length - 1].time);

    const lineData = (value: number) => [
      { time: firstTime, value },
      { time: lastTime, value },
    ];

    if (data.cpr_top != null) {
      const s = chart.addSeries(LineSeries, { color: 'var(--positive)', lineWidth: 2, title: 'CPR Top' });
      s.setData(lineData(data.cpr_top));
    }
    if (data.cpr_pivot != null) {
      const s = chart.addSeries(LineSeries, { color: 'var(--text-primary)', lineWidth: 1, title: 'CPR Pivot' });
      s.setData(lineData(data.cpr_pivot));
    }
    if (data.cpr_bottom != null) {
      const s = chart.addSeries(LineSeries, { color: 'var(--negative)', lineWidth: 2, title: 'CPR Bottom' });
      s.setData(lineData(data.cpr_bottom));
    }
    if (data.prev_day_high != null) {
      const s = chart.addSeries(LineSeries, { color: 'rgba(34, 197, 94, 0.7)', lineWidth: 1, lineStyle: 2, title: 'Prev Day High' });
      s.setData(lineData(data.prev_day_high));
    }
    if (data.prev_day_low != null) {
      const s = chart.addSeries(LineSeries, { color: 'rgba(239, 68, 68, 0.7)', lineWidth: 1, lineStyle: 2, title: 'Prev Day Low' });
      s.setData(lineData(data.prev_day_low));
    }
    if (data.range_5m_low != null) {
      const s = chart.addSeries(LineSeries, { color: 'rgba(250, 204, 21, 0.8)', lineWidth: 1, lineStyle: 2, title: 'Today 5m Low' });
      s.setData(lineData(data.range_5m_low));
    }
    if (data.range_5m_high != null) {
      const s = chart.addSeries(LineSeries, { color: 'rgba(250, 204, 21, 0.8)', lineWidth: 1, lineStyle: 2, title: 'Today 5m High' });
      s.setData(lineData(data.range_5m_high));
    }
    if (data.range_15m_low != null) {
      const s = chart.addSeries(LineSeries, { color: 'rgba(59, 130, 246, 0.7)', lineWidth: 1, lineStyle: 2, title: 'Today 15m Low' });
      s.setData(lineData(data.range_15m_low));
    }
    if (data.range_15m_high != null) {
      const s = chart.addSeries(LineSeries, { color: 'rgba(59, 130, 246, 0.7)', lineWidth: 1, lineStyle: 2, title: 'Today 15m High' });
      s.setData(lineData(data.range_15m_high));
    }

    chart.timeScale().fitContent();
    // Extend time scale to "now" so the chart shows today's date when last candle is from an earlier day
    const nowUTC = Math.floor(Date.now() / 1000) as UTCTimestamp;
    if (nowUTC > lastTime) {
      try {
        chart.timeScale().setVisibleRange({ from: firstTime, to: nowUTC });
      } catch {
        // ignore if range API fails
      }
    }
    const handleResize = () => {
      if (containerRef.current && chartRef.current) chartRef.current.applyOptions({ width: containerRef.current.clientWidth });
    };
    window.addEventListener('resize', handleResize);
    cleanupRef.current = () => window.removeEventListener('resize', handleResize);
    setStatus('loaded');
  }, [timeToUTC]);

  const initChart = useCallback(async () => {
    if (!containerRef.current) return;
    setStatus('loading');
    const fromExtended = chartDataFromExtended(extendedContext, symbol);
    if (fromExtended) {
      retriedRef.current = false;
      await renderChart(fromExtended);
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/market/chart/${symbol}`, { signal: AbortSignal.timeout(35000) });
      if (!res.ok) {
        setStatus('error');
        if (!retriedRef.current) {
          retriedRef.current = true;
          setTimeout(() => initChart(), 3000);
        }
        return;
      }
      const data: ChartData = await res.json();
      if (!data.candles || data.candles.length === 0) {
        setStatus('no-data');
        if (!retriedRef.current) {
          retriedRef.current = true;
          setTimeout(() => initChart(), 3000);
        }
        return;
      }
      retriedRef.current = false;
      await renderChart(data);
    } catch {
      setStatus('error');
      if (!retriedRef.current) {
        retriedRef.current = true;
        setTimeout(() => initChart(), 3000);
      }
    }
  }, [symbol, extendedContext, renderChart]);

  useEffect(() => {
    retriedRef.current = false;
    initChart();
    return () => {
      cleanupRef.current?.();
      cleanupRef.current = null;
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [initChart]);

  return (
    <div style={{ marginTop: '1rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '0.5rem' }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          5m candles (yesterday → today) • CPR, Prev day H/L, Today 5m & 15m opening range
        </span>
        {dataAsOf && status === 'loaded' && (
          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            Data as of {dataAsOf.replace('T', ' ')}
          </span>
        )}
        {status === 'loaded' && (
          <button
            type="button"
            onClick={() => { setDataAsOf(null); retriedRef.current = false; initChart(); }}
            style={{ marginLeft: 'auto', padding: '0.25rem 0.5rem', fontSize: '0.75rem', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 4, color: 'var(--text-secondary)', cursor: 'pointer' }}
          >
            Refresh chart
          </button>
        )}
      </div>
      <p style={{ fontSize: '0.7rem', color: 'var(--text-muted)', margin: '0 0 0.5rem 0' }}>
        Chart updates with market data every 15s. Today&apos;s candles appear when available from the feed.
      </p>
      {status === 'loading' && (
        <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)', background: 'var(--bg-page)', borderRadius: 'var(--radius)', minHeight: 200 }}>
          Loading chart…
        </div>
      )}
      {(status === 'error' || status === 'no-data') && (
        <div style={{ padding: '1rem', background: status === 'error' ? 'rgba(218,54,51,0.1)' : 'var(--bg-page)', borderRadius: 'var(--radius)', fontSize: '0.875rem', color: status === 'error' ? 'var(--negative)' : 'var(--text-muted)' }}>
          {status === 'error'
            ? 'Chart could not load. Backend may be busy or Upstox timed out.'
            : 'No 5m candle data for this period (market may be closed, no data yet, or Upstox was slow).'}
          <button type="button" onClick={() => { retriedRef.current = false; initChart(); }} style={{ marginLeft: '0.75rem', padding: '0.35rem 0.75rem', background: 'var(--accent)', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 600 }}>
            Try again
          </button>
        </div>
      )}
      <div ref={containerRef} style={{ width: '100%', minHeight: status === 'loaded' ? 380 : 0, display: status === 'loaded' ? 'block' : 'none' }} />
    </div>
  );
}
