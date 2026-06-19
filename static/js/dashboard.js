// Munters Production Planning Dashboard - JS
const PLOTLY_LIGHT = {paper_bgcolor:'rgba(0,0,0,0)',plot_bgcolor:'rgba(0,0,0,0)',font:{color:'#f8fafc',family:'Inter'},margin:{l:50,r:20,t:40,b:50},colorway:['#3b82f6','#06b6d4','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899','#14b8a6']};

const CLASS_PALETTE = [
  '#6366f1','#06b6d4','#10b981','#f59e0b','#ef4444',
  '#8b5cf6','#ec4899','#14b8a6','#f97316','#3b82f6',
  '#a855f7','#22c55e','#e11d48','#0ea5e9','#d946ef',
  '#84cc16','#f43f5e','#7c3aed','#059669','#fb923c',
  '#4f46e5','#0891b2','#16a34a','#ca8a04','#dc2626',
  '#7c3aed','#db2777','#0d9488','#ea580c','#2563eb',
  '#9333ea','#15803d','#be123c','#0284c7','#c026d3',
  '#65a30d','#e11d48',
];

// Navigation
document.querySelectorAll('.nav-links li').forEach(li=>{
  li.addEventListener('click',()=>{
    document.querySelectorAll('.nav-links li').forEach(x=>x.classList.remove('active'));
    document.querySelectorAll('.section').forEach(x=>x.classList.remove('active'));
    li.classList.add('active');
    const sec=li.dataset.section;
    document.getElementById('section-'+sec).classList.add('active');
    const titles={overview:'Production Overview',classification:'Panel Classification',schedule:'Machine Schedules',gantt:'Gantt Chart',ml:'ML Model Analysis',simulation:'Box Simulation'};
    document.getElementById('page-title').textContent=titles[sec]||'Dashboard';
  });
});

// Time
function updateTime(){const d=new Date();const t=d.toLocaleTimeString('en-IN',{hour:'2-digit',minute:'2-digit',second:'2-digit'});document.getElementById('current-time').textContent=t;document.getElementById('header-time').textContent=d.toLocaleDateString('en-IN',{day:'2-digit',month:'short',year:'numeric'})+' '+t;}
setInterval(updateTime,1000);updateTime();

// Fetch helper
async function api(url){const r=await fetch(url);return r.json();}

// ══════════════════════════════════════════════════════════
// TOAST NOTIFICATION
// ══════════════════════════════════════════════════════════
function showToast(message, duration = 3000) {
  let toast = document.getElementById('gantt-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'gantt-toast';
    toast.className = 'gantt-toast';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), duration);
}

// ══════════════════════════════════════════════════════════
// CLASS COLOR MAP (persistent across re-renders)
// ══════════════════════════════════════════════════════════
let globalClassColorMap = {};

function buildClassColorMap(classes) {
  const sorted = [...classes].sort();
  sorted.forEach((cls, i) => {
    if (!globalClassColorMap[cls]) {
      globalClassColorMap[cls] = CLASS_PALETTE[Object.keys(globalClassColorMap).length % CLASS_PALETTE.length];
    }
  });
}

// ══════════════════════════════════════════════════════════
// GANTT TOOLTIP
// ══════════════════════════════════════════════════════════
let tooltipEl = null;

function ensureTooltip() {
  if (!tooltipEl) {
    tooltipEl = document.createElement('div');
    tooltipEl.className = 'gantt-tooltip';
    document.body.appendChild(tooltipEl);
  }
  return tooltipEl;
}

function showGanttTooltip(e, data, color) {
  const tt = ensureTooltip();
  const isTC = data.type === 'tool_change';
  tt.innerHTML = `
    <div class="tt-title"><div class="tt-dot" style="background:${color}"></div>${isTC ? '🔧 Tool Change' : data.class}</div>
    <div class="tt-row"><span>Machine</span><span>${data.machine}</span></div>
    <div class="tt-row"><span>Time</span><span>${minutesToTime(data.start)} → ${minutesToTime(data.end)}</span></div>
    <div class="tt-row"><span>Duration</span><span>${data.duration.toFixed(1)} min</span></div>
    ${!isTC ? `<div class="tt-row"><span>FG Code</span><span>${data.fg_code}</span></div>` : ''}
    ${!isTC ? `<div class="tt-row"><span>Status</span><span style="color:${data.status==='Completed'?'#10b981':'#f59e0b'}">${data.status}</span></div>` : ''}
  `;
  tt.classList.add('visible');
  positionTooltip(e);
}

