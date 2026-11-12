<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { createChart, CandlestickSeries, HistogramSeries } from 'lightweight-charts'
const packet=ref(null), connected=ref(false), selected=ref('AAPL'), clock=ref(Date.now()), chartEl=ref(null), error=ref('')
let ws, chart, price, volume, retry, timer, observer, disposed=false, lastKey='', priorBars=0
const bars=computed(()=>packet.value?.candles||[])
const last=computed(()=>bars.value.at(-1))
const feed=computed(()=>connected.value ? packet.value?.feed?.state||'connecting' : 'disconnected')
const mode=computed(()=>packet.value?.mode||'live')
const money=n=>n==null?'—':n.toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})
const age=computed(()=>packet.value?.source_ms == null?'Awaiting source':`${Math.max(0,(clock.value-packet.value.source_ms)/1000).toFixed(1)}s old`)
const stamp=ms=>ms?new Date(ms).toISOString().slice(11,23)+' UTC':'—'
function command(action,extra={}) { if(ws?.readyState===1) ws.send(JSON.stringify({action,...extra})) }
function choose() {lastKey='';command('select',{symbol:selected.value})}
function render() {
  if(!chart)return
  const key=JSON.stringify(bars.value)
  if(key===lastKey)return
  const reset=lastKey==='' || bars.value.length < (price.data()?.length||0)
  lastKey=key
  price.setData(bars.value.map(b=>({time:b.time,open:b.open,high:b.high,low:b.low,close:b.close})))
  volume.setData(bars.value.map(b=>({time:b.time,value:b.volume,color:b.close>=b.open?'#679f9170':'#cf867670'})))
  if(reset || (bars.value.length!==priorBars && bars.value.length<60)) {
    chart.timeScale().setVisibleLogicalRange({from:Math.max(0,bars.value.length-60)-2,to:Math.max(30,bars.value.length)+2})
  }
  priorBars=bars.value.length
}
function connect(){
  if(disposed)return
  ws=new WebSocket(`${location.protocol==='https:'?'wss':'ws'}://${location.host}/ws`)
  ws.onopen=()=>{connected.value=true;error.value='';command('select',{symbol:selected.value})}
  ws.onmessage=e=>{try{packet.value=JSON.parse(e.data);render()}catch{error.value='Unable to read server update'}}
  ws.onclose=()=>{connected.value=false;if(!disposed)retry=setTimeout(connect,2000)}
  ws.onerror=()=>{error.value='Backend connection unavailable; reconnecting'}
}
onMounted(()=>{
  chart=createChart(chartEl.value,{autoSize:true,height:440,layout:{background:{color:'#151d19'},textColor:'#8d9d93',attributionLogo:true},grid:{vertLines:{color:'#243028'},horzLines:{color:'#243028'}},rightPriceScale:{borderColor:'#334037'},timeScale:{timeVisible:true,secondsVisible:true,borderColor:'#334037'},localization:{locale:'en-US',timeFormatter:t=>new Date(t*1000).toISOString().slice(11,19)+' UTC'}})
  price=chart.addSeries(CandlestickSeries,{upColor:'#89c6ab',downColor:'#d99b86',wickUpColor:'#89c6ab',wickDownColor:'#d99b86',borderVisible:false,priceFormat:{type:'price',precision:2,minMove:.01}})
  volume=chart.addSeries(HistogramSeries,{priceFormat:{type:'volume'},priceScaleId:''})
  price.priceScale().applyOptions({scaleMargins:{top:.12,bottom:.27}})
  volume.priceScale().applyOptions({scaleMargins:{top:.82,bottom:0}})
  timer=setInterval(()=>clock.value=Date.now(),100)
  connect()
})
onBeforeUnmount(()=>{disposed=true;clearTimeout(retry);clearInterval(timer);ws?.close();observer?.disconnect();chart?.remove()})
</script>

