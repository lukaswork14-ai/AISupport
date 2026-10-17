/* =================================================================== superHuy: biểu đồ dùng chung */
const SC = {late:'var(--s-red)', todo:'var(--s-blue)', doing:'var(--s-yellow)', done:'var(--s-aqua)', inc:'var(--s-aqua)', exp:'var(--s-orange)'};
const nf = n => Number(n||0).toLocaleString('vi-VN');
function money(v){ v = Math.round(v||0); const a = Math.abs(v), sg = v<0?'-':''; const t = x => (x.includes('.') ? x.replace(/0+$/,'').replace(/\.$/,'') : x).replace('.',',');
  if(a>=1e9) return sg+t((a/1e9).toFixed(2))+' tỷ'; if(a>=1e6) return sg+t((a/1e6).toFixed(a<1e7?2:1))+' tr'; if(a>=1e3) return sg+t((a/1e3).toFixed(a<1e5?1:0))+'k'; return sg+a+'đ'; }
function tipBind(root){ (root||document).querySelectorAll('.chart').forEach(c=>{ const line = c.querySelector('.tipline'); if(!line) return;
  const show = e => { const t = e.target.closest('[data-tip]'); if(t && c.contains(t)) line.textContent = t.dataset.tip; };
  c.onpointerover = show; c.onclick = show; }); }
function sbar(segs){ const tot = segs.reduce((a,x)=>a+x.v,0) || 1;
  return `<div class="sbar" role="img" aria-label="${esc(segs.map(x=>x.l+' '+x.v).join(', '))}">${segs.filter(x=>x.v>0).map(x=>`<i style="flex:${x.v/tot};background:${x.c}" data-tip="${esc(x.l)}: ${x.v}"></i>`).join('') || '<i style="flex:1;background:var(--fill)"></i>'}</div>
  <div class="legend">${segs.map(x=>`<span><i style="background:${x.c}"></i>${esc(x.l)} <b>${x.v}</b></span>`).join('')}</div>`; }