function positionTooltip(e) {
  if (!tooltipEl) return;
  const x = e.clientX + 14;
  const y = e.clientY - 10;
  tooltipEl.style.left = Math.min(x, window.innerWidth - 300) + 'px';
  tooltipEl.style.top = Math.min(y, window.innerHeight - 200) + 'px';
}

function hideGanttTooltip() {
  if (tooltipEl) tooltipEl.classList.remove('visible');
}

function minutesToTime(min) {
  const h = Math.floor(min / 60) + 10; // shift starts at 10:00
  const m = Math.round(min % 60);
  return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`;
}

// ══════════════════════════════════════════════════════════
// CUSTOM GANTT CHART
// ══════════════════════════════════════════════════════════
async function loadGantt() {
  const [ganttData, classInfo] = await Promise.all([
    api('/api/charts/gantt'),
    api('/api/gantt_classes'),
  ]);

  const machines = [...new Set(ganttData.map(d => d.machine))].sort();
  const allClasses = [...new Set(ganttData.filter(d => d.type === 'production').map(d => d.class))];
  buildClassColorMap(allClasses);

  // Find max time for scaling
  const maxEnd = Math.max(...ganttData.map(d => d.end), 405);
  const totalSpan = Math.ceil(maxEnd / 30) * 30; // round up to 30 min

  // Stats
  const totalPanels = ganttData.filter(d => d.type === 'production').length;
  document.getElementById('gantt-stat-panels').textContent = `${totalPanels} panels`;
  document.getElementById('gantt-stat-classes').textContent = `${allClasses.length} classes`;

  // ── Build custom Gantt HTML ──
  const container = document.getElementById('gantt-chart-custom');
  let html = '<div class="gantt-container">';

  // Time axis
  html += '<div class="gantt-time-axis">';
  for (let t = 0; t <= totalSpan; t += 30) {
    const pct = (t / totalSpan) * 100;
    html += `<div class="gantt-time-mark" style="left:${pct}%">${minutesToTime(t)}</div>`;
  }
  html += '</div>';

  // Machine rows
  machines.forEach(machine => {
    const machineEntries = ganttData.filter(d => d.machine === machine);
    html += `<div class="gantt-row">`;
    html += `<div class="gantt-machine-label"><span class="gantt-machine-dot"></span>${machine}</div>`;
    html += `<div class="gantt-bars-track">`;

    // Grid lines
    for (let t = 30; t < totalSpan; t += 30) {
      const pct = (t / totalSpan) * 100;
      html += `<div class="gantt-gridline" style="left:${pct}%"></div>`;
    }

    // Bars
    machineEntries.forEach((entry, idx) => {
      const left = (entry.start / totalSpan) * 100;
      const width = ((entry.end - entry.start) / totalSpan) * 100;
      const isTC = entry.type === 'tool_change';
      const color = isTC ? '#f59e0b' : (globalClassColorMap[entry.class] || '#6366f1');
      const statusCls = entry.status === 'Completed' ? ' status-completed' : '';
      const label = isTC ? 'TC' : (width > 3 ? entry.class.split('_').slice(1).join('_') : '');
      const bgStyle = isTC ? '' : `background:${color};`;

      const cursorStyle = isTC ? '' : 'cursor: pointer;';
      html += `<div class="gantt-bar type-${entry.type}${statusCls}" 
                    style="left:${left}%;width:${width}%;${bgStyle}${cursorStyle}" 
                    data-idx="${idx}" data-machine="${machine}"
                    onmouseenter="showGanttTooltip(event, ${escapeAttr(JSON.stringify(entry))}, '${color}')"
                    onmousemove="positionTooltip(event)"
                    onmouseleave="hideGanttTooltip()"
                    ${!isTC ? `onclick="markClassDoneAndSync('${entry.class}')"` : ''}>
                <span class="bar-text">${label}</span>
              </div>`;
    });

    html += '</div></div>';
  });

  html += '</div>';
  container.innerHTML = html;

  // ── Build class control panel ──
  renderClassControls(classInfo);
}

function escapeAttr(str) {
  return str.replace(/&/g,'&amp;').replace(/'/g,'&#39;').replace(/"/g,'&quot;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// ══════════════════════════════════════════════════════════
// CLASS CONTROLS PANEL
// ══════════════════════════════════════════════════════════
function renderClassControls(classInfo) {
  const container = document.getElementById('gantt-class-controls');
  let html = '<div class="class-controls-grid">';

  classInfo.forEach(cls => {
    const color = globalClassColorMap[cls.class_name] || '#6366f1';
    const isDone = cls.is_completed;
    const badgeCls = cls.panel_type === 'Thermal' ? 'thermal' : 'non-thermal';

    html += `
      <div class="class-control-item ${isDone ? 'completed' : ''}" data-class="${cls.class_name}">
        <div class="cci-color" style="background:${color}"></div>
        <div class="cci-info">
          <div class="cci-name" title="${cls.class_name}">${cls.class_name}</div>
          <div class="cci-meta">
            <span>${cls.total_panels} panels</span>
            <span>${cls.total_time_min} min</span>
            <span class="cci-badge ${badgeCls}">${cls.panel_type}</span>
          </div>
        </div>
        <div class="cci-actions">
          <button class="btn-class-done ${isDone ? 'done' : ''}" 
                  onclick="markClassDone('${cls.class_name}', this)" 
                  ${isDone ? 'disabled' : ''}>
            ${isDone ? '✓ Done' : '☐ Mark Done'}
          </button>
          <button class="btn-class-excel" onclick="downloadClassExcel('${cls.class_name}')">
            📥 Excel
          </button>
        </div>
      </div>
    `;
  });

  html += '</div>';
  container.innerHTML = html;
}

// ══════════════════════════════════════════════════════════
// MARK CLASS COMPLETED
// ══════════════════════════════════════════════════════════
async function markClassDone(className, btn) {
  btn.innerHTML = '⏳';
  btn.classList.add('loading');

  try {
    const res = await fetch('/api/mark_class_completed', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ class_name: className }),
    });
    const data = await res.json();

    if (data.success) {
      btn.innerHTML = '✓ Done';
      btn.classList.remove('loading');
      btn.classList.add('done');
      btn.disabled = true;

      // Update the parent card
      const item = btn.closest('.class-control-item');
      if (item) item.classList.add('completed');

      // Dim all Gantt bars of this class
      document.querySelectorAll('.gantt-bar.type-production').forEach(bar => {
        // Re-fetch the data to find matching bars
        // We use the bar text and class color to identify
      });

      showToast(`✅ ${data.count} panels of "${className}" marked completed`);

      // Refresh Gantt to update bar statuses
      await loadGantt();
      // Refresh Schedule
      await loadSchedule();
    } else {
      btn.innerHTML = '✗ Failed';
      btn.classList.remove('loading');
      setTimeout(() => { btn.innerHTML = '☐ Mark Done'; }, 2000);
    }
  } catch (err) {
    btn.innerHTML = '✗ Error';
    btn.classList.remove('loading');
    setTimeout(() => { btn.innerHTML = '☐ Mark Done'; }, 2000);
  }
}

// ══════════════════════════════════════════════════════════
// MARK CLASS DONE FROM GANTT BAR AND SYNC TO GITHUB
// ══════════════════════════════════════════════════════════
window.markClassDoneAndSync = async function(className) {
  if (!confirm(`Mark all panels in class ${className} as done and sync to GitHub?`)) return;
  
  showToast(`⏳ Marking ${className} as done and syncing to GitHub...`);
  
  try {
    const res = await fetch('/api/mark_class_completed_and_sync', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ class_name: className }),
    });
    const data = await res.json();
    
    if (data.success) {
      showToast(`✅ ${className} marked done. Sync: ${data.git_msg}`);
      await loadGantt();
      await loadSchedule();
      await loadKPIs();
      await loadClassTable();
    } else {
      showToast(`❌ Failed: ${data.message}`);
    }
  } catch (err) {
    showToast(`❌ Error: ${err.message}`);
  }
};

// ══════════════════════════════════════════════════════════
// DOWNLOAD CLASS EXCEL
// ══════════════════════════════════════════════════════════
function downloadClassExcel(className) {
  const link = document.createElement('a');
  link.href = `/api/download_class_excel/${encodeURIComponent(className)}`;
  link.download = `${className}_panels.xlsx`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast(`📥 Downloading Excel for "${className}"`);
}

// ══════════════════════════════════════════════════════════
// LIVE SCHEDULE: Mark individual panel done
// ══════════════════════════════════════════════════════════
window.markCompleted = async function(panelId, btn) {
  btn.innerText = '⏳';
  const res = await fetch('/api/mark_completed', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ panel_id: panelId })
  });
  const data = await res.json();
  if (data.success) {
    btn.innerHTML = '✓ Done';
    btn.classList.add('completed');
    await loadGantt();
    await loadSchedule();
  } else {
    btn.innerText = 'Failed';
  }
};

// ══════════════════════════════════════════════════════════
// REDISTRIBUTE (Reschedule)
// ══════════════════════════════════════════════════════════
document.getElementById('btn-reschedule')?.addEventListener('click', async (e) => {
  const btn = e.target;
  const originalText = btn.innerHTML;
  btn.innerHTML = '⏳ Rescheduling...';
  btn.style.opacity = '0.7';
  btn.style.pointerEvents = 'none';

  try {
    const res = await fetch('/api/reschedule', { method: 'POST' });
    const data = await res.json();

    if (data.success) {
      showToast(`🔄 Rescheduled ${data.summary.total_panels_scheduled} panels across ${data.summary.machines_used} machines`);
      await loadKPIs();
      await loadSchedule();
      await loadGantt();
      await loadCharts();
    } else {
      showToast(`⚠️ ${data.message || 'Reschedule failed'}`);
    }
  } catch (err) {
    showToast('❌ Reschedule error: ' + err.message);
  }

  btn.innerHTML = originalText;
  btn.style.opacity = '1';
  btn.style.pointerEvents = 'auto';
});


// ══════════════════════════════════════════════════════════
// LOAD KPIs
// ══════════════════════════════════════════════════════════
async function loadKPIs(){
  const d=await api('/api/kpis');
  const kpis=[
    {icon:'📦',value:d.total_orders,label:'Total Orders'},
    {icon:'🔥',value:d.thermal_panels,label:'Thermal Panels'},
    {icon:'❄️',value:d.non_thermal_panels,label:'Non-Thermal'},
    {icon:'🏷️',value:d.total_classes,label:'Classes'},
    {icon:'✅',value:d.total_scheduled,label:'Scheduled'},
    {icon:'✔️',value:d.completed_panels,label:'Completed'},
    {icon:'⏳',value:d.pending_panels,label:'Pending'},
    {icon:'🔨',value:d.total_strokes_done,label:'Strokes Done'},
    {icon:'🤖',value:d.best_r2+'%',label:'ML R² ('+d.best_model+')'},
  ];
  const g=document.getElementById('kpi-grid');
  g.innerHTML=kpis.map(k=>`<div class="kpi-card"><div class="kpi-icon">${k.icon}</div><div class="kpi-value">${k.value}</div><div class="kpi-label">${k.label}</div></div>`).join('');
}

// ══════════════════════════════════════════════════════════
// CHARTS
// ══════════════════════════════════════════════════════════
async function loadCharts(){
  // Panel Type Split
  const split=await api('/api/charts/panel_type_split');
  Plotly.newPlot('chart-panel-split',[{values:Object.values(split),labels:Object.keys(split),type:'pie',hole:.55,marker:{colors:['#ef4444','#06b6d4']},textfont:{size:13}}],{...PLOTLY_LIGHT,title:{text:'Thermal vs Non-Thermal',font:{size:15,color:'#f8fafc'}},showlegend:true,legend:{font:{size:12}}},{responsive:true});

  // Area Distribution
  const area=await api('/api/charts/area_distribution');
  Plotly.newPlot('chart-area-dist',[{x:area.thermal,type:'histogram',name:'Thermal',marker:{color:'rgba(239,68,68,0.6)'},nbinsx:30},{x:area.non_thermal,type:'histogram',name:'Non-Thermal',marker:{color:'rgba(6,182,212,0.6)'},nbinsx:30}],{...PLOTLY_LIGHT,title:{text:'Area Distribution (mm²)',font:{size:15,color:'#f8fafc'}},barmode:'overlay',xaxis:{title:'Area (mm²)',gridcolor:'rgba(255,255,255,0.05)'},yaxis:{title:'Count',gridcolor:'rgba(255,255,255,0.05)'}},{responsive:true});

  // Machine Utilization
  const util=await api('/api/charts/machine_utilization');
  const machines=Object.keys(util);
  Plotly.newPlot('chart-machine-util',[
    {x:machines,y:machines.map(m=>util[m].production),name:'Production',type:'bar',marker:{color:'#10b981'}},
    {x:machines,y:machines.map(m=>util[m].tool_change),name:'Tool Change',type:'bar',marker:{color:'#f59e0b'}},
    {x:machines,y:machines.map(m=>util[m].idle),name:'Idle',type:'bar',marker:{color:'#94a3b8'}},
  ],{...PLOTLY_LIGHT,title:{text:'Machine Time Breakdown (min)',font:{size:15,color:'#f8fafc'}},barmode:'stack',yaxis:{title:'Minutes',gridcolor:'rgba(255,255,255,0.05)'},xaxis:{gridcolor:'rgba(255,255,255,0.05)'}},{responsive:true});

  // Class Counts
  const cc=await api('/api/charts/class_counts');
  const sorted=Object.entries(cc).sort((a,b)=>b[1]-a[1]);
  Plotly.newPlot('chart-class-counts',[{x:sorted.map(s=>s[0]),y:sorted.map(s=>s[1]),type:'bar',marker:{color:sorted.map((_,i)=>`hsl(${230+i*8},70%,60%)`)}}],{...PLOTLY_LIGHT,title:{text:'Panels per Class',font:{size:15,color:'#f8fafc'}},xaxis:{tickangle:-45,tickfont:{size:9},gridcolor:'rgba(255,255,255,0.05)'},yaxis:{title:'Count',gridcolor:'rgba(255,255,255,0.05)'}},{responsive:true});
}

// ══════════════════════════════════════════════════════════
// CLASS TABLE
// ══════════════════════════════════════════════════════════
async function loadClassTable(){
  const data=await api('/api/class_distribution');
  let html='<table class="data-table"><thead><tr><th>Class</th><th>Count</th><th>Avg Area (mm²)</th><th>Avg Time (sec)</th><th>Total Time (min)</th><th>Type</th></tr></thead><tbody>';
  data.sort((a,b)=>b.panel_count-a.panel_count);
  data.forEach(r=>{
    const badge=r.class_name.startsWith('Thermal')?'<span class="thermal-badge">Thermal</span>':'<span class="non-thermal-badge">Non-Thermal</span>';
    html+=`<tr><td><strong>${r.class_name}</strong></td><td>${r.panel_count}</td><td>${r.avg_area.toLocaleString()}</td><td>${r.avg_time_sec}</td><td>${r.total_time_min}</td><td>${badge}</td></tr>`;
  });
  html+='</tbody></table>';
  document.getElementById('class-table-container').innerHTML=html;
}

// ══════════════════════════════════════════════════════════
// SCHEDULE
// ══════════════════════════════════════════════════════════
async function loadSchedule(){
  const data=await api('/api/schedule');
  const c=document.getElementById('schedule-container');
  let html='';
  for(const[machine,info]of Object.entries(data)){
    html+=`<div class="machine-schedule"><div class="machine-header"><div class="machine-name"><span class="dot"></span>${machine}</div><div class="stat-pills"><span class="stat-pill production">⚡ ${info.stats.panels_produced} panels</span><span class="stat-pill production">📊 ${info.stats.utilization_pct}%</span><span class="stat-pill tool-change">🔧 ${info.stats.tool_changes} changes</span><span class="stat-pill idle">💤 ${info.stats.idle_time.toFixed(0)} min idle</span></div></div><div class="schedule-timeline">`;
    info.schedule.forEach(e=>{
      const isProd = e.type === 'production';
      const isDone = isProd && e.status === 'Completed';
      const markBtn = isProd ? `<button class="mark-done-btn ${isDone ? 'completed' : ''}" onclick="markCompleted('${e.panel_id}', this)" ${isDone ? 'disabled' : ''}>${isDone ? '✓ Done' : '☐ Mark Done'}</button>` : '';
      const rowOpacity = isDone ? 'opacity: 0.5; filter: grayscale(1);' : '';
      html+=`<div class="timeline-entry ${e.type}" style="${rowOpacity}"><span class="timeline-time">${e.start_time} → ${e.end_time}</span><span class="timeline-class">${e.type==='tool_change'?'🔧 Tool Change':'🔨 '+e.class}</span><span class="timeline-fg">${e.fg_code}</span><span style="color:#64748b;font-size:11px;margin-right:10px">${e.duration_min.toFixed(1)} min</span>${markBtn}</div>`;
    });
    html+='</div></div>';
  }
  c.innerHTML=html;
}

// ══════════════════════════════════════════════════════════
// ML MODELS
// ══════════════════════════════════════════════════════════
async function loadML(){
  const data=await api('/api/ml_metrics');
  const c=document.getElementById('ml-comparison');
  let html='<div class="model-cards">';
  for(const[name,m]of Object.entries(data.metrics)){
    const isBest=name===data.best_model;
    const color=m.r2>.95?'#059669':m.r2>.9?'#0891b2':'#d97706';
    html+=`<div class="model-card ${isBest?'best':''}"><h4>${isBest?'⭐ ':''}${name}</h4><div class="r2-value" style="color:${color}">${(m.r2*100).toFixed(2)}%</div><div style="font-size:11px;color:#64748b;margin-top:4px">R² Score</div><div class="metric-row"><span>MAE</span><span>${m.mae.toFixed(2)}s</span></div><div class="metric-row"><span>RMSE</span><span>${m.rmse.toFixed(2)}s</span></div>${isBest?'<div style="margin-top:12px;font-size:11px;color:#059669;font-weight:600">★ BEST MODEL</div>':''}</div>`;
  }
  html+='</div>';c.innerHTML=html;

  const names=Object.keys(data.metrics);
  Plotly.newPlot('ml-r2-chart',[{x:names,y:names.map(n=>data.metrics[n].r2*100),type:'bar',marker:{color:names.map(n=>n===data.best_model?'#10b981':'#3b82f6')},text:names.map(n=>(data.metrics[n].r2*100).toFixed(2)+'%'),textposition:'outside'}],{...PLOTLY_LIGHT,title:{text:'R² Score Comparison (%)',font:{size:14,color:'#f8fafc'}},yaxis:{range:[0,105],gridcolor:'rgba(255,255,255,0.05)'}},{responsive:true});

  Plotly.newPlot('ml-error-chart',[
    {x:names,y:names.map(n=>data.metrics[n].mae),name:'MAE',type:'bar',marker:{color:'#f59e0b'}},
    {x:names,y:names.map(n=>data.metrics[n].rmse),name:'RMSE',type:'bar',marker:{color:'#ef4444'}}
  ],{...PLOTLY_LIGHT,title:{text:'Error Comparison (seconds)',font:{size:14,color:'#f8fafc'}},barmode:'group',yaxis:{gridcolor:'rgba(255,255,255,0.05)'}},{responsive:true});
}

// ══════════════════════════════════════════════════════════
// BOX SIMULATION
// ══════════════════════════════════════════════════════════
async function loadSimulation(){
  const data=await api('/api/box_simulation');
  const c=document.getElementById('box-simulation');
  let html='<div class="box-grid">';
  const maxScale=Math.max(...data.map(d=>d.scale));
  data.forEach(d=>{
    const size=60+d.scale/maxScale*180;
    const tColor='rgba(239,68,68,0.25)';const ntColor='rgba(6,182,212,0.25)';
    html+=`<div class="sim-box" style="width:${size}px;height:${size}px;background:${tColor};border:2px solid rgba(239,68,68,0.5)"><div class="box-label" style="color:#f87171">${d.group}</div><div class="box-count" style="color:#fca5a5">${d.thermal_count} thermal</div><div class="box-range" style="color:#fca5a5">${d.area_range}</div></div>`;
    html+=`<div class="sim-box" style="width:${size}px;height:${size}px;background:${ntColor};border:2px solid rgba(6,182,212,0.5)"><div class="box-label" style="color:#22d3ee">${d.group}</div><div class="box-count" style="color:#67e8f9">${d.non_thermal_count} non-therm</div><div class="box-range" style="color:#67e8f9">${d.area_range}</div></div>`;
  });
  html+='</div><div class="sim-legend"><div class="legend-item"><div class="legend-dot" style="background:rgba(239,68,68,0.5)"></div>Thermal</div><div class="legend-item"><div class="legend-dot" style="background:rgba(6,182,212,0.5)"></div>Non-Thermal</div></div>';
  c.innerHTML=html;
}

// ══════════════════════════════════════════════════════════
// EXCEL UPLOAD
// ══════════════════════════════════════════════════════════
document.getElementById('btn-upload')?.addEventListener('click', () => {
  document.getElementById('file-upload').click();
});

document.getElementById('file-upload')?.addEventListener('change', async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  
  const btn = document.getElementById('btn-upload');
  const originalText = btn.innerHTML;
  btn.innerHTML = '⏳ Uploading...';
  btn.style.opacity = '0.7';
  btn.style.pointerEvents = 'none';

  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/upload', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    
    if (data.success) {
      showToast('✅ ' + data.message);
      await loadKPIs();
      await loadCharts();
      await loadClassTable();
      await loadSchedule();
      await loadGantt();
      await loadML();
      await loadSimulation();
      await checkShiftStatus();
      
      if (data.has_plan) {
        showToast('📥 Downloading Next Day Plan...', 4000);
        window.location.href = '/api/download_next_day_plan';
      }
    } else {
      showToast('❌ Upload failed: ' + data.message);
    }
  } catch (err) {
    showToast('❌ Upload error: ' + err.message);
  }

  btn.innerHTML = originalText;
  btn.style.opacity = '1';
  btn.style.pointerEvents = 'auto';
  e.target.value = '';
});

// ══════════════════════════════════════════════════════════
// SHIFT STATUS & END SHIFT
// ══════════════════════════════════════════════════════════
async function checkShiftStatus() {
  const data = await api('/api/shift_status');
  const btnUpload = document.getElementById('btn-upload');
  const badge = document.getElementById('shift-badge');
  const btnEnd = document.getElementById('btn-end-shift');
  if (data.shift_active) {
    btnUpload.style.opacity = '0.4';
    btnUpload.style.pointerEvents = 'none';
    btnUpload.title = "End shift to upload new data";
    badge.innerText = "SHIFT ACTIVE";
    badge.style.background = "linear-gradient(135deg, var(--green), #059669)";
    if(btnEnd) { btnEnd.style.display = 'flex'; }
  } else {
    btnUpload.style.opacity = '1';
    btnUpload.style.pointerEvents = 'auto';
    btnUpload.title = "";
    badge.innerText = "SHIFT ENDED";
    badge.style.background = "linear-gradient(135deg, var(--text-secondary), #475569)";
    if(btnEnd) { btnEnd.style.display = 'none'; }
  }
}

document.getElementById('btn-end-shift')?.addEventListener('click', async () => {
  if (!confirm("Are you sure you want to end the shift? This will generate the backlog Excel file.")) return;
  
  const link = document.createElement('a');
  showToast("⏳ Ending shift and generating backlog...");
  const res = await fetch('/api/end_shift', { method: 'POST' });
  if (res.ok) {
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    link.href = url;
    
    const disp = res.headers.get('Content-Disposition');
    let fname = "Backlog.xlsx";
    if (disp && disp.includes('filename=')) {
      fname = disp.split('filename=')[1].replace(/"/g, '');
    }
    
    link.download = fname;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    
    showToast("✅ Shift Ended. Backlog generated.");
    await checkShiftStatus();
  } else {
    showToast("❌ Failed to end shift.");
  }
});

// ══════════════════════════════════════════════════════════
// INIT
// ══════════════════════════════════════════════════════════
(async()=>{
  await checkShiftStatus();
  await loadKPIs();
  await loadCharts();
  await loadClassTable();
  await loadSchedule();
  await loadGantt();
  await loadML();
  await loadSimulation();

  // GSAP Animations removed as requested
})();