<template>
  <div class="workspace">
    <header><a class="brand" href="/" aria-label="Market Desk home"><span class="mark">m<span>↗</span></span> MARKET DESK</a><div class="course">IST 402 <span>/</span> WORKSTATION 01</div><span class="local"><i></i> LOCAL SESSION</span></header>
    <main>
      <div class="eyebrow">OBSERVE. RECORD. REPLAY.</div>
      <div class="heading"><div><h1>A clear view of the market.</h1><p>Live observations, with a record you can trace.</p></div><div class="session-label">PART 4.1 <span>Market data & dashboard</span></div></div>
      <section class="toolbar" aria-label="Chart controls">
        <div class="instrument"><label for="symbol">INSTRUMENT</label><select id="symbol" v-model="selected" @change="choose"><option>AAPL</option><option>BTC-USD</option></select><span>{{ selected==='AAPL'?'Apple Inc. · NASDAQ':'Bitcoin / US Dollar' }}</span></div>
        <div class="interval">5s <span>CANDLES · UTC</span></div>
        <div class="segmented"><button :class="{active:mode==='live'}" @click="command('live');lastKey=''" :disabled="!connected">Live feed</button><button :class="{active:mode==='replay'}" @click="command('replay');lastKey=''" :disabled="!connected || !packet?.stats?.receipts">Replay record</button></div>
      </section>
      <div v-if="mode==='replay'" class="banner replay" role="status">RECORDED REPLAY <span>Receipt {{ packet?.cursor }} / {{ packet?.replay_end }} · {{ packet?.replay_finished?'Finished — return to Live feed to resume':'Accelerated receipt-order playback' }} · {{ stamp(packet?.replay_clock_ms) }}</span></div>
      <div v-if="['unavailable','stale','disconnected'].includes(feed)" class="banner warning" role="alert">{{ feed.toUpperCase() }} <span>{{ error || packet?.feed?.detail || 'Backend disconnected; retrying automatically. Stored chart remains visible.' }}. Displayed data may be old.</span></div>
      <div class="desk-grid">
        <section class="chart-card" aria-label="Market candlestick and volume chart">
          <div class="chart-heading"><div><span class="ticker">{{selected}}</span><span class="subtle">/ USD</span><div class="quote">{{money(last?.close)}}<small>LAST OBSERVED PRICE</small></div></div><div class="feed-badge" :class="feed"><i></i>{{mode==='replay'?'RECORDED':feed.toUpperCase()}}</div></div>
          <div class="ohlc"><span>O <b>{{money(last?.open)}}</b></span><span>H <b>{{money(last?.high)}}</b></span><span>L <b>{{money(last?.low)}}</b></span><span>C <b>{{money(last?.close)}}</b></span><span class="candle-state">{{last ? (last.complete?'Completed interval':'Forming · provisional'):'Waiting for observations'}}</span></div>
          <div class="chart-wrap"><div ref="chartEl" class="chart"></div><div v-if="!bars.length" class="empty"><strong>{{mode==='replay'?'Starting recorded playback':'Waiting for Yahoo Finance'}}</strong><span>New observations will appear here. No generated prices.</span></div></div>
          <div class="chart-foot"><span><i class="square"></i> PRICE <i class="square volume"></i> OBSERVED VOLUME DELTA</span><button @click="chart.timeScale().fitContent()">Fit chart ↗</button></div>
        </section>
        <aside class="record-card"><div class="card-label">THE DATA TRAIL <span>↗</span></div><h2>Every update,<br>accounted for.</h2><p>Source time and receipt time stay separate. The record stays on disk.</p><dl><div><dt>Provider</dt><dd>Yahoo Finance</dd></div><div><dt>Source age <span>(wall clock)</span></dt><dd :class="{aged:packet?.source_ms && clock-packet.source_ms>20000}">{{age}}</dd></div><div><dt>Latest source time</dt><dd>{{stamp(packet?.source_ms)}}</dd></div><div><dt>Latest receipt time</dt><dd>{{stamp(packet?.receipt_ms)}}</dd></div><div><dt>Storage</dt><dd>SQLite · persistent</dd></div></dl><div class="stats"><div><b>{{packet?.stats?.receipts||0}}</b><span>RECEIPTS</span></div><div><b>{{packet?.stats?.revisions||0}}</b><span>VERSIONS</span></div></div><div class="feed-control"><button @click="command(feed==='unavailable'?'reconnect':'disconnect')" :disabled="!connected || packet?.feed?.enabled===false">{{feed==='unavailable'?'Reconnect Yahoo feed':'Test feed disconnect'}} <span>↗</span></button><small>{{packet?.feed?.enabled===false?'Live provider disabled for offline replay.':'Deliberately disconnects the source; saved observations remain available.'}}</small></div></aside>
      </div>
      <section class="journal"><div class="journal-top"><div><span class="eyebrow">PERSISTENCE / RECEIPT JOURNAL</span><h2>Follow the observation.</h2></div><span>{{packet?.stats?.duplicates||0}} duplicate receipts · {{packet?.stats?.candle_versions||0}} candle versions <small>Totals include all instruments and live recording during replay.</small></span></div><div class="table-scroll"><table><thead><tr><th>RECEIPT / REVISION</th><th>SOURCE TIME · UTC</th><th>RECEIVED · UTC</th><th>PRICE</th><th>RESULT</th></tr></thead><tbody><tr v-for="row in packet?.recent||[]" :key="row.receipt_id"><td>#{{row.receipt_id}} <span>/ {{row.revision_id}} · v{{row.version}}</span></td><td>{{stamp(row.source_ms)}}</td><td>{{stamp(row.receipt_ms)}}</td><td>{{money(row.price)}}</td><td><span class="result">{{row.disposition}}</span></td></tr><tr v-if="!packet?.recent?.length"><td colspan="5" class="no-records">Waiting for recorded observations.</td></tr></tbody></table></div></section>
      <footer><span>Local market observation · no trading or orders</span><span>Volume is the nonnegative change in Yahoo’s cumulative daily volume, observed between updates; gaps are not reconstructed.</span><a href="https://www.tradingview.com/" target="_blank" rel="noreferrer">Charts by TradingView ↗</a></footer>
    </main>
  </div>
</template>