function vbars(rows, o={}){ // rows: [{l, v, tip, c?}] — cột dọc, đầu bo 4px, khe 2px, nhãn trục thưa
  const W = 320, H = o.h||110, pb = 18, n = rows.length || 1, gap = 2, bw = Math.max(2,(W - gap*(n-1))/n), max = Math.max(...rows.map(r=>r.v), 1);
  const every = Math.ceil(n/ (o.labels||8));
  const bars = rows.map((r,i)=>{ const h = r.v>0 ? Math.max(3, (H-pb-6) * r.v/max) : 0, x = i*(bw+gap), y = H-pb-h, rr = Math.min(4, bw/2);
    const path = h ? `M${x},${H-pb} V${y+rr} Q${x},${y} ${x+rr},${y} H${x+bw-rr} Q${x+bw},${y} ${x+bw},${y+rr} V${H-pb} Z` : '';
    return `<g data-tip="${esc(r.tip||r.l+': '+r.v)}"><rect x="${x}" y="0" width="${bw}" height="${H-pb}" fill="transparent"/>${path?`<path d="${path}" fill="${r.c||o.color||'var(--jade)'}"/>`:''}${i%every===0||i===n-1?`<text x="${x+bw/2}" y="${H-4}" text-anchor="middle">${esc(r.l)}</text>`:''}</g>`; }).join('');
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" preserveAspectRatio="none" role="img" aria-label="${esc(o.aria||'')}"><line class="base" x1="0" x2="${W}" y1="${H-pb}" y2="${H-pb}"/>${bars}</svg>`; }
function gbars(rows, keys, o={}){ // nhóm 2 cột / tháng: thu (aqua) và chi (cam)
  const W = 320, H = o.h||130, pb = 18, n = rows.length||1, grpW = W/n, inner = 2, bw = Math.min(22,(grpW-14)/keys.length), max = Math.max(...rows.flatMap(r=>keys.map(k=>r[k.k])),1);
  const g = rows.map((r,i)=>{ const x0 = i*grpW + (grpW - (bw*keys.length + inner*(keys.length-1)))/2;
    return keys.map((k,j)=>{ const v = r[k.k], h = v>0?Math.max(3,(H-pb-6)*v/max):0, x = x0 + j*(bw+inner), y = H-pb-h, rr=Math.min(4,bw/2);
      return h?`<path data-tip="${esc(r.l+' · '+k.l+': '+money(v))}" d="M${x},${H-pb} V${y+rr} Q${x},${y} ${x+rr},${y} H${x+bw-rr} Q${x+bw},${y} ${x+bw},${y+rr} V${H-pb} Z" fill="${k.c}"/>`:''; }).join('') + `<text x="${i*grpW+grpW/2}" y="${H-4}" text-anchor="middle">${esc(r.l)}</text>`; }).join('');
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" preserveAspectRatio="none" role="img" aria-label="${esc(o.aria||'')}"><line class="base" x1="0" x2="${W}" y1="${H-pb}" y2="${H-pb}"/>${g}</svg>`; }
function hbars(rows, fmtv){ const max = Math.max(...rows.map(r=>Math.max(r.v, r.budget||0)), 1);
  return rows.map(r=>`<div class="hb" data-tip="${esc(r.tip||r.l+': '+(fmtv?fmtv(r.v):r.v))}"><span class="nm">${esc(r.l)}</span><span class="tr"><i class="${r.budget && r.v>r.budget?'over':''}" style="width:${Math.max(r.v?2:0, r.v/max*100)}%"></i>${r.budget?`<u style="left:${r.budget/max*100}%"></u>`:''}</span><span class="v">${fmtv?fmtv(r.v):r.v}</span></div>`).join(''); }

/* =================================================================== trang chủ: tóm tắt việc + tiền */
S.tk = S.tk || {data:null, at:0, filter:'open', area:'', label:'', view:'list'};
S.fn = S.fn || {data:null, at:0, month:'', view:'overview'};
S.gr = S.gr || {data:null, at:0, view:'today', plan:null, planDay:''};
function homeStats(){
  const t = S.tk.data?.stats, r = S.fn.data?.report;
  const tasks = t ? `<b>${t.today} <small style="font-size:13px;font-weight:500">hôm nay</small></b><small>${t.overdue?`<span style="color:var(--danger);font-weight:600">${t.overdue} quá hạn</span> · `:''}${t.open} đang mở</small>` : `<b>…</b><small>Đang tải việc</small>`;
  const pct = r && r.budget_total ? Math.round(r.budget_spent/r.budget_total*100) : null;
  const fin = r ? `<b>${money(r.expense)}</b><small>${pct!==null?`${pct}% ngân sách đã đặt`:`thu ${money(r.income)} tháng này`}</small>` : `<b>…</b><small>Đang tải chi tiêu</small>`;
  const g = S.gr?.data, hab = g ? `<b>${g.today_done}/${g.today_due} <small style="font-size:13px;font-weight:500">thói quen</small></b><small>${g.today_due-g.today_done?`Còn ${g.today_due-g.today_done} việc tốt cho hôm nay`:'Hoàn thành hôm nay 🔥'}</small>` : `<b>…</b><small>Đang tải thói quen</small>`;
  return `<button class="card mini wide" onclick="go('growth')"><span class="lb2">${ico('sprout',16)} Phát triển hôm nay</span>${hab}</button><button class="card mini" onclick="go('tasks')"><span class="lb2">${ico('tasks',16)} Việc</span>${tasks}</button>
    <button class="card mini" onclick="go('money')"><span class="lb2">${ico('wallet',16)} Chi tiêu tháng</span>${fin}</button>`;
}
async function loadHomeStats(){
  const jobs = [];
  if(!S.tk.data || Date.now()-S.tk.at > 120000) jobs.push(run('viec','tongquan',{},'',true).then(r=>{ S.tk.data = r; S.tk.at = Date.now(); }).catch(()=>{}));
  if(!S.fn.data || Date.now()-S.fn.at > 120000) jobs.push(run('taichinh','tongquan',{},'',true).then(r=>{ S.fn.data = r; S.fn.at = Date.now(); }).catch(()=>{}));
  if(!S.gr.data || Date.now()-S.gr.at > 120000) jobs.push(run('phattrien','tongquan',{},'',true).then(r=>{ S.gr.data = r; S.gr.at = Date.now(); }).catch(()=>{}));
  if(!S.mt.at || Date.now()-S.mt.at > 120000) jobs.push(run('hop','danhsach',{},'',true).then(r=>{ S.mt.items = r.items||[]; S.mt.tax = r.taxonomy||{}; S.mt.at = Date.now(); }).catch(()=>{}));
  if(!jobs.length) return; await Promise.all(jobs); if(S.tab!=='home') return;
  const el = $('#hstat'); if(el) el.innerHTML = homeStats(); const rc = $('#recent'); if(rc) rc.innerHTML = recentCards(); const ap = $('.apps'); if(ap) ap.innerHTML = appsGrid();
  const hp = $('.hero p'); if(hp){ const t = S.tk.data?.stats, g = S.gr?.data, n = urgentItems().length; hp.innerHTML = [t?`<b>${t.today}</b> việc hôm nay`:'', g?`<b>${g.today_done}/${g.today_due}</b> thói quen`:'', n?`<b>${n}</b> mục cần anh`:''].filter(Boolean).join(' · ') || hp.innerHTML; }
}

/* =================================================================== VIỆC */
const AREA = {work:'Công việc', income:'Thu nhập', health:'Sức khoẻ', relations:'Quan hệ', skills:'Năng lực', self:'Bản thân'};
const SRC = {lark:'Lark', google:'Google', local:'superHuy'};
async function tasksEnter(force){
  if(S.tk.loading) return;
  if(!force && S.tk.data && Date.now()-S.tk.at < 30000) return;
  S.tk.loading = true; if(S.tab==='tasks') paintTasks();
  try{ S.tk.data = await run('viec','tongquan',{refresh: !!force || !!S.tk.data},'',true); S.tk.at = Date.now(); }
  catch(e){ toast(e.message); }
  S.tk.loading = false; if(S.tab==='tasks' && !document.querySelector('#sheet.on')) render();
}
function paintTasks(){ const el = $('#tkHead'); if(el) el.innerHTML = tkHead(); }
function tkHead(){ const s = S.tk.data?.stats;
  return S.tk.loading ? '<span class="spin" style="width:12px;height:12px;display:inline-block;vertical-align:-1px"></span> Đang đồng bộ Lark, Google…' : s ? `${s.open} việc đang mở · ${s.done30} xong 30 ngày qua` : 'Mọi việc ở một nơi'; }
function dueLabel(t){
  if(!t.due) return '';
  const d = new Date(t.due), now = new Date(), p2 = n => String(n).padStart(2,'0'), dd = `${p2(d.getDate())}/${p2(d.getMonth()+1)}`;
  const hm = t.all_day || (d.getHours()===23 && d.getMinutes()===59) ? '' : ` ${p2(d.getHours())}:${p2(d.getMinutes())}`;
  if(t.done) return dd;
  if(t.overdue) return `<span class="late">${t.days_over>0?'Quá hạn '+t.days_over+' ngày':'Quá hạn'+(hm?' từ'+hm:'')}</span>`;
  if(t.due_today) return `<span class="today">Hôm nay${hm}</span>`;
  const tm = new Date(now); tm.setDate(tm.getDate()+1);
  if(d.toDateString()===tm.toDateString()) return 'Ngày mai'+hm;
  return dd + hm;
}
function taskRow(t){
  const who = !t.mine && t.assignees?.length ? `<span>→ ${esc(t.assignees.join(', '))}</span>` : '';
  const labs = (t.labels||[]).slice(0,2).map(l=>`<span class="sx">${esc(l)}</span>`).join('');
  return `<div class="trow ${t.done?'done':''}"><button class="tick ${t.done?'on':t.status==='doing'?'doing':''}" aria-label="${t.done?'Mở lại':'Hoàn thành'}" onclick="tkToggle('${esc(t.id)}')">${ico('check',14)}</button>
    <button class="grow" style="text-align:left" onclick="openTask('${esc(t.id)}')"><div class="tt">${esc(t.title)}</div>
    <div class="tmeta">${dueLabel(t)}<span class="sx ${t.source}">${SRC[t.source]}</span>${who}${t.area!=='work'?`<span>${esc(AREA[t.area]||'')}</span>`:''}${labs}</div></button></div>`;
}
function tkFiltered(){
  const d = S.tk.data; if(!d) return [];
  const f = S.tk.filter;
  return d.items.filter(t => (f==='done' ? t.done : !t.done) && (f!=='today'||t.due_today) && (f!=='late'||t.overdue) && (f!=='review'||t.review)
    && (f!=='delegated'||!t.mine) && (!S.tk.area||t.area===S.tk.area) && (!S.tk.label||(t.labels||[]).includes(S.tk.label)));
}
function vTasks(){
  const d = S.tk.data, s = d?.stats, v = S.tk.view;
  const head = `<div class="date" id="tkHead">${tkHead()}</div><div class="row" style="align-items:center;margin-bottom:14px;flex-wrap:nowrap"><h1 class="grow" style="margin:2px 0 0">Việc</h1><button class="btn pri" onclick="openAddTask()">${ico('plus')} Thêm việc</button></div>
    <div class="seg" style="margin-bottom:14px"><button class="${v==='list'?'on':''}" onclick="S.tk.view='list';render()">Danh sách</button><button class="${v==='report'?'on':''}" onclick="S.tk.view='report';render()">Báo cáo</button></div>`;
  if(!d) return head + `<div class="card pad"><div class="skel" style="width:60%"></div><div class="skel"></div><div class="skel" style="width:80%"></div></div>`;
  const errs = Object.entries(d.errors||{}).map(([k,m])=>`<div class="note">${k==='google'?'Google Tasks':'Lark'}: ${esc(m)}</div>`).join('');
  const conn = !d.sources.lark ? `<div class="note">Kết nối Lark (Thêm › Kết nối › Lịch Lark) để thấy và giao việc Lark.</div>` : '';
  if(v==='report') return head + errs + tkReport(d);
  const f = S.tk.filter, items = tkFiltered();
  const fchips = [['open','Đang mở',s.open],['today','Hôm nay',s.today],['late','Quá hạn',s.overdue],['review','Cần xem xét',s.review],['delegated','Đã giao',s.delegated],['done','Đã xong',s.done30]]
    .map(([k,l,n])=>`<button class="chip ${f===k?'on':''}" onclick="S.tk.filter='${k}';render()">${l} ${n}</button>`).join('');
  const areas = Object.entries(AREA).filter(([k])=>d.items.some(t=>!t.done&&t.area===k));
  const achips = areas.length>1 ? `<div class="chips" style="padding-top:6px">${areas.map(([k,l])=>`<button class="chip ${S.tk.area===k?'on':''}" onclick="S.tk.area=S.tk.area==='${k}'?'':'${k}';render()">${l}</button>`).join('')}${(d.labels||[]).slice(0,10).map(l=>`<button class="chip ${S.tk.label===l?'on':''}" onclick="S.tk.label=S.tk.label===${esc(JSON.stringify(l))}?'':${esc(JSON.stringify(l))};render()">#${esc(l)}</button>`).join('')}</div>` : '';
  const quick = `<div class="nl" style="margin:0 0 4px"><input id="tkQuick" placeholder="Giao Linh báo cáo Q4 trước thứ 6…" enterkeyhint="go"><button class="btn pri" id="tkQuickBtn" aria-label="Tạo bằng AI">${ico('spark',17)}</button></div>`;
  const review = s.review && f==='open' ? `<button class="card review" onclick="tkSuggest()"><span class="grow"><b>${s.review} việc cần xem xét</b><div class="meta">Quá hạn hoặc treo lâu. superHuy gợi ý gia hạn, giao hay bỏ.</div></span>${ico('spark',20)}</button>` : '';
  let body;
  if(!items.length) body = `<div class="card empty">${f==='open'?'Không còn việc nào đang mở. Thêm việc mới bằng ô phía trên.':'Không có việc nào trong mục này.'}</div>`;
  else if(f==='open' || f==='delegated'){
    const now = new Date(), wk = new Date(now.getTime()+7*864e5);
    const g = [['Quá hạn', items.filter(t=>t.overdue), 'late'], ['Hôm nay', items.filter(t=>!t.overdue&&t.due_today)], ['7 ngày tới', items.filter(t=>!t.overdue&&!t.due_today&&t.due&&new Date(t.due)<=wk)],
               ['Sau đó', items.filter(t=>t.due&&new Date(t.due)>wk)], ['Chưa có hạn', items.filter(t=>!t.due)]];
    body = g.filter(x=>x[1].length).map(([l,arr,c])=>`<div class="grp ${c||''}"><span>${l}</span><span>${arr.length}</span></div><div class="card">${arr.map(taskRow).join('')}</div>`).join('');
  } else body = `<div class="card" style="margin-top:12px">${items.slice(0,150).map(taskRow).join('')}</div>`;
  setTimeout(bindTkQuick, 0);
  return head + errs + conn + quick + `<div class="chips">${fchips}</div>` + achips + review + body;
}
function tkReport(d){
  const s = d.stats, wk = s.weeks || [];
  const ontime = s.on_time_rate===null||s.on_time_rate===undefined ? '—' : Math.round(s.on_time_rate*100)+'%';
  const areaRows = Object.entries(s.by_area||{}).map(([k,v])=>({l:AREA[k]||k, v})).sort((a,b)=>b.v-a.v);
  const labRows = Object.entries(s.by_label||{}).map(([k,v])=>({l:k, v}));
  const srcRows = Object.entries(s.by_source||{}).map(([k,v])=>({l:SRC[k]||k, v}));
  return `<div class="kpis">
      <button class="card kpi" onclick="S.tk.view='list';S.tk.filter='open';render()"><b>${s.open}</b><span>Đang mở</span></button>
      <button class="card kpi" onclick="S.tk.view='list';S.tk.filter='today';render()"><b>${s.today}</b><span>Hạn hôm nay</span></button>
      <button class="card kpi ${s.overdue?'warn':''}" onclick="S.tk.view='list';S.tk.filter='late';render()"><b>${s.overdue}</b><span>Quá hạn</span></button>
      <button class="card kpi" onclick="S.tk.view='list';S.tk.filter='review';render()"><b>${s.review}</b><span>Cần xem xét (gia hạn, giao, bỏ)</span></button>
      <div class="card kpi"><b>${s.done30}</b><span>Hoàn thành 30 ngày</span></div>
      <div class="card kpi"><b>${ontime}</b><span>Đúng hạn (việc đã xong)</span></div></div>
    <div class="card chart" style="margin-top:12px"><h3>Trạng thái</h3><p class="cap">Việc đang mở theo trạng thái, kèm việc xong 30 ngày qua</p>
      ${sbar([{l:'Quá hạn',v:s.by_status.overdue,c:SC.late},{l:'Cần làm',v:Math.max(0,s.by_status.todo-s.by_status.overdue),c:SC.todo},{l:'Đang làm',v:s.by_status.doing,c:SC.doing},{l:'Xong',v:s.by_status.done,c:SC.done}])}<div class="tipline"></div></div>
    <div class="card chart" style="margin-top:12px"><h3>Hoàn thành mỗi tuần</h3><p class="cap">8 tuần gần nhất · chạm cột để xem số</p>
      ${vbars(wk.map(w=>({l:w.week, v:w.done, tip:`Tuần ${w.week}: xong ${w.done} việc, ${w.due} việc tới hạn`})), {aria:'Số việc hoàn thành mỗi tuần'})}<div class="tipline"></div></div>
    ${areaRows.length?`<div class="card chart" style="margin-top:12px"><h3>Theo lĩnh vực</h3><p class="cap">Việc đang mở trong 6 lĩnh vực của anh</p>${hbars(areaRows)}<div class="tipline"></div></div>`:''}
    ${labRows.length?`<div class="card chart" style="margin-top:12px"><h3>Theo nhãn / dự án</h3><p class="cap">Top nhãn có nhiều việc đang mở</p>${hbars(labRows)}<div class="tipline"></div></div>`:''}
    <div class="card chart" style="margin-top:12px"><h3>Theo nguồn</h3><p class="cap">Đang mở · ${s.delegated} việc anh đã giao cho người khác · ${s.no_due} việc chưa có hạn</p>${hbars(srcRows)}<div class="tipline"></div></div>
    <p class="muted small" style="margin:14px 4px">Cập nhật ${new Date(d.at*1000).toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit'})}. <button class="addlink" onclick="tasksEnter(true)">${ico('refresh',14)} Làm mới</button></p>`;
}
function bindTkQuick(){
  tipBind($('#app'));
  const i = $('#tkQuick'), b = $('#tkQuickBtn'); if(!i) return;
  i.onkeydown = e => { if(e.key==='Enter'){ e.preventDefault(); b.click(); } };
  b.onclick = async () => { const t = i.value.trim(); if(!t) return openAddTask();
    b.disabled = true; b.innerHTML = '<span class="spin"></span>';
    try{ const r = await run('viec','hieu',{text:t},'AI đang đọc việc'); openAddTask(r); }catch(e){ toast(e.message); }
    b.disabled = false; b.innerHTML = ico('spark',17); };
}
function tkFind(id){ return (S.tk.data?.items||[]).find(t=>t.id===id); }
async function tkToggle(id){
  const t = tkFind(id); if(!t) return; haptic(t.done?'light':'medium');
  t.done = !t.done; t.status = t.done?'done':'todo'; render();
  try{ const r = await run('viec','xong',{task_id:id, done:t.done},'',true); toast(r.text); tasksEnter(true); }
  catch(e){ t.done = !t.done; render(); toast(e.message); }
}
function isoPlus(days){ const d = new Date(); d.setDate(d.getDate()+days); return d.toLocaleDateString('sv-SE'); }
function nextMonday(){ const d = new Date(); d.setDate(d.getDate() + ((8 - d.getDay()) % 7 || 7)); return d.toLocaleDateString('sv-SE'); }
function sunday(){ const d = new Date(); d.setDate(d.getDate() + ((7 - d.getDay()) % 7)); return d.toLocaleDateString('sv-SE'); }
function openTask(id){
  const t = tkFind(id); if(!t) return;
  const due = t.due ? new Date(t.due).toLocaleString('vi-VN',{weekday:'long', day:'2-digit', month:'2-digit', ...(t.all_day?{}:{hour:'2-digit',minute:'2-digit'})}) : 'Chưa có hạn';
  sheet(`<div class="meta">${SRC[t.source]}${t.list?' · '+esc(t.list):''}</div><h2 style="margin:2px 0 6px">${esc(t.title)}</h2>
    <p class="lead">${esc(due)}${!t.mine&&t.assignees?.length?' · giao cho '+esc(t.assignees.join(', ')):''}${t.overdue?` · <span style="color:var(--danger);font-weight:600">quá hạn ${t.days_over} ngày</span>`:''}</p>
    ${t.notes?`<p style="white-space:pre-wrap;margin:-6px 0 14px;font-size:14px">${esc(t.notes)}</p>`:''}
    <p class="lbl">Trạng thái</p><div class="seg" style="margin-bottom:16px">${[['todo','Cần làm'],['doing','Đang làm'],['done','Xong']].map(([k,l])=>`<button class="${t.status===k?'on':''}" onclick="tkStatus('${esc(t.id)}','${k}')">${l}</button>`).join('')}</div>
    ${t.done?'':`<p class="lbl">Gia hạn</p><div class="inrow">${[['Ngày mai',isoPlus(1)],['+3 ngày',isoPlus(3)],['Chủ nhật',sunday()],['Tuần sau',nextMonday()]].map(([l,dd])=>`<button class="chip" onclick="tkExtend('${esc(t.id)}','${dd}')">${l}</button>`).join('')}<input type="date" onchange="tkExtend('${esc(t.id)}', this.value)"></div>`}
    <p class="lbl">Lĩnh vực</p><div class="inrow">${Object.entries(AREA).map(([k,l])=>`<button class="chip ${t.area===k?'on':''}" onclick="tkTag('${esc(t.id)}','${k}',null)">${l}</button>`).join('')}</div>
    <label class="field"><span>Nhãn (tổ chức, phòng ban, dự án), cách nhau bởi dấu phẩy</span><input type="text" id="tkLabels" value="${esc((t.labels||[]).filter(l=>l!==t.list).join(', '))}" onchange="tkTag('${esc(t.id)}','',this.value)"></label>
    <div class="row">${t.url?`<button class="btn" onclick="openLink('${esc(t.url)}')">${ico('link')} Mở trong ${SRC[t.source]}</button>`:''}${t.source==='local'?`<button class="btn" style="color:var(--danger)" onclick="tkDelete('${esc(t.id)}')">${ico('trash')} Xoá</button>`:''}</div>`);
}
async function tkStatus(id, st){ const t = tkFind(id); if(!t) return; t.status = st; t.done = st==='done'; closeSheet(); render();
  try{ const r = await run('viec', st==='done'?'xong':'trangthai', st==='done'?{task_id:id, done:true}:{task_id:id, status:st},'',true); toast(r.text); tasksEnter(true); }catch(e){ toast(e.message); tasksEnter(true); } }
async function tkExtend(id, due){ if(!due) return; closeSheet(); toast('Đang gia hạn…');
  try{ const r = await run('viec','giahan',{task_id:id, due},'Gia hạn'); toast(r.text); tasksEnter(true); }catch(e){ toast(e.message); } }
async function tkTag(id, area, labels){ const t = tkFind(id); const p = {task_id:id}; if(area){ p.area = area; if(t) t.area = area; } if(labels!==null) p.labels = labels;
  try{ await run('viec','nhan',p,'',true); if(area) openTask(id); toast('Đã cập nhật nhãn'); S.tk.at = 0; }catch(e){ toast(e.message); } }
async function tkDelete(id){ closeSheet(); try{ const r = await run('viec','xoa',{task_id:id}); toast(r.text); tasksEnter(true); }catch(e){ toast(e.message); } }
async function tkSuggest(){
  sheet(`<h2>superHuy gợi ý</h2><p class="lead">Đang xem các việc quá hạn và treo lâu theo vai trò CEO, CGO, CAO của anh…</p><div class="card pad"><div class="skel"></div><div class="skel" style="width:70%"></div></div>`);
  try{
    const r = await run('viec','goiy',{},'superHuy đang xem việc tồn');
    const lab = {extend:'Gia hạn', do:'Làm ngay', delegate:'Giao việc', drop:'Bỏ'};
    sheet(`<h2>superHuy gợi ý</h2><p class="lead">${esc(r.text)}</p><div class="card">${(r.items||[]).map(x=>{ const t = tkFind(x.id); if(!t) return '';
      const btn = x.action==='extend' && x.due ? `<button class="btn pri" onclick="tkExtend('${esc(t.id)}','${esc(x.due)}')">Gia hạn đến ${esc(x.due.slice(8,10)+'/'+x.due.slice(5,7))}</button>`
        : x.action==='do' ? `<button class="btn pri" onclick="tkExtend('${esc(t.id)}','${isoPlus(0)}')">Đặt hạn hôm nay</button>`
        : x.action==='drop' ? `<button class="btn" onclick="closeSheet();tkToggle('${esc(t.id)}')">Đánh dấu xong</button>`
        : `<button class="btn" onclick="openTask('${esc(t.id)}')">Mở việc</button>`;
      return `<div class="tsug"><div class="row" style="flex-wrap:nowrap;align-items:flex-start"><div class="grow"><div style="font-weight:600">${esc(t.title)}</div><div class="meta"><b style="color:var(--text)">${lab[x.action]||''}</b> · ${esc(x.why||'')}</div></div></div><div class="row" style="margin-top:8px">${btn}</div></div>`; }).join('') || '<div class="empty">Không có gợi ý.</div>'}</div>`);
  }catch(e){ sheet(`<h2>superHuy gợi ý</h2><p class="lead">${esc(e.message)}</p>`); }
}
function openAddTask(pre){
  const d = S.tk.data || {sources:{}, lists:{}, people:[], labels:[]};
  S.nt = Object.assign({title:'', due:'', time:'', source: d.sources?.lark ? 'lark' : 'local', assignee_id:'', assignee:'', list_id:'', area:'work', labels:[], notes:''}, pre||{});
  if(pre && pre.assignee && !pre.assignee_id) S.nt.source = 'local';
  sheet(`<h2>Thêm việc</h2><p class="lead">Gõ một câu để superHuy điền, hoặc điền tay.</p>
    <div class="nl"><input id="ntNl" placeholder="Nhắc Minh gửi hợp đồng thứ 5, dự án CJ" enterkeyhint="go"><button class="btn pri" id="ntNlBtn">${ico('spark',17)} Điền</button></div>
    <label class="field"><span>Việc cần làm</span><input type="text" id="ntTitle" placeholder="Ví dụ: Duyệt ngân sách ads tháng 11"></label>
    <p class="lbl">Hạn</p><div class="inrow" id="ntDue"></div>
    <p class="lbl">Lưu ở</p><div class="seg" id="ntSrc" style="margin-bottom:14px"></div>
    <div id="ntWho"></div>
    <p class="lbl">Lĩnh vực</p><div class="inrow" id="ntArea"></div>
    <p class="lbl">Nhãn</p><div class="inrow" id="ntLab"></div>
    <details><summary>Ghi chú</summary><label class="field"><span>Chi tiết</span><textarea id="ntNotes" style="min-height:80px"></textarea></label></details>
    <button class="btn pri full" id="ntSave">Tạo việc</button>`);
  paintNt();
  $('#ntNl').onkeydown = e => { if(e.key==='Enter'){ e.preventDefault(); $('#ntNlBtn').click(); } };
  $('#ntNlBtn').onclick = async () => { const t = $('#ntNl').value.trim(); if(!t) return; const b = $('#ntNlBtn'); b.disabled = true; b.innerHTML = '<span class="spin"></span>';
    try{ const r = await run('viec','hieu',{text:t},'AI đang đọc việc'); Object.assign(S.nt, r); paintNt(); }catch(e){ toast(e.message); }
    b.disabled = false; b.innerHTML = `${ico('spark',17)} Điền`; };
  $('#ntSave').onclick = async () => {
    S.nt.title = $('#ntTitle').value.trim(); S.nt.notes = $('#ntNotes').value.trim();
    if(!S.nt.title) return toast('Ghi tên việc trước nhé');
    const b = $('#ntSave'); b.disabled = true; b.innerHTML = '<span class="spin"></span> Đang tạo';
    try{ const r = await run('viec','tao',{...S.nt, labels:S.nt.labels},'Tạo việc'); closeSheet(); toast(r.text); haptic('medium'); tasksEnter(true); }
    catch(e){ toast(e.message); b.disabled = false; b.textContent = 'Tạo việc'; }
  };
}
function paintNt(){
  const n = S.nt, d = S.tk.data || {sources:{}, lists:{}, people:[], labels:[]};
  if(n.title) $('#ntTitle').value = n.title; if(n.notes) $('#ntNotes').value = n.notes;
  const opts = [['',`Không hạn`],[isoPlus(0),'Hôm nay'],[isoPlus(1),'Ngày mai'],[sunday(),'Cuối tuần'],[nextMonday(),'Tuần sau']];
  $('#ntDue').innerHTML = opts.map(([v,l])=>`<button class="chip ${n.due===v?'on':''}" onclick="S.nt.due='${v}';paintNt()">${l}</button>`).join('') + `<input type="date" value="${n.due||''}" onchange="S.nt.due=this.value;paintNt()">` + (n.due?`<input type="time" value="${n.time||''}" onchange="S.nt.time=this.value">`:'');
  const srcs = [['local','superHuy',true],['lark','Lark',d.sources?.lark],['google','Google Tasks',d.sources?.google]];
  $('#ntSrc').innerHTML = srcs.map(([k,l,ok])=>`<button class="${n.source===k?'on':''}" ${ok?'':'disabled style="opacity:.4"'} onclick="S.nt.source='${k}';paintNt()">${l}</button>`).join('');
  let who = '';
  if(n.source==='lark'){
    const ppl = d.people||[], q = (S.ntQ||'').toLowerCase();
    const sel = ppl.find(p=>p.id===n.assignee_id);
    const list = ppl.filter(p=>!q || p.name.toLowerCase().includes(q)).slice(0,40);
    who = `<p class="lbl">Giao cho</p><div class="nl" style="margin-bottom:8px"><input id="ntPpl" placeholder="Tìm tên đồng nghiệp…" value="${esc(S.ntQ||'')}"></div>
      <div class="pick card"><button class="${!n.assignee_id?'on':''}" onclick="S.nt.assignee_id='';S.nt.assignee='';paintNt()"><span class="av">Tôi</span>Tôi tự làm</button>${list.map(p=>`<button class="${n.assignee_id===p.id?'on':''}" onclick="S.nt.assignee_id='${esc(p.id)}';S.nt.assignee=${esc(JSON.stringify(p.name))};paintNt()"><span class="av">${esc(initials(p.name))}</span>${esc(p.name)}</button>`).join('')}</div>
      ${sel?`<p class="muted small" style="margin:-8px 0 12px">Sẽ giao cho <b style="color:var(--text)">${esc(sel.name)}</b> trên Lark, họ nhận thông báo ngay.</p>`:''}
      ${(d.lists?.lark||[]).length?`<label class="field"><span>Danh sách / dự án Lark</span><select onchange="S.nt.list_id=this.value"><option value="">Không</option>${d.lists.lark.map(l=>`<option value="${esc(l.id)}" ${n.list_id===l.id?'selected':''}>${esc(l.name)}</option>`).join('')}</select></label>`:''}`;
  } else if(n.source==='google' && (d.lists?.google||[]).length){
    who = `<label class="field"><span>Danh sách Google Tasks</span><select onchange="S.nt.list_id=this.value">${d.lists.google.map(l=>`<option value="${esc(l.id)}" ${n.list_id===l.id?'selected':''}>${esc(l.title)}</option>`).join('')}</select></label>`;
  } else if(n.source==='local'){
    who = `<label class="field"><span>Người phụ trách (không bắt buộc)</span><input type="text" value="${esc(n.assignee||'')}" placeholder="Tôi" onchange="S.nt.assignee=this.value"></label>`;
  }
  $('#ntWho').innerHTML = who;
  const pp = $('#ntPpl'); if(pp){ pp.oninput = () => { S.ntQ = pp.value; const pos = pp.selectionStart; paintNt(); const p2 = $('#ntPpl'); p2.focus(); p2.setSelectionRange(pos,pos); }; }
  $('#ntArea').innerHTML = Object.entries(AREA).map(([k,l])=>`<button class="chip ${n.area===k?'on':''}" onclick="S.nt.area='${k}';paintNt()">${l}</button>`).join('');
  const all = [...new Set([...(d.labels||[]).slice(0,12), ...n.labels])];
  $('#ntLab').innerHTML = all.map(l=>`<button class="chip ${n.labels.includes(l)?'on':''}" onclick="ntLab(${esc(JSON.stringify(l))})">#${esc(l)}</button>`).join('') + `<input type="text" placeholder="+ nhãn mới" style="width:120px;padding:8px 12px;border-radius:999px;border:0;box-shadow:0 0 0 1px var(--line);background:var(--surface);color:var(--text);font:inherit;font-size:13.5px" onkeydown="if(event.key==='Enter'){event.preventDefault();ntLab(this.value.trim())}" onchange="ntLab(this.value.trim())">`;
}
function ntLab(l){ if(!l) return; const a = S.nt.labels; const i = a.indexOf(l); if(i>=0) a.splice(i,1); else a.push(l); paintNt(); }

/* =================================================================== TÀI CHÍNH */
async function moneyEnter(force){
  if(S.fn.loading) return;
  if(!force && S.fn.data && Date.now()-S.fn.at < 30000 && (S.fn.data.report.month===(S.fn.month||S.fn.data.report.month))) return;
  S.fn.loading = true;
  try{ S.fn.data = await run('taichinh','tongquan',{month:S.fn.month||''},'',true); S.fn.at = Date.now(); }catch(e){ toast(e.message); }
  S.fn.loading = false; if(S.tab==='money' && !document.querySelector('#sheet.on')) render();
}
function ymShift(ym, k){ let [y,m] = ym.split('-').map(Number); m += k; while(m<1){m+=12;y--} while(m>12){m-=12;y++} return `${y}-${String(m).padStart(2,'0')}`; }
function catOf(t){ const c = S.fn.data?.cats; return (t.kind==='income'?c?.income:c?.expense)?.[t.category] || {name:'Khác', icon:'•'}; }
function vMoney(){
  const d = S.fn.data, v = S.fn.view;
  const ym = d?.report.month || new Date().toLocaleDateString('sv-SE').slice(0,7), cur = new Date().toLocaleDateString('sv-SE').slice(0,7);
  const head = `<div class="mnav"><button aria-label="Tháng trước" onclick="S.fn.month='${ymShift(ym,-1)}';moneyEnter(true)">${ico('back',16)}</button>Tháng ${ym.slice(5)}/${ym.slice(0,4)}${ym<cur?`<button aria-label="Tháng sau" onclick="S.fn.month='${ymShift(ym,1)}';moneyEnter(true)">${ico('chev',16)}</button>`:''}${S.fn.loading?' <span class="spin" style="width:12px;height:12px"></span>':''}</div>
    <div class="row" style="align-items:center;margin-bottom:14px;flex-wrap:nowrap"><h1 class="grow" style="margin:2px 0 0">Tài chính</h1><button class="btn pri" onclick="openAddMoney()">${ico('plus')} Ghi</button></div>
    <div class="nl" style="margin-bottom:12px"><input id="fnQuick" placeholder="cafe 45k · nhận lương 80tr · Linh nợ 5tr" enterkeyhint="go"><button class="btn pri" id="fnQuickBtn" aria-label="Ghi bằng AI">${ico('spark',17)}</button></div>
    <div class="seg" style="margin-bottom:14px">${[['overview','Tổng quan'],['tx','Thu chi'],['debts','Phải thu/trả'],['budget','Ngân sách']].map(([k,l])=>`<button class="${v===k?'on':''}" onclick="S.fn.view='${k}';render()">${l}</button>`).join('')}</div>`;
  setTimeout(bindFnQuick, 0);
  if(!d) return head + `<div class="card pad"><div class="skel" style="width:60%"></div><div class="skel"></div><div class="skel" style="width:80%"></div></div>`;
  return head + ({overview:fnOverview, tx:fnTx, debts:fnDebts, budget:fnBudget})[v](d);
}
function fnOverview(d){
  const r = d.report, pct = r.budget_total ? r.budget_spent/r.budget_total : null;
  const delta = r.prev_expense ? Math.round((r.expense - r.prev_expense)/r.prev_expense*100) : null;
  const sr = r.savings_rate===null ? '—' : Math.round(r.savings_rate*100)+'%';
  const days = r.daily.map((v,i)=>({l:String(i+1), v, tip:`Ngày ${i+1}/${r.month.slice(5)}: ${money(v)}`}));
  const cats = r.categories.map(c=>({l:`${c.icon} ${c.name}`, v:c.spent, budget:c.budget, tip:`${c.name}: ${money(c.spent)}${c.budget?` / ngân sách ${money(c.budget)}`:''}${c.prev?` · tháng trước ${money(c.prev)}`:''}`}));
  const trend = d.trend.map(t=>({l:'T'+Number(t.month.slice(5)), inc:t.income, exp:t.expense}));
  if(!r.income && !r.expense && !d.debts.length) return `<div class="card pad"><b>Bắt đầu theo dõi tài chính</b><p class="muted" style="margin:6px 0 0">Gõ một câu vào ô phía trên, ví dụ “cafe 45k”, “nhận lương 80tr”, “trả tiền nhà 12tr”, “Linh nợ 5tr trả cuối tháng”. superHuy tự phân loại và lập báo cáo.</p></div>${fnBudgetHint()}`;
  return `<div class="card hero"><div class="muted small" style="font-weight:600">Đã chi tháng này</div><div class="big">${money(r.expense)}</div>
      <div class="sub">${pct!==null?`Danh mục có ngân sách: ${money(r.budget_spent)} / ${money(r.budget_total)} (${Math.round(pct*100)}%)`:'Chưa đặt ngân sách'}${delta!==null?` · ${delta>=0?'+':''}${delta}% so với tháng trước`:''}${r.forecast_expense>r.expense?` · dự kiến cả tháng ${money(r.forecast_expense)}`:''}</div>
      ${pct!==null?`<div class="meter"><i class="${pct>1?'over':pct>.8?'near':''}" style="width:${Math.min(100,pct*100)}%"></i></div>`:''}</div>
    <div class="kpis" style="margin-top:10px">
      <div class="card kpi"><b>${money(r.income)}</b><span>Thu</span></div>
      <div class="card kpi ${r.net<0?'warn':''}"><b>${money(r.net)}</b><span>Còn lại (thu − chi)</span></div>
      <div class="card kpi"><b>${sr}</b><span>Tỷ lệ tiết kiệm</span></div>
      <button class="card kpi" onclick="S.fn.view='debts';render()"><b style="font-size:19px">+${money(r.receivable)} / −${money(r.payable)}</b><span>Phải thu / phải trả${r.overdue_debts?` · <span style="color:var(--danger);font-weight:600">${r.overdue_debts} quá hạn</span>`:''}</span></button></div>
    ${fnAnalysis(d)}
    ${cats.length?`<div class="card chart" style="margin-top:12px"><h3>Chi theo danh mục</h3><p class="cap">Vạch đứng là ngân sách tháng · chạm để xem chi tiết</p>${hbars(cats, money)}<div class="tipline"></div></div>`:''}
    <div class="card chart" style="margin-top:12px"><h3>Chi mỗi ngày</h3><p class="cap">Tháng ${r.month.slice(5)} · chạm cột để xem số</p>${vbars(days,{h:100,labels:6,color:'var(--s-orange)',aria:'Chi tiêu mỗi ngày'})}<div class="tipline"></div></div>
    <div class="card chart" style="margin-top:12px"><h3>6 tháng gần nhất</h3><div class="legend" style="margin:4px 0 8px"><span><i style="background:${SC.inc}"></i>Thu</span><span><i style="background:${SC.exp}"></i>Chi</span></div>${gbars(trend,[{k:'inc',l:'Thu',c:SC.inc},{k:'exp',l:'Chi',c:SC.exp}],{aria:'Thu và chi 6 tháng'})}<div class="tipline"></div></div>
    ${r.top.length?`<div class="sec"><h2>Khoản chi lớn nhất</h2></div><div class="card">${r.top.map(fnRow).join('')}</div>`:''}`;
}
function fnAnalysis(d){ const a = d.analysis;
  return `<div class="card pad" style="margin-top:12px"><div class="row" style="flex-wrap:nowrap;margin-bottom:8px"><b class="grow" style="display:inline-flex;gap:6px;align-items:center">${ico('spark',16)} Phân tích của superHuy</b><button class="addlink" id="fnAnaBtn" onclick="fnAnalyze()">${a?'Phân tích lại':'Phân tích ngay'}</button></div>
    ${a?`<div class="ai-text">${esc(a.text)}</div>`:'<p class="muted small" style="margin:0">Trợ lý tài chính đọc thu chi tháng này, chỉ ra điểm bất thường và đề xuất tối ưu cụ thể. Báo cáo tháng cũng tự gửi vào Telegram ngày 1 hằng tháng.</p>'}</div>`; }
async function fnAnalyze(){ const b = $('#fnAnaBtn'); if(b){ b.innerHTML = '<span class="spin"></span> Đang phân tích'; b.disabled = true; }
  try{ const r = await run('taichinh','phantich',{month:S.fn.data?.report.month||''},'superHuy đang phân tích'); S.fn.data.analysis = {text:r.text}; render(); }catch(e){ toast(e.message); if(b){ b.textContent='Phân tích ngay'; b.disabled=false; } } }
function fnRow(t){ const c = catOf(t);
  return `<button class="txrow" onclick="openTx('${t.id}')"><span class="ic">${c.icon}</span><div class="grow"><div style="font-weight:500">${esc(t.note||c.name)}</div><div class="meta">${esc(c.name)} · ${t.date.slice(8,10)}/${t.date.slice(5,7)}</div></div><span class="amt ${t.kind==='income'?'in':''}">${t.kind==='income'?'+':'−'}${money(t.amount)}</span></button>`; }
function fnTx(d){
  if(!d.tx.length) return `<div class="card empty">Chưa có giao dịch tháng này. Ghi nhanh bằng ô phía trên.</div>`;
  const by = {}; d.tx.forEach(t=>(by[t.date] = by[t.date]||[]).push(t));
  return Object.entries(by).map(([day, arr])=>{ const net = arr.reduce((a,t)=>a+(t.kind==='income'?t.amount:-t.amount),0);
    const dd = new Date(day+'T12:00:00').toLocaleDateString('vi-VN',{weekday:'short', day:'2-digit', month:'2-digit'});
    return `<div class="grp"><span>${esc(dd)}</span><span>${net>=0?'+':''}${money(net)}</span></div><div class="card">${arr.map(fnRow).join('')}</div>`; }).join('');
}
function openTx(id){ const t = S.fn.data.tx.find(x=>x.id===id) || S.fn.data.report.top.find(x=>x.id===id); if(!t) return; const c = catOf(t);
  sheet(`<div class="meta">${esc(c.name)} · ${esc(S.fn.data.accounts?.[t.account]||'')}</div><h2 style="margin:2px 0 6px">${t.kind==='income'?'+':'−'}${money(t.amount)}</h2>
    <p class="lead">${esc(t.note||'')} · ${t.date.slice(8,10)}/${t.date.slice(5,7)}/${t.date.slice(0,4)}</p>
    <button class="btn full" style="color:var(--danger)" onclick="fnDelete('${t.id}')">${ico('trash')} Xoá giao dịch</button>`); }
async function fnDelete(id){ closeSheet(); try{ const r = await run('taichinh','xoa',{tx_id:id}); toast(r.text); moneyEnter(true); }catch(e){ toast(e.message); } }
function fnDebts(d){
  const today = new Date().toLocaleDateString('sv-SE');
  const sec = (kind, title) => { const arr = d.debts.filter(x=>x.kind===kind && x.status==='open');
    const tot = arr.reduce((a,x)=>a+x.amount-(x.paid||0),0);
    return `<div class="grp"><span>${title}</span><span>${money(tot)}</span></div><div class="card">${arr.length?arr.map(x=>{ const left = x.amount-(x.paid||0), late = x.due && x.due<today;
      return `<div class="txrow"><span class="ic">${kind==='receivable'?'↘':'↗'}</span><div class="grow"><div style="font-weight:500">${esc(x.party)}</div><div class="meta">${x.note?esc(x.note)+' · ':''}${x.due?`<span style="${late?'color:var(--danger);font-weight:600':''}">hạn ${x.due.slice(8,10)}/${x.due.slice(5,7)}${late?' (quá hạn)':''}</span>`:'không hạn'}${x.paid?` · đã ${kind==='receivable'?'thu':'trả'} ${money(x.paid)}`:''}</div></div>
        <div style="text-align:right"><div class="amt">${money(left)}</div><button class="addlink" style="font-size:13px" onclick="fnSettle('${x.id}','${kind}')">${kind==='receivable'?'Đã thu':'Đã trả'}</button></div></div>`; }).join(''):`<div class="empty">Không có khoản nào.</div>`}</div>`; };
  const done = d.debts.filter(x=>x.status==='done').slice(0,10);
  return sec('receivable','Phải thu (người khác nợ anh)') + sec('payable','Phải trả (anh nợ)') +
    `<button class="btn full" style="margin-top:14px" onclick="openAddMoney('receivable')">${ico('plus')} Thêm khoản phải thu / phải trả</button>` +
    (done.length?`<div class="grp"><span>Đã tất toán</span></div><div class="card">${done.map(x=>`<div class="txrow"><span class="ic">✓</span><div class="grow">${esc(x.party)}</div><span class="amt muted">${money(x.amount)}</span></div>`).join('')}</div>`:'');
}
function fnSettle(id, kind){ const x = S.fn.data.debts.find(y=>y.id===id); if(!x) return;
  sheet(`<h2>${kind==='receivable'?'Ghi nhận đã thu':'Ghi nhận đã trả'}</h2><p class="lead">${esc(x.party)} · còn ${money(x.amount-(x.paid||0))}. Để trống = toàn bộ. Tự ghi vào thu chi.</p>
    <label class="field"><span>Số tiền (ví dụ 2tr, 500k)</span><input type="text" id="stAmt" inputmode="decimal" placeholder="Toàn bộ"></label>
    <button class="btn pri full" onclick="fnSettleGo('${id}')">Xác nhận</button>`); }
async function fnSettleGo(id){ const a = $('#stAmt').value.trim(); closeSheet(); try{ const r = await run('taichinh','tatoan',{debt_id:id, amount:a}); toast(r.text); moneyEnter(true); }catch(e){ toast(e.message); } }
function fnBudgetHint(){ return `<div class="card pad" style="margin-top:12px"><b>Đặt ngân sách</b><p class="muted small" style="margin:6px 0 10px">Đặt mức chi tối đa mỗi tháng cho từng danh mục, superHuy cảnh báo khi dùng 80% và khi vượt.</p><button class="btn" onclick="S.fn.view='budget';render()">Đặt ngân sách</button></div>`; }
function fnBudget(d){
  const r = d.report, spent = Object.fromEntries(r.categories.map(c=>[c.id, c.spent]));
  return `<p class="muted small" style="margin:0 4px 10px">Chạm vào danh mục để đặt mức chi tối đa mỗi tháng. Tổng ngân sách: <b style="color:var(--text)">${money(r.budget_total)}</b></p>
    <div class="card">${Object.entries(d.cats.expense).map(([k,c])=>{ const b = d.budgets[k]||0, sp = spent[k]||0, p = b? sp/b : 0;
      return `<button class="txrow" onclick="fnSetBudget('${k}')"><span class="ic">${c.icon}</span><div class="grow"><div style="font-weight:500">${esc(c.name)}</div>
        ${b?`<div class="meter" style="margin-top:6px;height:6px"><i class="${p>1?'over':p>.8?'near':''}" style="width:${Math.min(100,p*100)}%"></i></div>`:''}<div class="meta">${b?`${money(sp)} / ${money(b)}`:(sp?`Đã chi ${money(sp)} · chưa đặt`:'Chưa đặt')}</div></div><span class="chev">${ico('chev',18)}</span></button>`; }).join('')}</div>`;
}
function fnSetBudget(cat){ const c = S.fn.data.cats.expense[cat], b = S.fn.data.budgets[cat]||'';
  sheet(`<h2>${c.icon} Ngân sách ${esc(c.name)}</h2><p class="lead">Mức chi tối đa mỗi tháng. Để trống để bỏ ngân sách.</p>
    <label class="field"><span>Số tiền / tháng (ví dụ 5tr, 800k)</span><input type="text" id="bgAmt" inputmode="decimal" value="${b?money(b).replace(' ',''):''}"></label>
    <button class="btn pri full" onclick="fnSetBudgetGo('${cat}')">Lưu</button>`); }
async function fnSetBudgetGo(cat){ const a = $('#bgAmt').value.trim(); closeSheet(); try{ const r = await run('taichinh','ngansach',{category:cat, amount:a}); toast(r.text); moneyEnter(true); }catch(e){ toast(e.message); } }
function bindFnQuick(){
  tipBind($('#app'));
  const i = $('#fnQuick'), b = $('#fnQuickBtn'); if(!i) return;
  i.onkeydown = e => { if(e.key==='Enter'){ e.preventDefault(); b.click(); } };
  b.onclick = async () => { const t = i.value.trim(); if(!t) return openAddMoney();
    b.disabled = true; b.innerHTML = '<span class="spin"></span>';
    try{ const r = await run('taichinh','ghi',{text:t},'superHuy đang ghi'); i.value = ''; toast(r.text, 4200); haptic('medium'); S.fn.month = ''; moneyEnter(true); S.fn.at = 0; }
    catch(e){ toast(e.message); }
    b.disabled = false; b.innerHTML = ico('spark',17); };
}
function openAddMoney(kind){
  S.nm = {kind: kind||'expense', amount:'', category:'', note:'', date:new Date().toLocaleDateString('sv-SE'), account:'bank', party:'', due:''};
  sheet(`<h2>Ghi thu chi</h2><div class="seg" id="nmKind" style="margin:4px 0 16px"></div>
    <label class="field"><span>Số tiền (45k, 1tr2, 80tr…)</span><input type="text" id="nmAmt" inputmode="decimal" placeholder="0" style="font-size:22px;font-weight:700"></label>
    <div id="nmBody"></div><button class="btn pri full" id="nmSave">Lưu</button>`);
  paintNm();
  $('#nmSave').onclick = async () => {
    const n = S.nm; n.amount = $('#nmAmt').value.trim(); n.note = ($('#nmNote')?.value||'').trim(); n.party = ($('#nmParty')?.value||'').trim();
    if(!n.amount) return toast('Nhập số tiền');
    if((n.kind==='receivable'||n.kind==='payable') && !n.party) return toast('Ghi tên người hoặc đơn vị');
    const b = $('#nmSave'); b.disabled = true; b.innerHTML = '<span class="spin"></span>';
    try{ const r = await run('taichinh','them',{...n}); closeSheet(); toast(r.text, 4200); haptic('medium'); moneyEnter(true); }catch(e){ toast(e.message); b.disabled = false; b.textContent = 'Lưu'; }
  };
}
function paintNm(){
  const n = S.nm, c = S.fn.data?.cats || {expense:{}, income:{}};
  $('#nmKind').innerHTML = [['expense','Chi'],['income','Thu'],['receivable','Phải thu'],['payable','Phải trả']].map(([k,l])=>`<button class="${n.kind===k?'on':''}" onclick="S.nm.kind='${k}';S.nm.category='';paintNm()">${l}</button>`).join('');
  const note = ($('#nmNote')?.value)||'';
  if(n.kind==='receivable' || n.kind==='payable'){
    $('#nmBody').innerHTML = `<label class="field"><span>${n.kind==='receivable'?'Ai nợ anh':'Anh nợ ai'}</span><input type="text" id="nmParty" placeholder="Tên người / công ty"></label>
      <p class="lbl">Hạn</p><div class="inrow"><input type="date" value="${n.due}" onchange="S.nm.due=this.value"></div>
      <label class="field"><span>Ghi chú</span><input type="text" id="nmNote" value="${esc(note)}"></label>`;
  } else {
    const cats = n.kind==='income' ? c.income : c.expense;
    $('#nmBody').innerHTML = `<p class="lbl">Danh mục</p><div class="cats">${Object.entries(cats).map(([k,v])=>`<button class="${n.category===k?'on':''}" onclick="S.nm.category='${k}';paintNm()"><span>${v.icon}</span>${esc(v.name)}</button>`).join('')}</div>
      <label class="field"><span>Ghi chú</span><input type="text" id="nmNote" value="${esc(note)}" placeholder="${n.kind==='income'?'Lương tháng 10':'Ăn trưa với đối tác'}"></label>
      <p class="lbl">Ngày và tài khoản</p><div class="inrow"><input type="date" value="${n.date}" onchange="S.nm.date=this.value"><select onchange="S.nm.account=this.value" style="padding:9px 12px;border-radius:12px;border:0;box-shadow:0 0 0 1px var(--line);background:var(--surface);color:var(--text);font:inherit">${Object.entries(S.fn.data?.accounts||{bank:'Ngân hàng'}).map(([k,v])=>`<option value="${k}" ${n.account===k?'selected':''}>${esc(v)}</option>`).join('')}</select></div>`;
  }
}

/* =================================================================== PHÁT TRIỂN */
const KINDP = {meeting:'Lịch họp', focus:'Làm sâu', task:'Việc', habit:'Thói quen', workout:'Tập', meal:'Ăn', rest:'Nghỉ', family:'Gia đình', learn:'Học', admin:'Tin nhắn'};
async function growthEnter(force){
  if(S.gr.loading) return;
  if(!force && S.gr.data && Date.now()-S.gr.at < 20000) return;
  S.gr.loading = true;
  try{ S.gr.data = await run('phattrien','tongquan',{},'',true); S.gr.at = Date.now();
    const day = S.gr.planDay || new Date().toLocaleDateString('sv-SE');
    const p = await run('phattrien','xem_lichtrinh',{date:day},'',true); S.gr.plan = p.plan || null; }catch(e){ toast(e.message); }
  S.gr.loading = false; if(S.tab==='growth' && !document.querySelector('#sheet.on')) render();
}
function pring(done, due){ const r = 32, c = 2*Math.PI*r, f = due ? done/due : 0;
  return `<div class="pring" role="img" aria-label="${done} trên ${due} thói quen"><svg width="76" height="76" viewBox="0 0 76 76"><circle class="trk" cx="38" cy="38" r="${r}" fill="none" stroke-width="8"/>${f>0?`<circle class="val" cx="38" cy="38" r="${r}" fill="none" stroke-width="8" stroke-linecap="round" stroke-dasharray="${c*f} ${c}"/>`:''}</svg><b>${done}/${due}</b></div>`; }
function vGrowth(){
  const d = S.gr.data, v = S.gr.view;
  const head = `<div class="date">${S.gr.loading?'<span class="spin" style="width:12px;height:12px;display:inline-block;vertical-align:-1px"></span> Đang tải…':'Mục tiêu, thói quen và lịch trình của anh'}</div><h1>Phát triển</h1>
    <div class="seg segscroll" style="margin-bottom:14px">${[['today','Hôm nay'],['learn','Học tập'],['goals','Mục tiêu'],['habits','Thói quen'],['mind','Hiểu anh']].map(([k,l])=>`<button class="${v===k?'on':''}" onclick="S.gr.view='${k}';render()">${l}</button>`).join('')}</div>`;
  if(!d) return head + `<div class="card pad"><div class="skel" style="width:60%"></div><div class="skel"></div></div>`;
  setTimeout(()=>tipBind($('#app')), 0);
  if(v!=='learn' || true){ const gh = gmHeader(); if(gh) return head.replace('<div class="seg segscroll"', gh + '<div class="seg segscroll"') + ({today:grToday, learn:grLearn, goals:grGoals, habits:grHabits, mind:grMind})[v](d); }
  return head + ({today:grToday, learn:grLearn, goals:grGoals, habits:grHabits, mind:grMind})[v](d);
}

/* ---------- Học tập: khoá học, bài mỗi ngày, audio, quiz, ôn tập, thực hành */
const LKIND = {learn:'Học', practice:'Thực hành', review:'Ôn tập', project:'Dự án'};
function grLearn(){
  if(!S.lr){ lrLoad(); return `<div class="card pad"><div class="skel" style="width:60%"></div><div class="skel"></div></div>`; }
  const cs = S.lr.courses||[];
  return `<p class="lead" style="margin:0 0 12px">Mỗi ngày 30-60 phút: đọc hoặc nghe bài, làm quiz để nhớ lâu, rồi thực hành ngay trên Leversphere và Sellnity. Câu sai tự quay lại theo lịch ôn giãn cách.</p>
    ${cs.map(c=>{ const pct = Math.round(100*c.done/c.total);
      return `<article class="card pad lcourse"><div class="row" style="align-items:center;gap:8px"><span class="itype">${c.total} ngày</span>${c.streak?`<span class="fire">🔥 ${c.streak} ngày liền</span>`:''}<span class="grow"></span><button class="link" onclick="lrCourse('${c.id}')">Lộ trình</button></div>
        <h3>${esc(c.title)}</h3><div class="pbar"><i style="width:${pct}%"></i></div><div class="meta">Đã xong ${c.done}/${c.total} ngày${c.avg_quiz!==null?` · quiz trung bình ${c.avg_quiz}/10`:''}</div>
        <button class="lnext" onclick="lrDay('${c.id}',${c.today})"><span class="lday">Ngày ${c.today}</span><span class="grow"><b>${esc(c.today_title)}</b><span class="meta" style="display:block;margin:2px 0 0">Bài học · audio · quiz · thực hành</span></span>${ico('chev',18)}</button>
        ${c.review_due?`<button class="btn full" style="margin-top:8px" onclick="lrReview('${c.id}')">${ico('refresh',16)} Ôn ${c.review_due} câu đến hạn</button>`:''}</article>`; }).join('')}
    ${cs.length?'':`<div class="card empty">Chưa có khoá học nào. Tạo khoá đầu tiên bên dưới.</div>`}
    <button class="btn pri full" style="margin-top:12px" onclick="lrNew()">${ico('plus',16)} Tạo khoá học mới</button>`;
}
async function lrLoad(){ try{ S.lr = await run('hoc','tongquan',{},'',true); }catch(e){ S.lr = {courses:[]}; toast(e.message); } if(S.tab==='growth' && S.gr.view==='learn' && !$('#sheet').classList.contains('on')) render(); }
function lrNew(){
  S.ln = {days:30, tpl:''};
  const paint = () => { const n = S.ln; sheet(`<h2>Tạo khoá học</h2><p class="lead">superHuy thiết kế lộ trình theo ngày, soạn bài, audio, quiz và bài thực hành áp dụng cho Leversphere và Sellnity.</p>
    <p class="lbl">Mẫu có sẵn</p><div class="chips" style="padding-top:0;flex-wrap:wrap;margin-bottom:12px">${Object.entries(S.lr?.templates||{}).map(([k,l])=>`<button class="chip ${n.tpl===k?'on':''}" onclick="S.ln.tpl=S.ln.tpl==='${k}'?'':'${k}';S.lnp()">${esc(l)}</button>`).join('')}</div>
    ${n.tpl?'':`<label class="field"><span>Chủ đề</span><input type="text" id="lnTopic" value="${esc(n.topic||'')}" placeholder="Ví dụ: Quảng cáo TikTok Shop cho POD, Tài chính cho CEO, n8n tự động hoá"></label>
    <label class="field"><span>Mục tiêu đầu ra</span><textarea id="lnGoal" placeholder="Ví dụ: tự dựng được 3 luồng tự động hoá chăm sóc khách cho Leversphere">${esc(n.goal||'')}</textarea></label>
    <label class="field"><span>Trình độ hiện tại</span><input type="text" id="lnLevel" value="${esc(n.level||'')}" placeholder="Mới bắt đầu / đã biết cơ bản…"></label>
    <label class="field"><span>Tài liệu, repo tham khảo (không bắt buộc, mỗi link 1 dòng)</span><textarea id="lnSrc" placeholder="https://github.com/...">${esc(n.src||'')}</textarea></label>
    <p class="lbl">Thời lượng</p><div class="seg" style="margin-bottom:12px">${[7,14,30].map(x=>`<button class="${n.days===x?'on':''}" onclick="S.ln.days=${x};S.lnp()">${x} ngày</button>`).join('')}</div>`}
    <button class="btn pri full" id="lnGo" onclick="lrCreate()">${ico('spark',16)} Thiết kế khoá học</button>`); };
  S.lnp = () => { ['topic','goal','level','src'].forEach(k=>{ const el = $('#ln'+k[0].toUpperCase()+k.slice(1)); if(el) S.ln[k] = el.value; }); paint(); }; paint();
}
async function lrCreate(){
  S.lnp(); const n = S.ln; if(!n.tpl && !(n.topic||'').trim()) return toast('Anh nhập chủ đề');
  const b = $('#lnGo'); b.disabled = true; b.textContent = 'superHuy đang thiết kế lộ trình…';
  try{ const r = await run('hoc','tao',{topic:n.topic||'', goal:n.goal||'', days:n.days, level:n.level||'', sources:n.src||'', template:n.tpl||''},'Thiết kế khoá học'); closeSheet(); toast(r.text, 4000); S.lr = null; render(); }
  catch(e){ toast(e.message); b.disabled = false; b.textContent = 'Thiết kế khoá học'; }
}
async function lrCourse(cid){
  try{ const c = await run('hoc','khoa',{cid},'',true);
    sheet(`<div class="meta" style="margin-bottom:4px">${c.done}/${c.total} ngày · bắt đầu ${esc(c.start.split('-').reverse().join('/'))}</div><h2 style="margin-bottom:6px">${esc(c.title)}</h2>
      <p class="lead" style="margin:0 0 10px">${esc(c.goal)}</p>
      ${(c.sources||[]).length?`<div class="meta" style="margin-bottom:10px">Nguồn: ${c.sources.map(x=>`<a href="#" onclick="event.preventDefault();openLink('${esc(x.url)}')">${esc(x.title)}</a>`).join(' · ')}</div>`:''}
      <div class="card list">${c.days.map(d=>`<button onclick="lrDay('${cid}',${d.day})"><span class="ldot ${d.status==='done'?'on':d.status==='learning'?'half':''}">${d.status==='done'?ico('check',14):d.day}</span>
        <div class="grow"><div style="font-weight:${d.day===c.today?700:500}">${esc(d.title)}</div><div class="meta">${LKIND[d.kind]||''}${d.quiz_score!=null?` · quiz ${d.quiz_score}/10`:''}${d.best?` · bài ${d.best}/10`:''}${d.day===c.today?' · hôm nay':''}</div></div><span class="chev">${ico('chev',18)}</span></button>`).join('')}</div>
      <button class="btn full" style="margin-top:12px;color:var(--danger)" onclick="lrArchive('${cid}')">Lưu trữ khoá này</button>`);
  }catch(e){ toast(e.message); }
}
async function lrArchive(cid){ try{ await run('hoc','luu_tru',{cid},'',true); closeSheet(); S.lr = null; render(); }catch(e){ toast(e.message); } }
async function lrDay(cid, day){
  sheet(`<h2>Ngày ${day}</h2><div class="card pad"><div class="spin"></div><p class="meta">superHuy đang chuẩn bị bài học (lần đầu mất khoảng 30-60 giây)…</p></div>`);
  try{ S.ld = await run('hoc','ngay',{cid, day},'',true); S.ld.ans = {}; lrPaint(); }catch(e){ closeSheet(); toast(e.message); }
}
function lrPaint(keep){
  const d = S.ld, L = d.lesson||{}, P = L.practice||{}, y = $('#sheet').scrollTop;
  const qz = (L.quiz||[]).map((q,i)=>{ const r = d.qres?.detail?.find(x=>x.id===q.id);
    return `<div class="lq"><div class="lqq">${i+1}. ${esc(q.q)}</div>${q.options.map((o,k)=>`<label class="lqo ${r?(k===r.answer?'right':(d.ans[q.id]===k?'wrong':'')):''}"><input type="radio" name="q${q.id}" ${d.ans[q.id]===k?'checked':''} ${r?'disabled':''} onchange="S.ld.ans['${q.id}']=${k}"><span>${esc(o)}</span></label>`).join('')}
      ${r?`<div class="meta" style="margin:4px 0 0">${r.ok?'✓ Đúng':'✗ Chưa đúng'} — ${esc(r.explain)}</div>`:''}</div>`; }).join('');
  const subs = (d.submissions||[]).slice().reverse();
  sheet(`<div class="meta" style="margin-bottom:4px">${esc(d.course)} · Ngày ${d.day}/${d.total} · ${LKIND[d.kind]||''}</div><h2 style="margin-bottom:10px">${esc(d.title)}</h2>
    ${(L.objectives||[]).length?`<div class="note" style="margin-bottom:12px"><b>Mục tiêu buổi học</b><ul style="margin:6px 0 0;padding-left:18px">${L.objectives.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`:''}
    <div class="card pad laudio">${L.audio?`<div class="meta" style="margin:0 0 6px">Bài giảng audio · nghe khi lái xe, tập thể dục</div><audio controls preload="none" src="${L.audio}" style="width:100%"></audio>`
      :`<div class="row" style="align-items:center"><span class="grow meta" style="margin:0">Bài giảng audio 3-5 phút</span><button class="btn sm" id="lrAud" onclick="lrAudio()">${ico('play',14)} Tạo audio</button></div>`}</div>
    <div class="mdbody" style="margin-top:12px">${mdRender(L.md||'')}</div>
    ${(L.key_points||[]).length?`<div class="mblk dec"><h3>${ico('check',16)} Ý cần nhớ</h3><ul>${L.key_points.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`:''}
    ${(L.resources||[]).length?`<div class="sec" style="margin-top:6px"><h2 style="font-size:17px">Tài liệu & video</h2></div><div class="card list">${L.resources.map(r=>`<button onclick="openLink('${esc(r.url)}')"><span class="thumb">${ico(r.type==='video'?'play':'link',18)}</span><div class="grow"><div style="font-weight:600">${esc(r.title)}</div><div class="meta">${r.type==='video'?'Tìm video trên YouTube':'Mở tài liệu'}</div></div></button>`).join('')}</div>`:''}
    <div class="sec"><h2 style="font-size:17px">Quiz ôn bài</h2>${d.quiz_score!=null?`<span class="meta">Điểm cao nhất ${d.quiz_score}/10</span>`:''}</div>
    <div class="card pad">${qz||'<div class="meta">Không có quiz.</div>'}${(L.quiz||[]).length?`<div class="row" style="margin-top:10px">${d.qres?`<b class="grow">${esc(d.qres.text)}</b><button class="btn sm" onclick="S.ld.qres=null;S.ld.ans={};lrPaint()">Làm lại</button>`:`<button class="btn pri full" onclick="lrQuiz()">Nộp quiz</button>`}</div>`:''}</div>
    ${P.task?`<div class="sec"><h2 style="font-size:17px">Thực hành · ${esc(P.context||'')}</h2>${d.best?`<span class="meta">Điểm cao nhất ${d.best}/10</span>`:''}</div>
    <div class="card pad"><p style="margin:0 0 8px;font-weight:600">${esc(P.task)}</p>${(P.steps||[]).length?`<ol style="margin:0 0 8px;padding-left:18px">${P.steps.map(x=>`<li>${esc(x)}</li>`).join('')}</ol>`:''}
      <div class="meta" style="margin:0 0 4px"><b>Nộp:</b> ${esc(P.deliverable||'')}</div>${(P.rubric||[]).length?`<div class="meta" style="margin:0"><b>Tiêu chí chấm:</b> ${P.rubric.map(esc).join(' · ')}</div>`:''}</div>
    <label class="field" style="margin-top:12px"><span>Bài làm của anh</span><textarea id="lrText" style="min-height:160px" placeholder="Dán kết quả, nội dung file, câu lệnh, ảnh chụp mô tả… ">${esc(S.ldDraft||'')}</textarea></label>
    <label class="field"><span>Link (Google Docs, GitHub, Sheets… không bắt buộc)</span><input type="url" id="lrLink" placeholder="https://"></label>
    <label class="field"><span>Phản tư: ${esc(L.reflection||'Hôm nay anh rút ra điều gì?')}</span><textarea id="lrRef"></textarea></label>
    <button class="btn pri full" id="lrGo" onclick="lrSubmit()">${ico('send',16)} Nộp bài để superHuy chấm</button>`:''}
    ${subs.map(s=>{ const g = s.grade||{}; return `<div class="card pad lgrade"><div class="row" style="align-items:center"><b class="grow">Điểm ${g.score}/10 · ${g.pass?'Đạt':'Chưa đạt'}</b><span class="meta" style="margin:0">${esc(ago(s.at))}</span></div>
      ${(g.criteria||[]).map(c=>`<div class="meta" style="margin:6px 0 0"><b style="color:var(--text)">${esc(c.name)}: ${c.score}/10</b> — ${esc(c.comment)}</div>`).join('')}
      ${(g.strengths||[]).length?`<div style="margin-top:8px"><b>Làm tốt:</b> ${g.strengths.map(esc).join('; ')}</div>`:''}
      ${(g.improve||[]).length?`<div style="margin-top:6px"><b>Cần sửa:</b><ul style="margin:4px 0 0;padding-left:18px">${g.improve.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></div>`:''}
      ${g.next?`<div class="note" style="margin-top:8px">${esc(g.next)}</div>`:''}${s.note?`<div class="meta">Đã lưu Obsidian: ${esc(s.note)}</div>`:''}</div>`; }).join('')}
    <div class="row" style="margin-top:12px">${d.status!=='done'?`<button class="btn grow" onclick="lrDone()">${ico('check',16)} Đánh dấu đã học xong</button>`:'<span class="meta grow">✓ Đã hoàn thành ngày này</span>'}${d.day<d.total?`<button class="btn grow" onclick="lrDay('${d.cid}',${d.day+1})">Ngày ${d.day+1} ${ico('chev',14)}</button>`:''}</div>`);
  if(keep) $('#sheet').scrollTop = y;
}
async function lrAudio(){ const b = $('#lrAud'); b.disabled = true; b.textContent = 'Đang tạo…';
  try{ const r = await run('hoc','audio',{cid:S.ld.cid, day:S.ld.day},'',true); S.ld.lesson.audio = r.audio; lrPaint(true); }catch(e){ toast(e.message); b.disabled = false; } }
async function lrQuiz(){
  const n = (S.ld.lesson.quiz||[]).length; if(Object.keys(S.ld.ans).length < n) return toast('Anh trả lời hết các câu trước nhé');
  try{ S.ld.qres = await run('hoc','quiz',{cid:S.ld.cid, day:S.ld.day, answers:JSON.stringify(S.ld.ans)},'',true); S.ld.quiz_score = Math.max(S.ld.quiz_score||0, S.ld.qres.score); notifyH(S.ld.qres.right===n?'success':'warning'); lrPaint(true); S.lr = null; }
  catch(e){ toast(e.message); }
}
async function lrSubmit(){
  const text = $('#lrText').value.trim(), link = $('#lrLink').value.trim(), reflection = $('#lrRef').value.trim();
  if(text.length < 20 && !link) return toast('Anh dán bài làm (hoặc link) trước khi nộp');
  S.ldDraft = text; const b = $('#lrGo'); b.disabled = true; b.textContent = 'superHuy đang chấm bài…';
  try{ const r = await run('hoc','nop',{cid:S.ld.cid, day:S.ld.day, text, link, reflection},'Chấm bài thực hành'); toast(r.text, 4500); S.ldDraft = ''; S.lr = null;
    S.ld = {...(await run('hoc','ngay',{cid:S.ld.cid, day:S.ld.day},'',true)), ans:S.ld.ans, qres:S.ld.qres}; lrPaint(true); }
  catch(e){ toast(e.message, 5000); b.disabled = false; b.textContent = 'Nộp bài để superHuy chấm'; }
}
async function lrDone(){ try{ await run('hoc','xong',{cid:S.ld.cid, day:S.ld.day},'',true); S.ld.status = 'done'; S.lr = null; toast('Đã xong ngày '+S.ld.day+' 🔥'); notifyH('success'); lrPaint(true); }catch(e){ toast(e.message); } }
async function lrReview(cid){
  try{ const r = await run('hoc','on_tap',{cid},'',true); S.lv = {cid, items:r.items, ans:{}};
    if(!r.items.length) return toast('Không có câu nào đến hạn ôn');
    const paint = () => sheet(`<h2>Ôn tập giãn cách</h2><p class="lead">Câu anh từng làm sai. Trả lời đúng thì lần ôn sau giãn ra (1 → 3 → 7 → 14 ngày).</p>
      <div class="card pad">${S.lv.items.map((q,i)=>`<div class="lq"><div class="meta" style="margin:0">Ngày ${q.day}</div><div class="lqq">${i+1}. ${esc(q.q)}</div>${q.options.map((o,k)=>`<label class="lqo"><input type="radio" name="rv${q.id}" onchange="S.lv.ans['${q.id}']=${k}"><span>${esc(o)}</span></label>`).join('')}</div>`).join('')}</div>
      <button class="btn pri full" style="margin-top:12px" onclick="lrReviewGo()">Nộp ôn tập</button>`);
    paint();
  }catch(e){ toast(e.message); }
}
async function lrReviewGo(){ try{ const r = await run('hoc','on_tap_nop',{cid:S.lv.cid, answers:JSON.stringify(S.lv.ans)},'',true); closeSheet(); toast(r.text, 4500); S.lr = null; render(); }catch(e){ toast(e.message); } }

/* ---------- Hành trình game hoá: XP, cấp độ, vàng, nhiệm vụ, huy hiệu, vật phẩm, phần thưởng */
function xpPop(g){
  if(!g || !g.xp) return; S.gm = null;
  const el = document.createElement('div'); el.className = 'xppop';
  el.innerHTML = `<b>+${g.xp} XP</b><span>+${g.gold} vàng · ${esc(g.note||'')}</span>${(g.extra||[]).map(x=>`<em>${esc(x)}</em>`).join('')}${g.level_up?`<strong>⬆️ Lên cấp ${g.level_up.level}: ${esc(g.level_up.title)}!</strong>`:''}${(g.badges||[]).length?`<strong>🏅 Huy hiệu mới!</strong>`:''}`;
  document.body.appendChild(el); haptic(g.level_up?'heavy':'medium'); if(g.level_up) notifyH('success');
  setTimeout(()=>el.classList.add('out'), g.level_up||(g.extra||[]).length ? 3600 : 2000); setTimeout(()=>el.remove(), 4400);
  if(S.tab==='growth') setTimeout(()=>gmLoad(), 400);
}
async function gmLoad(){ try{ S.gm = await run('game','hoso',{},'',true); if(S.tab==='growth' && !$('#sheet').classList.contains('on')) render(); else if($('#gmSheet')) gmOpen(S.gmTab); }catch(e){} }
function gmHeader(){
  const g = S.gm; if(!g){ if(!S.gmLoading){ S.gmLoading = true; gmLoad().finally(()=>S.gmLoading=false); } return ''; }
  const lv = g.level, pct = Math.round(lv.progress*100), qd = g.quests.filter(q=>q.claimed).length;
  return `<button class="gmhead" onclick="gmOpen()"><span class="gmlv"><b>${lv.level}</b><i>cấp</i></span>
    <span class="grow" style="min-width:0"><span class="row" style="align-items:baseline;gap:8px"><b class="gmtitle">${esc(lv.title)}</b><span class="meta" style="margin:0">${g.xp} XP</span>${g.boost_until?'<span class="gmboost">x2 XP</span>':''}</span>
      <span class="gmbar"><i style="width:${pct}%"></i></span><span class="meta" style="margin:2px 0 0;display:block">Còn ${lv.next-g.xp} XP lên cấp ${lv.level+1}${g.xp_today?` · hôm nay +${g.xp_today}`:''} · nhiệm vụ ${qd}/${g.quests.length}</span></span>
    <span class="gmgold">🪙 ${g.gold}</span></button>`;
}
function gmOpen(tab){
  const g = S.gm; if(!g) return gmLoad();
  S.gmTab = tab || S.gmTab || 'quest';
  const lv = g.level, t = S.gmTab;
  const body = {
    quest: () => `<div class="card list">${g.quests.map(q=>`<div style="align-items:center"><span class="gmq ${q.claimed?'on':''}">${q.claimed?'✓':`${q.done}/${q.n}`}</span><div class="grow"><div style="font-weight:600">${esc(q.t)}</div><div class="meta">+${q.xp} XP</div></div></div>`).join('')}</div>
      <p class="meta" style="margin:8px 0 14px">Xong cả 3 nhiệm vụ: +50 XP và 1 rương 🎁</p>
      <div class="card pad"><b>Thử thách tuần ${g.weekly.done?'✓':''}</b><div class="meta" style="margin:4px 0 8px">${esc(g.weekly.text)} · thưởng 150 XP + Bình x2 XP</div>
      ${Object.entries(g.weekly.goal).map(([k,n])=>`<div class="row" style="align-items:center;gap:8px;margin:4px 0"><span style="width:110px" class="meta">${{lesson:'Ngày học',habit:'Check-in',task:'Việc xong'}[k]}</span><span class="gmbar grow"><i style="width:${Math.round(100*g.weekly.progress[k]/n)}%"></i></span><span class="meta" style="margin:0">${g.weekly.progress[k]}/${n}</span></div>`).join('')}</div>
      <p class="lbl" style="margin-top:14px">Cách nhận XP</p><div class="card list">${Object.entries(g.xp_table).map(([k,v])=>`<div><span class="grow">${esc(v[1])}</span><b>+${v[0]}</b></div>`).join('')}</div>`,
    badge: () => `<div class="gmbadges">${g.badges.map(b=>`<div class="gmbadge ${b.at?'on':''}"><span>${b.icon}</span><b>${esc(b.name)}</b><em>${b.at?'Đạt '+b.at.split('-').reverse().join('/'):esc(b.desc)}</em></div>`).join('')}</div>`,
    bag: () => `<div class="card list">${g.items.map(it=>`<div style="align-items:center"><span class="gmitem">${it.icon}</span><div class="grow"><div style="font-weight:600">${esc(it.name)} <span class="meta" style="margin:0">×${it.qty}</span></div><div class="meta">${esc(it.desc)}</div></div>
      ${it.qty&&['potion','chest'].includes(it.id)?`<button class="btn sm pri" onclick="gmUse('${it.id}')">${it.id==='chest'?'Mở':'Dùng'}</button>`:''}${it.price?`<button class="btn sm" onclick="gmBuy('${it.id}')">🪙 ${it.price}</button>`:''}</div>`).join('')}</div>
      <p class="meta" style="margin:8px 0 0">Lên cấp nhận rương; mỗi 3 cấp thêm 1 Khiên chuỗi. Khiên tự giữ chuỗi thói quen khi anh lỡ 1 ngày.</p>`,
    shop: () => `<p class="lead" style="margin:0 0 10px">Đổi vàng lấy phần thưởng thật anh tự đặt cho mình.</p><div class="card list">${g.rewards.map(r=>`<div style="align-items:center"><span class="gmitem">${r.icon}</span><div class="grow"><div style="font-weight:600">${esc(r.name)}</div><div class="meta">🪙 ${r.price}${g.gold<r.price?` · còn thiếu ${r.price-g.gold}`:''}</div></div>
      <button class="btn sm ${g.gold>=r.price?'pri':''}" ${g.gold>=r.price?'':'disabled'} onclick="gmRedeem('${r.id}')">Đổi</button><button class="iconbtn sm" aria-label="Xoá" onclick="gmDelReward('${r.id}')">${ico('x',15)}</button></div>`).join('')}</div>
      <div class="row" style="margin-top:10px;gap:8px"><input id="gmRn" class="grow gminp" placeholder="Phần thưởng mới, vd: Ăn tối nhà hàng yêu thích"><input id="gmRp" class="gminp" style="width:90px" type="number" placeholder="Vàng"><button class="btn" onclick="gmAddReward()">${ico('plus',15)}</button></div>
      ${(g.redeemed||[]).length?`<p class="lbl" style="margin-top:14px">Đã đổi gần đây</p><div class="card list">${g.redeemed.slice().reverse().map(r=>`<div><span class="grow">${r.icon} ${esc(r.name)}</span><span class="meta" style="margin:0">${esc(ago(r.at))}</span></div>`).join('')}</div>`:''}`,
    log: () => `<div class="card list">${g.log.map(x=>`<div><div class="grow"><div>${esc(x.note)}</div><div class="meta">${esc(ago(x.at))}${x.boost?' · x2':''}</div></div>${x.xp?`<b style="color:var(--jade)">+${x.xp}</b>`:x.gold<0?`<b>${x.gold} 🪙</b>`:''}</div>`).join('')||'<div class="empty">Chưa có hoạt động.</div>'}</div>`,
  };
  sheet(`<div id="gmSheet"><div class="gmhero"><span class="gmlv big"><b>${lv.level}</b><i>cấp</i></span><div class="grow"><div class="gmtitle" style="font-size:20px">${esc(lv.title)}</div>
      <div class="gmbar" style="margin:6px 0 4px"><i style="width:${Math.round(lv.progress*100)}%"></i></div><div class="meta" style="margin:0">${g.xp} / ${lv.next} XP · 🪙 ${g.gold} vàng${g.boost_until?' · x2 XP đang bật':''}</div></div></div>
    <div class="seg segscroll" style="margin:12px 0">${[['quest','Nhiệm vụ'],['badge','Huy hiệu'],['bag','Túi đồ'],['shop','Thưởng'],['log','Nhật ký']].map(([k,l])=>`<button class="${t===k?'on':''}" onclick="gmOpen('${k}')">${l}</button>`).join('')}</div>
    ${body[t]()}</div>`);
}
async function gmUse(id){ try{ const r = await run('game','dung',{item:id},'',true); S.gm = r; toast(r.text, 3500); haptic('heavy'); gmOpen('bag'); }catch(e){ toast(e.message); } }
async function gmBuy(id){ try{ const r = await run('game','mua',{item:id},'',true); S.gm = r; toast(r.text); gmOpen('bag'); }catch(e){ toast(e.message); } }
async function gmRedeem(id){ try{ const r = await run('game','doi_thuong',{rid:id},'',true); S.gm = r; toast(r.text, 4000); notifyH('success'); gmOpen('shop'); }catch(e){ toast(e.message, 3500); } }
async function gmDelReward(id){ try{ S.gm = await run('game','xoa_thuong',{rid:id},'',true); gmOpen('shop'); }catch(e){ toast(e.message); } }
async function gmAddReward(){ const n = $('#gmRn').value.trim(), p = +$('#gmRp').value; if(!n || !p) return toast('Nhập tên và số vàng'); try{ S.gm = await run('game','them_thuong',{name:n, price:p},'',true); gmOpen('shop'); }catch(e){ toast(e.message); } }
function habitRow(h, compact){
  const unit = h.schedule?.type==='weekly' ? 'tuần' : 'ngày';
  const sub = [h.time, h.target, h.schedule?.type==='weekly'?`${h.week_count||0}/${h.schedule.times} lần tuần này`:''].filter(Boolean).join(' · ');
  return `<div class="hrow"><button class="tick ${h.done_today?'on':''}" aria-label="${h.done_today?'Bỏ đánh dấu':'Đánh dấu đã làm'}" onclick="grCheck('${h.id}', ${!h.done_today})">${ico('check',16)}</button>
    <button class="grow" style="text-align:left" onclick="openHabit('${h.id}')"><div style="font-weight:500">${esc(h.title)}</div><div class="meta">${esc(sub||h.sched)}</div>${compact?'':`<div class="dots28" aria-hidden="true">${h.last28.map(x=>`<i class="${x?'on':''}"></i>`).join('')}</div>`}</button>
    ${h.streak?`<span class="fire">🔥 ${h.streak} ${unit}</span>`:''}</div>`;
}
function grToday(d){
  const due = d.habits.filter(h=>h.due_today), p = S.gr.plan, today = new Date().toLocaleDateString('sv-SE');
  const day = S.gr.planDay || today;
  const planCard = p ? `<div class="card" style="margin-top:12px"><div class="pad" style="padding-bottom:8px"><div class="row" style="flex-wrap:nowrap"><b class="grow">🗓 Lịch trình ${day===today?'hôm nay':'ngày mai'}</b><button class="addlink" onclick="grPlan()">Lập lại</button></div>
      <p class="muted small" style="margin:6px 0 0">${esc(p.summary||'')}</p>${p.focus?`<p style="margin:8px 0 0;font-size:14px"><b>🎯 Trọng tâm:</b> ${esc(p.focus)}</p>`:''}</div>
      <div>${p.blocks.map((b,i)=>`<label class="blk ${b.fixed?'fixed':''}"><span class="t">${b.start}<small>${b.end}</small></span><span><span class="k">${KINDP[b.kind]||b.kind}</span><span class="ttl">${esc(b.title)}</span>${b.note?`<div class="meta">${esc(b.note)}</div>`:''}</span>${b.fixed?'<span class="meta">📌</span>':b.added?'<span class="meta">✓ lịch</span>':`<input type="checkbox" data-i="${i}" ${['focus','workout','learn','task','family'].includes(b.kind)?'checked':''} aria-label="Đưa vào Google Calendar">`}</label>`).join('')}</div>
      <div class="pad" style="padding-top:8px"><button class="btn pri full" onclick="grApply()">${ico('calendar')} Đưa khối đã chọn vào Google Calendar</button></div></div>`
    : `<div class="card pad" style="margin-top:12px"><b>🗓 Lịch trình ngày do superHuy lập</b><p class="muted small" style="margin:6px 0 10px">Ghép lịch họp, việc tới hạn, thói quen và 3 mục tiêu của anh thành thời khoá biểu tối ưu. Anh chọn khối nào thì đưa vào Google Calendar.</p>
      <div class="nl" style="margin-bottom:10px"><input id="grNote" placeholder="Ghi chú: hôm nay mệt, ưu tiên chốt KPI…"></div>
      <div class="row"><button class="btn pri" onclick="grPlan()">${ico('spark',17)} Lập cho hôm nay</button><button class="btn" onclick="grPlan(1)">Ngày mai</button></div></div>`;
  return `<div class="card ringwrap">${pring(d.today_done, d.today_due)}<div><b style="font-size:16px">${d.today_done===d.today_due&&d.today_due?'Hoàn thành thói quen hôm nay 🔥':'Thói quen hôm nay'}</b><div class="muted small">${d.today_due-d.today_done?`Còn ${d.today_due-d.today_done} việc tốt. Chạm vòng tròn để đánh dấu.`:'Giữ chuỗi ngày nhé.'}</div></div></div>
    <div class="card" style="margin-top:12px">${due.length?due.map(h=>habitRow(h,true)).join(''):'<div class="empty">Hôm nay không có thói quen nào đến lịch.</div>'}</div>
    ${planCard}
    <div class="sec"><h2>Mục tiêu</h2><button class="link" onclick="S.gr.view='goals';render()">Tất cả</button></div>
    ${d.goals.map(goalCard).join('<div style="height:10px"></div>')}`;
}
function goalCard(g){
  const m = g.metric||{}, pct = g.progress===null||g.progress===undefined ? null : Math.round(g.progress*100);
  return `<button class="card goal" onclick="openGoal('${g.id}')"><div class="row" style="flex-wrap:nowrap;align-items:flex-start"><span class="grow" style="font-weight:600;line-height:1.35">${esc(g.title)}</span>${g.days_left!==null&&g.days_left!==undefined?`<span class="sx">${g.days_left>=0?'còn '+g.days_left+' ngày':'quá hạn'}</span>`:''}</div>
    ${m.name?`${pct!==null?`<div class="pbar"><i style="width:${pct}%"></i></div>`:''}<div class="meta">${esc(m.name)}: <b style="color:var(--text)">${g.current??'—'}</b> ${esc(m.unit||'')} → ${m.target??'—'}${pct!==null?` · ${pct}%`:''}</div>`:''}
    <div class="meta" style="margin-top:4px">Cột mốc ${g.milestones_done}/${(g.milestones||[]).length} · ${g.habit_ids.length} thói quen</div></button>`;
}
function grGoals(d){ return d.goals.map(goalCard).join('<div style="height:10px"></div>') + `<button class="btn full" style="margin-top:14px" onclick="openAddGoal()">${ico('plus')} Thêm mục tiêu</button>`; }
function grHabits(d){
  const wk = d.weeks.filter(w=>w.rate!==null);
  return `<div class="card">${d.habits.map(h=>habitRow(h,false)).join('')||'<div class="empty">Chưa có thói quen.</div>'}</div>
    <button class="btn full" style="margin-top:12px" onclick="openAddHabit()">${ico('plus')} Thêm thói quen</button>
    ${wk.length?`<div class="card chart" style="margin-top:12px"><h3>Tỷ lệ hoàn thành mỗi tuần</h3><p class="cap">Thói quen theo ngày · 8 tuần gần nhất · chạm cột để xem</p>${vbars(d.weeks.map(w=>({l:w.week, v:w.rate===null?0:Math.round(w.rate*100), tip:w.rate===null?`Tuần ${w.week}: chưa có thói quen`:`Tuần ${w.week}: ${Math.round(w.rate*100)}% (${w.done}/${w.due})`})),{aria:'Tỷ lệ hoàn thành thói quen mỗi tuần'})}<div class="tipline"></div></div>`:''}`;
}
function grMind(d){
  const by = {}; (d.memory||[]).forEach(f=>(by[f.kind]=by[f.kind]||[]).push(f));
  return `<p class="muted small" style="margin:0 4px 12px">Những điều superHuy ghi nhớ để cá nhân hoá lịch trình, gợi ý và câu trả lời. superHuy tự học thêm khi trò chuyện; anh có thể thêm hoặc xoá bất cứ lúc nào.</p>
    <div class="nl"><input id="mmIn" placeholder="Ví dụ: Anh thích tập buổi sáng sớm"><button class="btn pri" onclick="grRemember()">Nhớ</button></div>
    ${Object.entries(d.memory_kinds).filter(([k])=>by[k]).map(([k,l])=>`<div class="grp"><span>${esc(l)}</span><span>${by[k].length}</span></div><div class="card">${by[k].slice().reverse().map(f=>`<div class="fact"><div class="grow" style="font-size:14px">${esc(f.text)}<div class="meta">${esc(f.source)} · ${esc((f.at||'').slice(8,10)+'/'+(f.at||'').slice(5,7))}</div></div><button class="x" aria-label="Quên điều này" onclick="grForget('${f.id}')">${ico('x',16)}</button></div>`).join('')}</div>`).join('') || '<div class="card empty">superHuy chưa ghi nhớ điều gì.</div>'}`;
}
async function grCheck(id, done){
  const h = S.gr.data.habits.find(x=>x.id===id); if(h){ h.done_today = done; S.gr.data.today_done += done?1:-1; } haptic(done?'medium':'light'); render();
  try{ const r = await run('phattrien','checkin',{habit:id, done},'',true); if(done) toast(r.text); growthEnter(true); }catch(e){ toast(e.message); growthEnter(true); }
}
async function grPlan(tomorrow){
  const note = $('#grNote')?.value?.trim()||''; const day = tomorrow ? isoPlus(1) : new Date().toLocaleDateString('sv-SE');
  S.gr.planDay = day;
  sheet(`<h2>superHuy đang lập lịch trình</h2><p class="lead">Đọc lịch, việc tới hạn, thói quen và mục tiêu của anh…</p><div class="card pad"><div class="skel"></div><div class="skel" style="width:70%"></div><div class="skel" style="width:85%"></div></div>`);
  try{ const r = await run('phattrien','lichtrinh',{date:day, note},'superHuy đang lập lịch trình'); S.gr.plan = r; closeSheet(); S.gr.view='today'; render(); toast('Đã lập lịch trình'); }
  catch(e){ sheet(`<h2>Chưa lập được</h2><p class="lead">${esc(e.message)}</p>`); }
}
async function grApply(){
  const idx = [...document.querySelectorAll('.blk input[type=checkbox]')].filter(x=>x.checked).map(x=>x.dataset.i);
  if(!idx.length) return toast('Chọn ít nhất một khối');
  try{ const r = await run('phattrien','ap_lichtrinh',{date:S.gr.plan.date, indexes:idx.join(',')},'Đưa vào Google Calendar'); toast(r.text); S.cal = {}; growthEnter(true); }
  catch(e){ toast(e.message); }
}
function lineChart(logs, m){
  if(!logs.length) return '<div class="empty" style="padding:8px 0">Chưa có số liệu. Ghi số đầu tiên ở trên.</div>';
  const W = 320, H = 120, pl = 30, pb = 18, vals = logs.map(x=>x.value).concat(m.target!=null?[m.target]:[]), mn = Math.min(...vals), mx = Math.max(...vals), pad = (mx-mn)*0.15 || 1;
  const lo = mn-pad, hi = mx+pad, X = i => pl + (logs.length===1 ? (W-pl)/2 : i*(W-pl-6)/(logs.length-1)), Y = v => 6 + (H-pb-6) * (1-(v-lo)/(hi-lo));
  const path = logs.map((x,i)=>`${i?'L':'M'}${X(i).toFixed(1)},${Y(x.value).toFixed(1)}`).join(' ');
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" role="img" aria-label="${esc(m.name||'Chỉ số')} theo thời gian">
    ${m.target!=null?`<line x1="${pl}" x2="${W}" y1="${Y(m.target)}" y2="${Y(m.target)}" stroke="var(--muted)" stroke-dasharray="4 4" stroke-width="1"/><text x="${W-2}" y="${Y(m.target)-4}" text-anchor="end">mục tiêu ${m.target}</text>`:''}
    <text x="0" y="${Y(hi-pad)+4}">${(hi-pad).toFixed(1).replace('.0','')}</text><text x="0" y="${Y(lo+pad)+4}">${(lo+pad).toFixed(1).replace('.0','')}</text>
    <path d="${path}" fill="none" stroke="var(--jade)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
    ${logs.map((x,i)=>`<circle cx="${X(i)}" cy="${Y(x.value)}" r="4" fill="var(--jade)" stroke="var(--surface)" stroke-width="2" data-tip="${esc(x.date.slice(8,10)+'/'+x.date.slice(5,7))}: ${x.value} ${esc(m.unit||'')}${x.note?' · '+esc(x.note):''}"/>`).join('')}
    <text x="${pl}" y="${H-4}">${esc(logs[0].date.slice(8,10)+'/'+logs[0].date.slice(5,7))}</text>${logs.length>1?`<text x="${W-4}" y="${H-4}" text-anchor="end">${esc(logs[logs.length-1].date.slice(8,10)+'/'+logs[logs.length-1].date.slice(5,7))}</text>`:''}</svg>`;
}
function openGoal(id){
  const g = S.gr.data.goals.find(x=>x.id===id); if(!g) return; const m = g.metric||{}, sg = S.gr.data.suggestions?.[id];
  const acc = new Set(sg?.accepted||[]);
  sheet(`<div class="meta">${esc(S.gr.data.areas[g.area]||'')}${g.target_date?' · hạn '+esc(g.target_date.slice(8,10)+'/'+g.target_date.slice(5,7)+'/'+g.target_date.slice(0,4)):''}</div><h2 style="margin:2px 0 6px">${esc(g.title)}</h2>
    ${g.why?`<p class="lead">${esc(g.why)}</p>`:''}
    ${m.name?`<div class="card chart"><h3>${esc(m.name)}</h3><p class="cap">Hiện tại ${g.current??'—'} ${esc(m.unit||'')} · mục tiêu ${m.target??'—'} ${esc(m.unit||'')}</p>${lineChart(g.logs, m)}<div class="tipline"></div>
      <div class="nl" style="margin:8px 0 0"><input id="glVal" inputmode="decimal" placeholder="Ghi ${esc(m.name.toLowerCase())} hôm nay (${esc(m.unit||'')})"><button class="btn pri" onclick="grLog('${g.id}')">Ghi</button></div></div>`:''}
    <div class="sec" style="margin-top:18px"><h2>Cột mốc</h2></div>
    <div class="card">${(g.milestones||[]).map((x,i)=>`<div class="hrow"><button class="tick ${x.done?'on':''}" onclick="grMilestone('${g.id}',${i})" aria-label="Đánh dấu cột mốc">${ico('check',16)}</button><span class="grow" style="${x.done?'text-decoration:line-through;color:var(--muted)':''}">${esc(x.title)}</span></div>`).join('')||'<div class="empty">Chưa có cột mốc.</div>'}</div>
    <div class="sec"><h2>Thói quen của mục tiêu</h2></div>
    <div class="card">${S.gr.data.habits.filter(h=>h.goal_id===g.id).map(h=>habitRow(h,true)).join('')||'<div class="empty">Chưa có. Nhờ superHuy đề xuất bên dưới.</div>'}</div>
    <div class="card pad" style="margin-top:14px"><div class="row" style="flex-wrap:nowrap"><b class="grow" style="display:inline-flex;gap:6px;align-items:center">${ico('spark',16)} Huấn luyện viên superHuy</b><button class="addlink" id="coachBtn" onclick="grCoach('${g.id}')">${sg?'Đề xuất lại':'Đề xuất ngay'}</button></div>
      ${sg?`<p style="margin:8px 0 10px;font-size:14px">${esc(sg.summary||'')}</p>
        ${(sg.habits||[]).map((h,i)=>`<div class="hrow" style="padding:10px 0"><div class="grow"><div style="font-weight:500">${esc(h.title)}</div><div class="meta">${esc([h.target,h.time,h.why].filter(Boolean).join(' · '))}</div></div>${acc.has('habit:'+i)?'<span class="meta">✓ đã thêm</span>':`<button class="btn" onclick="grAccept('${g.id}','habit',${i})">${ico('plus')} Thêm</button>`}</div>`).join('')}
        ${(sg.milestones||[]).length?`<p class="lbl" style="margin-top:12px">Cột mốc đề xuất</p>${sg.milestones.map((x,i)=>`<div class="hrow" style="padding:8px 0"><span class="grow" style="font-size:14px">${esc(x)}</span>${acc.has('milestone:'+i)?'<span class="meta">✓</span>':`<button class="addlink" onclick="grAccept('${g.id}','milestone',${i})">Thêm</button>`}</div>`).join('')}`:''}
        ${(sg.week_plan||[]).length?`<details style="margin-top:10px"><summary>Tuần mẫu</summary><div class="ai-text" style="margin-top:8px">${esc(sg.week_plan.join('\n'))}</div></details>`:''}
        <p class="muted small" style="margin:10px 0 0">Gợi ý chung để tham khảo, không thay thế bác sĩ hay huấn luyện viên chuyên môn.</p>`
      :`<p class="muted small" style="margin:6px 0 0">superHuy đề xuất thói quen, cột mốc và một tuần mẫu cho mục tiêu này, dựa trên những gì đã biết về anh.</p>`}</div>`);
  tipBind($('#sheet'));
}
async function grLog(id){ const v = $('#glVal').value.trim(); if(!v) return; try{ const r = await run('phattrien','ghi_chiso',{goal:id, value:v}); toast(r.text); await growthEnter(true); openGoal(id); }catch(e){ toast(e.message); } }
async function grMilestone(id, i){ try{ await run('phattrien','cotmoc',{goal_id:id, index:i}); await growthEnter(true); openGoal(id); }catch(e){ toast(e.message); } }
async function grCoach(id){ const b = $('#coachBtn'); if(b){ b.innerHTML = '<span class="spin"></span> Đang soạn'; b.disabled = true; }
  try{ await run('phattrien','goiy',{goal:id},'Huấn luyện viên đang soạn'); await growthEnter(true); openGoal(id); }catch(e){ toast(e.message); if(b){ b.textContent='Đề xuất ngay'; b.disabled=false; } } }
async function grAccept(id, kind, i){ try{ const r = await run('phattrien','nhan_goiy',{goal_id:id, kind, index:i}); toast(r.text); await growthEnter(true); openGoal(id); }catch(e){ toast(e.message); } }
async function grRemember(){ const v = $('#mmIn').value.trim(); if(!v) return; try{ await run('phattrien','nho',{text:v}); toast('superHuy đã ghi nhớ'); growthEnter(true); }catch(e){ toast(e.message); } }
async function grForget(id){ try{ await run('phattrien','nho_xoa',{fact_id:id}); toast('Đã quên'); growthEnter(true); }catch(e){ toast(e.message); } }
const SCH = [['daily','Mỗi ngày'],['weekdays','T2-T6'],['weekly:3','3 lần/tuần'],['weekly:2','2 lần/tuần'],['weekly:1','1 lần/tuần']];
function schedKey(s){ if(!s) return 'daily'; if(s.type==='weekly') return 'weekly:'+(s.times||3); if(s.type==='days') return 'days:'+(s.days||[]).join(','); return s.type; }
function openHabit(id){ const h = S.gr.data.habits.find(x=>x.id===id); if(!h) return; S.eh = {habit_id:id, title:h.title, schedule:schedKey(h.schedule), time:h.time||'', target:h.target||''};
  sheet(`<div class="meta">${esc(h.sched)}${h.rate30!==null&&h.rate30!==undefined?` · 30 ngày: ${Math.round(h.rate30*100)}%`:''}${h.streak?` · 🔥 ${h.streak}`:''}</div><h2 style="margin:2px 0 14px">${esc(h.title)}</h2>
    ${h.why?`<p class="lead">${esc(h.why)}</p>`:''}<div class="dots28" style="max-width:none;margin-bottom:16px">${h.last28.map(x=>`<i class="${x?'on':''}"></i>`).join('')}</div>
    <label class="field"><span>Tên</span><input type="text" id="ehT" value="${esc(h.title)}"></label>
    <p class="lbl">Lặp lại</p><div class="inrow" id="ehS"></div>
    <div class="inrow"><label class="field" style="margin:0;flex:1"><span>Giờ</span><input type="text" id="ehTime" value="${esc(h.time||'')}" placeholder="06:00"></label><label class="field" style="margin:0;flex:2"><span>Mức cụ thể</span><input type="text" id="ehTg" value="${esc(h.target||'')}"></label></div>
    <div class="row" style="margin-top:6px"><button class="btn pri grow" onclick="grSaveHabit()">Lưu</button><button class="btn" style="color:var(--danger)" onclick="grArchive('${id}')">Ẩn thói quen</button></div>`);
  paintEh(); }
function paintEh(){ $('#ehS').innerHTML = SCH.map(([k,l])=>`<button class="chip ${S.eh.schedule===k?'on':''}" onclick="S.eh.schedule='${k}';paintEh()">${l}</button>`).join(''); }
async function grSaveHabit(){ const e = S.eh; e.title = $('#ehT').value.trim(); e.time = $('#ehTime').value.trim(); e.target = $('#ehTg').value.trim(); closeSheet();
  try{ await run('phattrien','sua_thoiquen',e); toast('Đã lưu'); growthEnter(true); }catch(x){ toast(x.message); } }
async function grArchive(id){ closeSheet(); try{ await run('phattrien','sua_thoiquen',{habit_id:id, archived:true}); toast('Đã ẩn thói quen'); growthEnter(true); }catch(x){ toast(x.message); } }
function openAddHabit(){ S.eh = {title:'', schedule:'daily', time:'', target:'', goal:''};
  sheet(`<h2>Thêm thói quen</h2><p class="lead">Nhỏ, đo được, gắn với mục tiêu. Bắt đầu dễ rồi tăng dần.</p>
    <label class="field"><span>Thói quen</span><input type="text" id="ehT" placeholder="Ví dụ: Giãn cơ 10 phút sau khi chạy"></label>
    <p class="lbl">Lặp lại</p><div class="inrow" id="ehS"></div>
    <div class="inrow"><label class="field" style="margin:0;flex:1"><span>Giờ</span><input type="text" id="ehTime" placeholder="06:00"></label><label class="field" style="margin:0;flex:2"><span>Mức cụ thể</span><input type="text" id="ehTg" placeholder="10 phút"></label></div>
    <label class="field"><span>Thuộc mục tiêu</span><select id="ehG"><option value="">Không</option>${S.gr.data.goals.map(g=>`<option value="${g.id}">${esc(g.title)}</option>`).join('')}</select></label>
    <button class="btn pri full" onclick="grAddHabit()">Thêm</button>`); paintEh(); }
async function grAddHabit(){ const e = S.eh; e.title = $('#ehT').value.trim(); if(!e.title) return toast('Ghi tên thói quen'); e.time = $('#ehTime').value.trim(); e.target = $('#ehTg').value.trim(); e.goal = $('#ehG').value; closeSheet();
  try{ const r = await run('phattrien','them_thoiquen',e); toast(r.text); growthEnter(true); }catch(x){ toast(x.message); } }
function openAddGoal(){ sheet(`<h2>Thêm mục tiêu</h2>
    <label class="field"><span>Mục tiêu</span><input type="text" id="agT" placeholder="Ví dụ: Đọc 24 cuốn sách năm 2027"></label>
    <label class="field"><span>Vì sao quan trọng</span><input type="text" id="agW"></label>
    <p class="lbl">Lĩnh vực</p><div class="inrow">${Object.entries(AREA).map(([k,l])=>`<button class="chip" data-a="${k}" onclick="document.querySelectorAll('[data-a]').forEach(b=>b.classList.toggle('on',b===this))">${l}</button>`).join('')}</div>
    <label class="field"><span>Hạn</span><input type="date" id="agD" style="padding:12px;border-radius:14px;border:0;box-shadow:0 0 0 1px var(--line);background:var(--surface);color:var(--text);font:inherit"></label>
    <details><summary>Chỉ số đo tiến độ</summary><div class="inrow" style="margin-top:10px"><input type="text" id="agM" placeholder="Tên (ví dụ Số sách)" style="flex:2;padding:10px;border-radius:12px;border:0;box-shadow:0 0 0 1px var(--line);background:var(--surface);color:var(--text);font:inherit"><input type="text" id="agU" placeholder="Đơn vị" style="flex:1;padding:10px;border-radius:12px;border:0;box-shadow:0 0 0 1px var(--line);background:var(--surface);color:var(--text);font:inherit"></div>
      <div class="inrow"><input type="text" id="agS" inputmode="decimal" placeholder="Bắt đầu" style="flex:1;padding:10px;border-radius:12px;border:0;box-shadow:0 0 0 1px var(--line);background:var(--surface);color:var(--text);font:inherit"><input type="text" id="agG" inputmode="decimal" placeholder="Đích" style="flex:1;padding:10px;border-radius:12px;border:0;box-shadow:0 0 0 1px var(--line);background:var(--surface);color:var(--text);font:inherit"></div></details>
    <button class="btn pri full" onclick="grAddGoal()">Thêm mục tiêu</button>`); }
async function grAddGoal(){ const t = $('#agT').value.trim(); if(!t) return toast('Ghi tên mục tiêu');
  const p = {title:t, why:$('#agW').value.trim(), area:(document.querySelector('[data-a].on')||{}).dataset?.a||'self', target_date:$('#agD').value, metric_name:$('#agM').value.trim(), unit:$('#agU').value.trim(), start:$('#agS').value.trim(), target:$('#agG').value.trim()};
  closeSheet(); try{ const r = await run('phattrien','them_muctieu',p); toast(r.text); growthEnter(true); }catch(x){ toast(x.message); } }

