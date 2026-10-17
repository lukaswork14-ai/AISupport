/* ---------- Hôm nay */
function urgentItems(){
  const out = [];
  for(const [k, d] of Object.entries(S.data.digests||{})){
    const lines = (d.text||'').split('\n'); let on = false;
    for(const raw of lines){
      const l = raw.trim();
      if(/^(\d\)\s*)?🔥/.test(l)){ on = true; continue; }
      if(on){
        if(!l) { if(out.filter(o=>o.k===k).length) break; else continue; }
        if(/^(\d\)\s*)?(📌|🏢|🗂|💬|🗑)/.test(l)) break;
        const t = l.replace(/^[•\-\d.)\s]+/, '');
        if(t && !/^không có/i.test(t) && !/(\S+)(\s+\1){4,}/.test(t)) out.push({k, t:t.slice(0,180), at:d.at});
      }
    }
  }
  return out.slice(0, 6);
}
function vHome(){
  const d = S.data, now = new Date(), h = now.getHours();
  const hi = h<11 ? 'Chào buổi sáng' : h<14 ? 'Chào buổi trưa' : h<18 ? 'Chào buổi chiều' : 'Chào buổi tối';
  const cqNew = (d.cq?.new||[]).slice(0,6), todo = urgentItems();
  const lastScan = Object.values(d.digests||{}).map(x=>x.at).sort().pop();
  const t = S.tk.data?.stats, g = S.gr?.data;
  const sum = [t?`<b>${t.today}</b> việc hôm nay`:'', g?`<b>${g.today_done}/${g.today_due}</b> thói quen`:'', todo.length?`<b>${todo.length}</b> mục cần anh`:''].filter(Boolean).join(' · ');
  const QA = [['Ghi âm họp','mic','#E5484D',"go('meet');setTimeout(recStart,200)"],['Lịch trình hôm nay','calendar','#7B5CF0',"homeAsk('Lên lịch trình hôm nay giúp anh, tối ưu cho các mục tiêu')"],
    ['Tạo việc','tasks','#2a78d6',"go('tasks');setTimeout(()=>window.openAddTask&&openAddTask(),250)"],['Ghi chi tiêu','wallet','#d95926',"go('money');setTimeout(()=>window.openAddMoney&&openAddMoney(),250)"],
    ['Check-in thói quen','sprout','#199e70',"go('growth')"],['Săn tin & reels','film','#C13F96',"go('news')"]];
  return `
  <div class="htop"><span class="orb"><img class="brandimg" src="/icons/huy-128.png?v=3" alt=""></span><div class="who"><b>superHuy</b><div>${esc(viDate(now))}</div></div>
    <button class="iconbtn" aria-label="Tình trạng hệ thống" onclick="openQC()">${ico('check',19)}</button>
    <button class="iconbtn" aria-label="Tất cả tiện ích và cài đặt" onclick="go('more')">${ico('more',19)}</button></div>
  <div class="hgrid"><section class="hb b-hero">
  <div class="hero"><h1>${hi}${S.first?', '+esc(S.first):''}</h1><p>${sum || 'superHuy đang chuẩn bị ngày của anh…'}</p></div>
  <form class="hask" onsubmit="event.preventDefault();homeAsk($('#hq').value)"><input id="hq" placeholder="Hỏi hoặc nhờ superHuy bất cứ điều gì…" autocomplete="off" enterkeyhint="send">
    <button type="button" class="mic" aria-label="Ghi âm cuộc họp" onclick="go('meet');setTimeout(recStart,200)">${ico('mic',20)}</button><button class="go" aria-label="Gửi">${ico('arrow',20)}</button></form>
  <div class="qa">${QA.map(([l,i,c,f])=>`<button onclick="${f}"><i style="--c:${c}">${ico(i,16)}</i>${l}</button>`).join('')}</div>
  </section>

  <div class="hcol hcol-l"><section class="hb b-cal">

  <div class="sec"><h2>Lịch <button class="addlink" onclick="openAddEvent()" style="margin-left:8px">${ico('plus',16)}Thêm</button></h2><div class="seg" role="tablist"><button class="${S.calDay==='today'?'on':''}" onclick="setDay('today')">Hôm nay</button><button class="${S.calDay==='tomorrow'?'on':''}" onclick="setDay('tomorrow')">Ngày mai</button></div></div>
  <div class="card" id="cal"><div class="tl"><div class="skel" style="width:70%"></div><div class="skel" style="width:50%"></div></div></div>
  <div id="invWrap">${invSection()}</div></section><section class="hb b-todo">

  <div class="sec"><h2>Cần anh xử lý</h2><button class="link" id="dgBtn" style="color:var(--jade);font-weight:600;font-size:14px;display:inline-flex;gap:5px;align-items:center" onclick="liveDigests(true)">${S.dgBusy?'<span class="spin" style="width:14px;height:14px"></span> Đang cập nhật':`${ico('refresh',15)} ${lastScan?'Cập nhật '+esc(fmtTime(lastScan)):'Cập nhật'}`}</button></div>
  <div class="card ${todo.length?'urgent':''}">${todo.length ? todo.map(x=>{ const m = x.t.match(/^\[(CEO|Tăng trưởng|AI)\]\s*/); return `<div class="todo"><span class="src ${x.k}">${x.k==='lark'?'Lark':'Email'}</span><div class="grow">${m?`<span class="tag role" style="margin-right:6px">${esc(m[1])}</span>`:''}${esc(m?x.t.slice(m[0].length):x.t)}</div></div>`; }).join('')
     : `<div class="empty">Chưa có việc gấp. superHuy quét email và Lark theo lịch; việc cần anh xử lý sẽ hiện ở đây.</div>`}</div>

  </section>${cqNew.length ? `<section class="hb b-news">` : ''}${cqNew.length ? `<div class="sec"><h2>Chờ duyệt nội dung</h2><button class="link" onclick="go('news')">Duyệt nhanh</button></div>
  <div class="rail">${cqNew.map(n=>`
    <article class="card pad news"><div class="row" style="gap:6px"><span class="trk ${n.track}">${esc(TRK[n.track]||n.track)}</span><span class="topic">${esc(n.topic)}</span></div><h3>${esc(n.headline_vi)}</h3>
      <p class="why">${esc(n.why_hot||'')}</p>
      <div class="row" style="margin-top:auto"><button class="btn pri" onclick="cApprove('${n.id}')">${ico('film')} Tạo reels</button><button class="btn" onclick="cSkip('${n.id}')">Bỏ qua</button></div>
    </article>`).join('')}</div></section>` : ''}</div><div class="hcol hcol-r"><section class="hb b-today"><div class="sec"><h2>Hôm nay</h2></div>
  <div class="hstat" id="hstat">${homeStats()}</div></section><section class="hb b-apps"><div class="sec"><h2>Tiện ích</h2></div>
  <div class="apps">${appsGrid()}</div></section><section class="hb b-recent"><div class="sec"><h2>Gần đây</h2><button class="link" onclick="go('studio')">Thư viện</button></div>
  <div class="masonry" id="recent">${recentCards()}</div></section></div></div>`;
}
const APPS = [
  ['calendar','Lịch','#7B5CF0',"if(S.tab!=='home')go('home');setTimeout(()=>document.getElementById('cal')?.scrollIntoView({behavior:'smooth',block:'center'}),250)"],
  ['tasks','Việc','#2a78d6',"go('tasks')", ()=>S.tk.data?.stats?.today],
  ['mic','Họp','#E5484D',"go('meet')", ()=>(S.mt.items||[]).filter(m=>m.status==='working'||m.status==='queued').length],
  ['inbox','Hộp thư','#0E8FB8',"go('mail')"],
  ['lark','Lark','#1F7AE0',"openAgent('lark')"],
  ['film','Nội dung','#C13F96',"go('news')", ()=>S.data.cq?.new?.length],
  ['sprout','Phát triển','#199e70',"go('growth')", ()=>{ const g=S.gr?.data; return g ? g.today_due-g.today_done : 0; }],
  ['wallet','Tài chính','#d95926',"go('money')"],
  ['brain','Second Brain','#8B5CF6',"openBrain()"],
  ['send','Đăng bài','#c98500',"openAgent('dang')"],
  ['chat','Trò chuyện','#A2338C',"go('chat')"],
  ['bag','Marketplace','#5B3FD9',"go('mkt')"],
  ['layers','Workflow','#2457C5',"go('wf')"],
  ['users','Hồ sơ','#0E7C6B',"go('me')"],
  ['factory','superYou HQ','#7A5A00',"openLink(location.origin+'/hq')"],
  ['gear','Cài đặt','#7A7387',"go('more')"],
];
function appsGrid(){ return APPS.map(([i,l,c,f,b])=>{ const n = b ? b() : 0; return `<button onclick="${f}" aria-label="${l}"><i style="--c:${c}">${ico(i,24)}</i>${l}${n?`<span class="bd">${n>99?'99+':n}</span>`:''}</button>`; }).join(''); }
function recentCards(){
  const items = [];
  (S.mt.items||[]).filter(m=>m.status==='done').slice(0,3).forEach(m=>items.push({at:m.started||'', html:`<button class="rc" onclick="meetOpen('${m.id}')"><div class="k"><i style="--c:#E5484D">${ico('mic',13)}</i>Họp · ${(m.started||'').slice(11,16)} ${(m.started||'').slice(8,10)}/${(m.started||'').slice(5,7)}</div><h4>${esc(m.title||'Cuộc họp')}</h4><p class="clamp2">${esc(m.summary||'')}</p></button>`}));
  (S.data.contents||[]).slice(0,4).forEach(c=>items.push({at:c.created||'', html:`<button class="rc" onclick="openContent('${c.id}')"><div class="k"><i style="--c:#C13F96">${ico((KIND[c.kind]||['','pen'])[1],13)}</i>${esc((KIND[c.kind]||[c.kind])[0])} · ${esc((c.created||'').slice(11,16))}</div><h4 class="clamp2">${esc(c.title)}</h4>${c.image?`<img src="${c.image}" alt="" loading="lazy">`:''}</button>`}));
  const chat = (S.data.chat||[]).filter(x=>x.role==='user').slice(-1)[0];
  if(chat) items.push({at:'9', html:`<button class="rc" onclick="S.dockOpen=true;dock()"><div class="k"><i style="--c:#7B5CF0">${ico('spark',13)}</i>Hỏi superHuy</div><h4>${esc(chat.content.slice(0,90))}</h4><p>Bấm để mở lại cuộc trò chuyện</p></button>`});
  items.sort((a,b)=>b.at.localeCompare(a.at));
  return items.length ? items.map(x=>x.html).join('') : `<div class="card empty">Cuộc họp, bài viết, video và câu hỏi gần đây sẽ hiện ở đây.</div>`;
}
function homeAsk(v){
  v = (v||'').trim(); if(!v) return;
  const i = $('#hq'); if(i) i.value = '';
  S.dockOpen = true; dock(); $('#dIn') && ($('#dIn').value = v); dockAsk();
}
function crew(){
  const st = Object.fromEntries((S.data.connections||[]).map(c=>[c.id, c.ok]));
  const need = { lich:'calendar', email:'gmail', lark:'lark', dang:'facebook', brain:'obsidian' };
  return (S.data.agents||[]).filter(a=>!['caidat','tin','studio'].includes(a.id)).map(a=>{
    const off = need[a.id] && st[need[a.id]] === false;
    const page = {email:'mail', tin:'news', studio:'studio', noidung:'content', hop:'meet', viec:'tasks', taichinh:'money', phattrien:'growth'}[a.id];
    return `<button class="mate ${off?'off':'ok'}" data-id="${a.id}" onclick="${page?`go('${page}')`:`openAgent('${a.id}')`}" aria-label="${esc(a.name)}">
      <span class="ring"><svg class="r" viewBox="0 0 58 58"><circle class="track" cx="29" cy="29" r="26.5" fill="none" stroke-width="3"/><circle class="arc" cx="29" cy="29" r="26.5" fill="none" stroke-width="3" stroke-linecap="round"/></svg>
      <span class="core">${ico(AGENT_ICON[a.id]||'spark', 22)}</span></span><span class="nm">${esc(a.name.replace('Tin nhắn ',''))}</span></button>`;
  }).join('');
}
function setDay(d){ S.calDay = d; document.querySelectorAll('.seg button').forEach((b,i)=>b.classList.toggle('on', (i===0)===(d==='today'))); loadCal(true); }
async function loadCal(force){
  const el = $('#cal'); if(!el) return;
  const day = new Date(); if(S.calDay==='tomorrow') day.setDate(day.getDate()+1);
  const iso = day.toLocaleDateString('sv-SE');
  if(S.cal[iso] && force) paintCal(iso);  // hiện ngay bản đang có, rồi lấy bản mới nhất
  if(!S.cal[iso] || force){
    try{ S.cal[iso] = await run('lich','ngay',{date:iso},'',true); }catch(e){ if(!S.cal[iso]) el.innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
  }
  paintCal(iso);
}
function paintCal(iso){
  const el = $('#cal'); if(!el) return;
  const cur = new Date(); if(S.calDay==='tomorrow') cur.setDate(cur.getDate()+1);
  if(cur.toLocaleDateString('sv-SE') !== iso || !S.cal[iso]) return;  // người dùng đã đổi ngày
  const r = S.cal[iso], now = new Date(), isToday = S.calDay==='today';
  S.canWrite = !!r.can_write;
  const evs = (r.items||[]).map(v=>{ let past=false; if(isToday && v.end){ const d=new Date(now); const [h,m]=v.end.split(':'); d.setHours(+h,+m,0); past = d < now; } return {...v, past}; });
  S.evs = Object.fromEntries(evs.filter(v=>v.id).map(v=>[v.id, v]));
  $('#cal').innerHTML = evs.length ? `<div class="tl">${evs.map(v=>`<div class="ev ${v.past?'past':''}"><div class="t">${v.all_day?'Cả ngày':esc(v.start)}${v.end?`<small>${esc(v.end)}</small>`:''}</div><span class="dot ${v.priority||'normal'}"></span>
      <button class="ttl" onclick="openEvent('${esc(v.id||'')}')">${esc(v.title)}${v.location?`<div class="meta">${esc(v.location)}</div>`:''}</button></div>`).join('')}</div>`
    : `<div class="empty">${isToday?'Hôm nay':'Ngày mai'} chưa có lịch. <button class="addlink" onclick="openAddEvent()">Thêm lịch</button></div>`;
}

const PRI = [['red','Gấp và quan trọng','Làm ngay'],['orange','Quan trọng','Lên lịch làm'],['blue','Gấp','Giao hoặc làm nhanh'],['normal','Bình thường','Khi rảnh']];
const PRI_COLOR = {red:'var(--p-red)', orange:'var(--p-orange)', blue:'var(--p-blue)', normal:'var(--muted)'};
const matrix = (cur, fn) => `<div class="matrix">${PRI.map(([k,t,d])=>`<button type="button" class="mx ${cur===k?'on':''}" data-p="${k}" onclick="${fn}('${k}')"><i style="background:${PRI_COLOR[k]}"></i><span><b>${t}</b><small>${d}</small></span></button>`).join('')}</div>`;

function openAddEvent(){
  const d0 = new Date(); if(S.calDay==='tomorrow') d0.setDate(d0.getDate()+1);
  S.ev = { title:'', date:d0.toLocaleDateString('sv-SE'), start:'09:00', duration_min:60, all_day:false, priority:'normal', location:'' };
  const conn = S.canWrite===false ? `<div class="note">Để tạo lịch, cần bật cầu nối Google Calendar một lần. <button class="addlink" onclick="openAction('caidat','caunoilich')">Bật ngay</button></div>` : '';
  sheet(`<h2>Thêm lịch</h2><p class="lead">Gõ tự nhiên rồi để AI điền, hoặc điền tay.</p>${conn}
    <div class="nl"><input id="nlIn" placeholder="Họp CJ 3h chiều mai 1 tiếng" enterkeyhint="go"><button class="btn pri" id="nlBtn">${ico('spark',17)} Điền</button></div>
    <label class="field"><span>Tiêu đề</span><input type="text" id="evTitle" placeholder="Tên sự kiện"></label>
    <p class="lbl">Ngày</p><div class="inrow" id="evDay"></div>
    <p class="lbl">Thời gian</p><div class="inrow" id="evTime"></div>
    <p class="lbl">Mức ưu tiên</p><div id="evPri"></div>
    <details><summary>Thêm địa điểm</summary><label class="field"><span>Địa điểm</span><input type="text" id="evLoc"></label></details>
    <button class="btn pri full" id="evSave">Thêm vào lịch</button>`);
  paintEv();
  $('#nlIn').onkeydown = e => { if(e.key==='Enter'){ e.preventDefault(); $('#nlBtn').click(); } };
  $('#nlBtn').onclick = async () => {
    const t = $('#nlIn').value.trim(); if(!t) return;
    const b = $('#nlBtn'); b.disabled = true; b.innerHTML = '<span class="spin"></span>';
    try{ const r = await run('lich','hieu',{text:t},'AI đang đọc lịch'); Object.assign(S.ev, r.fields||{}); if(!S.ev.start) S.ev.all_day = true; paintEv(); }
    catch(e){ toast(e.message); }
    b.disabled = false; b.innerHTML = `${ico('spark',17)} Điền`;
  };
  $('#evSave').onclick = async () => {
    S.ev.title = $('#evTitle').value.trim(); S.ev.location = $('#evLoc').value.trim();
    if(!S.ev.title) return toast('Thêm tiêu đề cho sự kiện');
    const b = $('#evSave'); b.disabled = true; b.innerHTML = '<span class="spin"></span> Đang thêm';
    try{ const r = await run('lich','tao',{...S.ev},'Thêm lịch'); closeSheet(); toast(r.text); S.cal = {}; loadCal(true); }
    catch(e){ toast(e.message); b.disabled = false; b.textContent = 'Thêm vào lịch'; }
  };
}
function paintEv(){
  const e = S.ev, today = new Date().toLocaleDateString('sv-SE'), tm = new Date(Date.now()+864e5).toLocaleDateString('sv-SE');
  $('#evTitle').value = e.title || $('#evTitle').value; if(e.location) $('#evLoc').value = e.location;
  $('#evDay').innerHTML = `<button class="chip ${e.date===today?'on':''}" onclick="S.ev.date='${today}';paintEv()">Hôm nay</button><button class="chip ${e.date===tm?'on':''}" onclick="S.ev.date='${tm}';paintEv()">Ngày mai</button><input type="date" value="${e.date}" onchange="S.ev.date=this.value;paintEv()">`;
  const durs = [[30,'30 phút'],[60,'1 giờ'],[120,'2 giờ']];
  $('#evTime').innerHTML = (e.all_day ? '' : `<input type="time" value="${e.start||'09:00'}" onchange="S.ev.start=this.value">`) +
    durs.map(([m,l])=>`<button class="chip ${!e.all_day&&+e.duration_min===m?'on':''}" onclick="S.ev.all_day=false;S.ev.duration_min=${m};if(!S.ev.start)S.ev.start='09:00';paintEv()">${l}</button>`).join('') +
    `<button class="chip ${e.all_day?'on':''}" onclick="S.ev.all_day=!S.ev.all_day;paintEv()">Cả ngày</button>`;
  $('#evPri').innerHTML = matrix(e.priority, 'setEvPri');
}
function setEvPri(k){ S.ev.priority = k; haptic(); $('#evPri').innerHTML = matrix(k, 'setEvPri'); }
function openEvent(id){
  const v = S.evs?.[id]; if(!v) return;
  S.evOpen = v;
  sheet(`<div class="meta">${esc(v.source)}</div><h2 style="margin-bottom:6px">${esc(v.title)}</h2>
    <p class="lead">${v.all_day?'Cả ngày':esc(v.start+' – '+v.end)}${v.location?' · '+esc(v.location):''}</p>
    ${v.editable ? `<p class="lbl">Mức ưu tiên</p><div id="opPri">${matrix(v.priority,'setOpenPri')}</div>
      <button class="btn full" id="evDel" style="color:var(--danger)">${ico('x',17)} Xóa sự kiện</button>`
      : `<div class="note">Sự kiện này thuộc lịch khác hoặc lịch Lark nên chỉ xem được.</div>`}`);
  const del = $('#evDel'); if(del) del.onclick = async () => {
    if(del.dataset.ok!=='1'){ del.dataset.ok='1'; del.textContent='Bấm lần nữa để xóa'; return; }
    try{ await run('lich','xoa',{event_id:v.id},'Xóa sự kiện'); closeSheet(); toast('Đã xóa sự kiện'); S.cal={}; loadCal(true); }catch(e){ toast(e.message); }
  };
}
async function setOpenPri(k){
  const v = S.evOpen; $('#opPri').innerHTML = matrix(k,'setOpenPri');
  try{ await run('lich','uutien',{event_id:v.id, priority:k},'Đổi ưu tiên'); v.priority = k; toast('Đã đổi mức ưu tiên'); S.cal={}; loadCal(true); }catch(e){ toast(e.message); }
}

/* ---------- Tin */
const src = s => String(s||'').replace('GNews: ','');
function vNews(){
  const news = S.data.news||[];
  return `
  <div class="date">${news.length?`${news.length} tin chọn từ nguồn uy tín`:'Chưa quét tin hôm nay'}</div>
  <h1>Tin hot hôm nay</h1>
  <div class="row" style="margin-bottom:16px">
    <button class="btn pri" onclick="act.scan()">${ico('refresh')} Quét lại</button>
    <button class="btn" onclick="act.bantin()">${ico('image')} Ảnh bản tin</button>
    <button class="btn" onclick="act.video()">${ico('film')} Video</button>
  </div>
  ${news.length ? news.map((n,i)=>`
  <article class="card pad news" style="width:auto;margin-bottom:12px">
    <div class="row"><span class="topic">${esc(n.topic)}</span><span class="muted small">${esc(src(n.source))}</span></div>
    <h3>${esc(n.headline_vi)}</h3>
    <p class="sum">${esc(n.summary_vi)}</p>
    ${n.why_hot?`<p class="why">${esc(n.why_hot)}</p>`:''}
    <div class="row">
      <button class="btn pri" onclick="act.write(${i+1})">${ico('pen')} Viết bài</button>
      <button class="btn" onclick="act.saveNews(${i+1})">${ico('save')} Lưu</button>
      <button class="btn" onclick="openLink('${esc(n.url)}')">${ico('link')} Bài gốc</button>
    </div>
  </article>`).join('') : `<div class="card empty">Bấm “Quét lại” để agent tìm 5 tin hot về AI và thương mại điện tử.</div>`}`;
}

/* ---------- Hộp thư */
const LBL = {Work:'Công việc', Learning:'Kiến thức', Personal:'Cá nhân', Important:'Quan trọng', Finance:'Tài chính', Promotion:'Quảng cáo'};
S.mail = { items:[], loaded:false, view:'swipe', filter:'', syncing:false, platforms:{gmail:true, lark:false} };
const initials = n => (String(n||'?').replace(/[<"].*$/,'').split(/[\s·\-|,.]+/).filter(w=>/^\p{L}/u.test(w)).map(w=>w[0]).slice(-2).join('') || '?').toUpperCase();
async function liveDigests(force){
  if(S.dgBusy) return;
  const last = Math.max(...Object.values(S.data.digests||{}).map(x=>Date.parse(x.at)||0), 0);
  if(!force && S.dgAt && Date.now() - S.dgAt < 3*60*1000) return;  // vừa cập nhật trong 3 phút
  S.dgBusy = true; S.dgAt = Date.now(); paintDg();
  const kinds = [['email','capnhat'], ...((S.data.connections||[]).some(c=>c.id==='lark'&&c.ok) ? [['lark','capnhat']] : [])];
  await Promise.all(kinds.map(([a,b]) => run(a, b, {}, '', true).then(r=>{ if(r?.digests) S.data.digests = r.digests; }).catch(()=>{})));
  S.dgBusy = false;
  if(S.tab==='home' && !document.querySelector('#sheet.on')) render(); else paintDg();
}
function paintDg(){ const b = $('#dgBtn'); if(!b) return; const at = Object.values(S.data.digests||{}).map(x=>x.at).sort().pop();
  b.innerHTML = S.dgBusy ? '<span class="spin" style="width:14px;height:14px"></span> Đang cập nhật' : `${ico('refresh',15)} ${at?'Cập nhật '+esc(fmtTime(at)):'Cập nhật'}`; }
async function mailEnter(){
  if(S.mail.syncing) return;
  if(S.mail.loaded && S.mail.at && Date.now() - S.mail.at < 30000) return;  // vừa đồng bộ
  S.mail.at = Date.now();
  if(S.mail.loaded){ S.mail.syncing = true; try{ const r = await run('email','hopthu',{refresh:true},'',true); mergeMail(r); }catch(e){} S.mail.syncing = false; if(S.tab==='mail' && !document.querySelector('#sheet.on')) render(); return; }
  S.mail.syncing = true;
  try{ Object.assign(S.mail, await run('email','hopthu',{refresh:false},'Mở hộp thư')); S.mail.loaded = true; if(S.tab==='mail') render(); }catch(e){}
  try{ const r = await run('email','hopthu',{refresh:true},'Đồng bộ và phân loại thư'); mergeMail(r); if(r.text) toast(r.text); }
  catch(e){ toast(e.message); }
  S.mail.syncing = false; if(S.tab==='mail') render();
}
function mergeMail(r){ const local = Object.fromEntries(S.mail.items.filter(m=>m.status!=='new').map(m=>[m.uid,m]));
  r.items.forEach(m=>{ if(local[m.uid]){ m.status=local[m.uid].status; m.label=local[m.uid].label; } }); Object.assign(S.mail, r); S.mail.loaded = true; }
const MPRI = {high:['Ưu tiên cao','hi',0], medium:['Trung bình','mid',1], low:['Thấp','lo',2]};
const ROLE = {CEO:'CEO', Growth:'Tăng trưởng', AI:'AI', Personal:'Cá nhân'};
const queue = () => S.mail.items.filter(m => m.status==='new').map((m,i)=>[m,i]).sort((a,b)=>((MPRI[a[0].priority]||MPRI.medium)[2]-(MPRI[b[0].priority]||MPRI.medium)[2]) || a[1]-b[1]).map(x=>x[0]);
const tagsHtml = m => { const p = MPRI[m.priority]||MPRI.medium; return `<div class="tags"><span class="tag ${p[1]}">${p[0]}</span>${m.role&&ROLE[m.role]?`<span class="tag role">${ROLE[m.role]}</span>`:''}</div>`; };
const sugHtml = m => m.action ? `<div class="aisug">${ico('spark',15)}<span>${esc(m.action)}</span></div>` : '';
function vMail(){
  const q = queue(), all = S.mail.items, v = S.mail.view;
  const head = `<div class="date">${S.mail.syncing?'Đang đồng bộ và gắn nhãn…':`${q.length} thư chờ duyệt`}</div><div class="row" style="align-items:center;margin-bottom:14px"><h1 class="grow" style="margin:2px 0 0">Hộp thư</h1><button class="btn pri" onclick="openCompose()">${ico('pen')} Soạn thư</button></div>
    <div class="seg" style="margin-bottom:14px"><button class="${v==='swipe'?'on':''}" onclick="S.mail.view='swipe';render()">Duyệt nhanh</button><button class="${v==='labels'?'on':''}" onclick="S.mail.view='labels';render()">Theo nhãn</button></div>`;
  if(!S.mail.loaded || (S.mail.syncing && !all.length)) return head + `<p class="muted small" style="margin:0 0 10px">Lần đầu cần khoảng 1 phút để AI đọc và gắn nhãn thư.</p>` + `<div class="card pad"><div class="skel" style="width:60%"></div><div class="skel"></div><div class="skel" style="width:80%"></div></div>`;
  if(v==='swipe'){
    if(!q.length) return head + `<div class="done"><b>Đã duyệt hết thư</b>Thư mới sẽ tự được phân loại. Xem lại mọi thư trong “Theo nhãn”.</div>`;
    const top = q.slice(0,3).reverse();
    return head + `<div class="stack" id="stack">${top.map((m,i)=>{ const depth = top.length-1-i;
      return `<article class="card mcard ${depth===1?'back1':depth===2?'back2':''}" data-uid="${m.uid}">
        ${depth===0?'<span class="stamp yes">Trả lời</span><span class="stamp no">Bỏ qua</span>':''}
        <div class="who"><span class="av">${esc(initials(m.from_name||m.from))}</span><div class="grow"><div style="font-weight:600">${esc(m.from_name||m.from)}</div><div class="meta">${esc(m.time)}</div></div><span class="lb ${m.label}">${esc(LBL[m.label]||m.label)}</span></div>
        ${tagsHtml(m)}
        <h3>${esc(m.subject)}</h3>
        <p class="sum">${esc(m.summary)}</p>
        ${sugHtml(m)}
        ${m.needs_reply?'<span class="badge draft" style="align-self:flex-start">Đang chờ bạn trả lời</span>':''}
        <div class="body">${esc(m.body)}</div></article>`; }).join('')}</div>
      <div class="swipebar"><button class="round" aria-label="Bỏ qua" onclick="swipeTop(-1)">${ico('x')}</button><button class="round yes" aria-label="Trả lời" onclick="swipeTop(1)">${ico('reply')}</button></div>
      <p class="muted small" style="text-align:center;margin-top:12px">Quẹt phải để trả lời, quẹt trái để bỏ qua</p>`;
  }
  const counts = {}; all.forEach(m=>counts[m.label]=(counts[m.label]||0)+1);
  const f = S.mail.filter, list = all.filter(m=>!f || m.label===f);
  return head + `<div class="chips" style="padding-top:0;margin-bottom:12px"><button class="chip ${!f?'on':''}" onclick="S.mail.filter='';render()">Tất cả ${all.length}</button>${Object.keys(LBL).filter(k=>counts[k]).map(k=>`<button class="chip ${f===k?'on':''}" onclick="S.mail.filter='${k}';render()">${LBL[k]} ${counts[k]}</button>`).join('')}</div>
    ${list.length?`<div class="card list">${list.map(m=>`<button onclick="openMail('${m.uid}')"><span class="av">${esc(initials(m.from_name||m.from))}</span><div class="grow"><div class="row" style="gap:6px"><b style="font-weight:600">${esc(m.from_name||m.from)}</b><span class="meta" style="margin:0">${esc(m.time)}</span></div><div class="ttl2" style="font-weight:500">${esc(m.subject)}</div><div class="meta">${esc(m.summary)}</div>${m.priority==='high'?'<span class="tag hi" style="display:inline-block;margin-top:6px">Ưu tiên cao</span>':''}</div><span class="lb ${m.label}">${esc(LBL[m.label]||'')}</span></button>`).join('')}</div>`:`<div class="card empty">Chưa có thư nào ở nhãn này.</div>`}`;
}
function bindSwipe(){
  const card = document.querySelector('.mcard:not(.back1):not(.back2)'); if(!card) return;
  let x0=null, dx=0;
  const yes = card.querySelector('.stamp.yes'), no = card.querySelector('.stamp.no');
  card.onpointerdown = e => { x0 = e.clientX; dx = 0; card.setPointerCapture(e.pointerId); card.style.transition='none'; };
  card.onpointermove = e => { if(x0===null) return; dx = e.clientX - x0; card.style.transform = `translateX(${dx}px) rotate(${dx/18}deg)`; yes.style.opacity = Math.max(0, dx/110); no.style.opacity = Math.max(0, -dx/110); };
  card.onpointerup = card.onpointercancel = () => { if(x0===null) return; x0=null; card.style.transition='transform .25s ease';
    if(Math.abs(dx) > 110) swipeTop(dx>0?1:-1); else { card.style.transform=''; yes.style.opacity=0; no.style.opacity=0; } };
}
function swipeTop(dir){
  const card = document.querySelector('.mcard:not(.back1):not(.back2)'); if(!card) return;
  const uid = card.dataset.uid, m = S.mail.items.find(x=>x.uid===uid);
  haptic(dir>0?'medium':'light');
  card.style.transition='transform .28s ease, opacity .28s'; card.style.transform=`translateX(${dir*480}px) rotate(${dir*18}deg)`; card.style.opacity=0;
  setTimeout(()=>{
    if(dir<0){ m.status='skipped'; run('email','boqua',{uid},'Đánh dấu đã đọc').catch(()=>{}); render(); }
    else { openReply(uid); render(); }
  }, 220);
}
function openMail(uid){
  const m = S.mail.items.find(x=>x.uid===uid); if(!m) return;
  sheet(`<div class="who row" style="margin-bottom:10px"><span class="av">${esc(initials(m.from_name||m.from))}</span><div class="grow"><div style="font-weight:600">${esc(m.from_name)}</div><div class="meta">${esc(m.from)} · ${esc(m.time)}</div></div></div>
    ${tagsHtml(m)}<h2 style="margin-top:10px">${esc(m.subject)}</h2><p class="lead">${esc(m.summary)}</p>${m.action?`<div style="margin:-4px 0 14px">${sugHtml(m)}</div>`:''}
    <p class="lbl">Nhãn</p><div class="chips" style="padding-top:0;flex-wrap:wrap;margin-bottom:12px">${Object.entries(LBL).map(([k,l])=>`<button class="chip ${m.label===k?'on':''}" onclick="relabel('${uid}','${k}')">${l}</button>`).join('')}</div>
    <div class="card out" style="max-height:38vh;overflow:auto">${esc(m.body)}</div>
    <div class="row" style="margin-top:14px"><button class="btn pri grow" onclick="openReply('${uid}')">${ico('reply')} Trả lời</button><button class="btn" onclick="skipMail('${uid}')">Bỏ qua</button></div>`);
}
async function relabel(uid, k){
  const m = S.mail.items.find(x=>x.uid===uid); m.label = k; openMail(uid);
  try{ await run('email','nhan',{uid, label:k},'Đổi nhãn'); toast('Đã gắn nhãn '+LBL[k]+' trong Gmail'); }catch(e){ toast(e.message); }
}
function skipMail(uid){ const m=S.mail.items.find(x=>x.uid===uid); m.status='skipped'; run('email','boqua',{uid},'Đánh dấu đã đọc').catch(()=>{}); closeSheet(); render(); toast('Đã bỏ qua'); }
function openReply(uid){
  const m = S.mail.items.find(x=>x.uid===uid); if(!m) return;
  const hints = [...(m.action?[['Theo gợi ý AI', m.action]]:[]), ...['Đồng ý','Từ chối lịch sự','Hẹn một cuộc gọi','Cảm ơn, sẽ phản hồi sau'].map(h=>[h,h])];
  S.hints = hints;
  sheet(`<div class="meta">Trả lời ${esc(m.from_name||m.from)}</div><h2 style="margin-bottom:12px">Re: ${esc(m.subject)}</h2>
    <div class="chips" style="padding-top:0;margin-bottom:10px">${hints.map((h,i)=>`<button class="chip" onclick="redraft('${uid}', S.hints[${i}][1])">${esc(h[0])}</button>`).join('')}</div>
    <label class="field"><span>Nội dung trả lời</span><textarea id="rpBody" style="min-height:200px" placeholder="AI đang viết nháp…"></textarea></label>
    <button class="btn pri full" id="rpSend">${ico('send')} Gửi qua Gmail</button>`);
  redraft(uid, '');
  $('#rpSend').onclick = async () => {
    const body = $('#rpBody').value.trim(); if(!body) return toast('Nội dung đang trống');
    const b = $('#rpSend'); b.disabled = true; b.innerHTML = '<span class="spin"></span> Đang gửi';
    try{ const subj = /^re:/i.test(m.subject) ? m.subject : 'Re: '+m.subject;
      const r = await run('email','gui',{platform:'gmail', to:m.from, subject:subj, body, reply_uid:uid},'Gửi thư');
      m.status='replied'; closeSheet(); toast(r.text); render(); }
    catch(e){ toast(e.message); b.disabled=false; b.innerHTML = `${ico('send')} Gửi qua Gmail`; }
  };
}
async function redraft(uid, hint){
  const t = $('#rpBody'); if(!t) return; t.value=''; t.placeholder='AI đang viết nháp…';
  try{ const r = await run('email','nhap',{uid, hint},'Viết nháp trả lời'); if($('#rpBody')) $('#rpBody').value = r.text || ''; }
  catch(e){ if($('#rpBody')) $('#rpBody').placeholder = 'Viết câu trả lời của bạn'; toast(e.message); }
}
function openCompose(){
  const p = S.mail.platforms||{}; S.plat = 'gmail';
  sheet(`<h2>Soạn thư</h2><p class="lead">Gõ ý chính để AI viết giúp, hoặc tự viết.</p>
    <div class="seg" style="margin-bottom:14px" id="platSeg"><button class="on" data-p="gmail">Gmail</button><button data-p="lark" ${p.lark?'':'aria-disabled="true"'}>Lark Mail</button></div>
    ${p.lark?'':`<p class="muted small" style="margin:-6px 0 14px">Lark Mail chưa kết nối. <button class="addlink" onclick="openAction('caidat','larkmail')">Kết nối</button></p>`}
    <label class="field"><span>Gửi tới</span><input type="text" id="cpTo" inputmode="email" placeholder="ten@congty.com, ..."></label>
    <div class="nl"><input id="cpBrief" placeholder="Ý chính, ví dụ: hẹn CJ họp thứ 5 về phí fulfillment"><button class="btn pri" id="cpAI">${ico('spark',17)} Viết</button></div>
    <label class="field"><span>Tiêu đề</span><input type="text" id="cpSubj"></label>
    <label class="field"><span>Nội dung</span><textarea id="cpBody" style="min-height:200px"></textarea></label>
    <button class="btn pri full" id="cpSend">${ico('send')} Gửi</button>`);
  document.querySelectorAll('#platSeg button').forEach(b => b.onclick = () => {
    if(b.dataset.p==='lark' && !p.lark) return toast('Kết nối Lark Mail trước');
    S.plat = b.dataset.p; document.querySelectorAll('#platSeg button').forEach(x=>x.classList.toggle('on', x===b));
  });
  $('#cpAI').onclick = async () => {
    const brief = $('#cpBrief').value.trim(); if(!brief) return toast('Gõ ý chính trước');
    const b = $('#cpAI'); b.disabled = true; b.innerHTML = '<span class="spin"></span>';
    try{ const r = await run('email','soan',{brief},'AI viết thư'); $('#cpSubj').value = r.subject||$('#cpSubj').value; $('#cpBody').value = r.text||''; }catch(e){ toast(e.message); }
    b.disabled = false; b.innerHTML = `${ico('spark',17)} Viết`;
  };
  $('#cpSend').onclick = async () => {
    const to=$('#cpTo').value.trim(), subject=$('#cpSubj').value.trim(), body=$('#cpBody').value.trim();
    if(!to||!subject||!body) return toast('Cần người nhận, tiêu đề và nội dung');
    const b = $('#cpSend'); b.disabled = true; b.innerHTML = '<span class="spin"></span> Đang gửi';
    try{ const r = await run('email','gui',{platform:S.plat, to, subject, body},'Gửi thư'); closeSheet(); toast(r.text); }
    catch(e){ toast(e.message); b.disabled=false; b.innerHTML=`${ico('send')} Gửi`; }
  };
}

/* ---------- Họp (Meeting Studio) */
const ORG = {sellnity:['Sellnity','CEO'], leversphere:['Leversphere','CGO kiêm CAO'], 'ca-nhan':['Cá nhân',''], khac:['Khác','']};
const MTYPES = ['Họp nội bộ','Họp ban lãnh đạo','1-1','Đối tác','Khách hàng','Nhà đầu tư','Tuyển dụng','Đào tạo / chia sẻ','Brainstorm','Báo cáo tiến độ','Khác'];
const SPK_C = ['#2a78d6','#d95926','#199e70','#7C5CE0','#c98500','#d6457a'];
S.mt = { items:[], tax:{}, at:0, open:null, m:null, view:'recap', org:'', rec:null, follow:true };
const fmtT = s => { s = Math.max(0, Math.floor(s||0)); const h = s/3600|0, m = (s%3600)/60|0, x = s%60; return (h?h+':'+String(m).padStart(2,'0'):String(m).padStart(2,'0'))+':'+String(x).padStart(2,'0'); };
const fmtDur = s => { s = Math.round(s||0); return s>=3600 ? `${s/3600|0} giờ ${Math.round(s%3600/60)} phút` : s>=60 ? `${Math.round(s/60)} phút` : `${s} giây`; };
function orgBadge(o, p){ const g = ORG[o]; return g ? `<span class="org ${o}">${esc(g[0])}</span>${p?`<span class="meta" style="margin:0">› ${esc(p)}</span>`:''}` : ''; }
async function meetEnter(force){
  if(S.mt.open) return meetDetailEnter();
  if(!force && Date.now()-S.mt.at < 15000) return;
  try{ const r = await run('hop','danhsach',{},'',true); S.mt.items = r.items||[]; S.mt.tax = r.taxonomy||{}; S.mt.at = Date.now();
    if(S.tab==='meet' && !S.mt.open && !S.mt.rec) $('#app').innerHTML = vMeet(); meetPoll(); }catch(e){ toast(e.message); }
}
function meetPoll(){
  clearTimeout(S.mt.timer);
  const busy = S.mt.items.some(m=>m.status==='queued'||m.status==='working') || (S.mt.m && ['queued','working'].includes(S.mt.m.status));
  if(!busy) return;
  S.mt.timer = setTimeout(async ()=>{
    if(S.tab!=='meet') return;
    if(S.mt.open){ await meetLoad(S.mt.open, true); } else { S.mt.at = 0; await meetEnter(true); }
  }, 6000);
}
function vMeet(){
  if(S.mt.rec) return vRecorder();
  if(S.mt.open) return vMeetDetail();
  const all = S.mt.items, f = S.mt.org, list = all.filter(m=>!f || m.org===f);
  const counts = {}; all.forEach(m=>counts[m.org]=(counts[m.org]||0)+1);
  const groups = {}; list.forEach(m=>{ const d=(m.started||'').slice(0,10); (groups[d]=groups[d]||[]).push(m); });
  return `<div class="date">${all.length?`${all.length} cuộc họp đã ghi`:'Meeting Studio'}</div><h1>Họp</h1>
  <section class="recpad">
    <button class="recbtn" onclick="recStart()" aria-label="Bắt đầu ghi âm cuộc họp"><span class="dot"></span></button>
    <div class="grow"><div class="ttl2" style="font-size:17px">Ghi âm cuộc họp</div><div class="meta" style="margin-top:2px">Đặt điện thoại giữa bàn. superHuy chép lời, tách người nói, làm biên bản và lưu Obsidian.</div></div>
  </section>
  <div class="srcrow">
    <button class="src" onclick="$('#mfile').click()">${ico('upload',20)}<span>Tải file ghi âm</span></button>
    <button class="src" onclick="meetHowTelegram()">${ico('send',20)}<span>Gửi qua Telegram</span></button>
    <button class="src" onclick="meetSoon('online')">${ico('video',20)}<span>superHuy dự họp online</span></button>
    <button class="src" onclick="meetSoon('plaud')">${ico('mic',20)}<span>Thiết bị Plaud</span></button>
  </div>
  <input type="file" id="mfile" accept="audio/*,video/*,.m4a,.mp3,.wav,.aac,.ogg,.opus,.webm,.mp4,.mov,.amr" hidden onchange="meetUpload(this.files[0]);this.value=''">
  <form class="askbar" onsubmit="event.preventDefault();meetAsk($('#mq').value)"><span class="ic">${ico('spark',18)}</span><input id="mq" placeholder="Hỏi lại bất cứ điều gì đã bàn trong các cuộc họp…" autocomplete="off"><button class="btn pri sm">Hỏi</button></form>
  <div id="mans"></div>
  ${all.length?`<div class="chips" style="padding-top:4px;margin-bottom:6px"><button class="chip ${!f?'on':''}" onclick="S.mt.org='';render()">Tất cả ${all.length}</button>${Object.keys(ORG).filter(k=>counts[k]).map(k=>`<button class="chip ${f===k?'on':''}" onclick="S.mt.org='${k}';render()">${ORG[k][0]} ${counts[k]}</button>`).join('')}</div>`:''}
  ${S.mt.at ? (list.length ? Object.entries(groups).map(([d,ms])=>`<div class="grp"><span>${d?viDate(new Date(d+'T12:00')):''}</span></div><div class="card list">${ms.map(meetRow).join('')}</div>`).join('')
    : `<div class="card empty">Chưa có cuộc họp nào. Bấm nút đỏ để ghi âm cuộc họp đầu tiên, hoặc tải file ghi âm có sẵn.</div>`)
    : `<div class="card pad"><div class="skel" style="width:60%"></div><div class="skel"></div></div>`}`;
}
function meetRow(m){
  const busy = m.status==='queued'||m.status==='working';
  return `<button onclick="meetOpen('${m.id}')" class="mrow">
    <div class="grow">
      <div class="row" style="gap:6px;align-items:center;margin-bottom:4px">${orgBadge(m.org, m.project)}${m.type?`<span class="meta" style="margin:0">· ${esc(m.type)}</span>`:''}</div>
      <div class="ttl2">${esc(m.title || (busy?'Cuộc họp đang xử lý':'Cuộc họp'))}</div>
      ${busy?`<div class="pbar"><span style="width:${m.progress||3}%"></span></div><div class="meta">${esc(m.step||'Đang xếp hàng')}</div>`
        : m.status==='error' ? `<div class="meta" style="color:var(--danger)">Lỗi: ${esc(m.err||'')}</div>`
        : `<div class="meta clamp2">${esc(m.summary||'')}</div><div class="meta">${(m.started||'').slice(11,16)} · ${fmtDur(m.duration)}${m.n_dec?` · ${m.n_dec} quyết định`:''}${m.n_next?` · ${m.n_next} việc`:''}</div>`}
    </div><span class="chev">${ico('chev',18)}</span></button>`;
}
function meetSoon(k){
  sheet(k==='online' ? `<h2>superHuy dự họp online</h2><p class="lead">superHuy vào Google Meet / Zoom / Teams như một thành viên tên “superHuy (ghi chú)”, tự ghi âm rồi làm biên bản giống hệt các cuộc họp khác.</p>
    <div class="note">Phần này cần một dịch vụ bot dự họp (Recall.ai, khoảng 0,5–0,7 USD mỗi giờ họp). Khi anh tạo tài khoản và dán API key vào file .env (RECALL_API_KEY), superHuy sẽ tự vào các cuộc họp có link trong lịch của anh.</div>
    <p class="lead">Trong lúc chờ: với họp online trên máy tính, anh bật ghi âm ở đây (điện thoại đặt cạnh loa), hoặc gửi file ghi hình cuộc họp vào bot Telegram / Tải file.</p>`
  : `<h2>Thiết bị Plaud</h2><p class="lead">Khi có Plaud, anh xuất file âm thanh từ app Plaud rồi chia sẻ vào bot Telegram superHuy (hoặc Tải file). superHuy chép lời và làm biên bản theo chuẩn riêng của anh, lưu chung kho để hỏi lại.</p>
    <div class="note">Khi anh có máy, em sẽ nối tự động: file mới trong thư mục đồng bộ của Plaud sẽ tự vào Meeting Studio.</div>`);
}
function meetHowTelegram(){
  sheet(`<h2>Gửi ghi âm qua Telegram</h2><p class="lead">Gửi file ghi âm, voice, hoặc video cuộc họp vào chat với bot superHuy. Ghi chú bối cảnh ở phần chú thích, ví dụ “họp Leversphere, dự án Growth Q4”.</p>
    <div class="note">Telegram giới hạn 20 MB cho bot. File lớn hơn (họp dài) anh dùng Tải file ở trang này, không giới hạn dung lượng.</div>`);
}
async function meetAsk(q, mid){
  q = (q||'').trim(); if(!q) return;
  const box = mid ? $('#mdans') : $('#mans'); if(!box) return;
  box.innerHTML = `<div class="card pad ans"><div class="row" style="gap:10px;align-items:center"><span class="spin"></span><span class="meta" style="margin:0">superHuy đang tìm trong kho cuộc họp…</span></div></div>`;
  try{
    const r = await run('hop','hoi',{question:q, meeting_id: mid||''},'',true);
    box.innerHTML = `<div class="card pad ans"><div class="atext">${esc(r.answer||r.text)}</div>${(r.sources||[]).length?`<div class="srcs">${r.sources.map(s=>`<button class="tchip" onclick="meetOpen('${s.mid}', ${s.t})">${ico('play',12)} [${s.n}] ${esc(s.title.slice(0,32))} · ${s.at}</button>`).join('')}</div>`:''}</div>`;
  }catch(e){ box.innerHTML = `<div class="card pad ans" style="color:var(--danger)">${esc(e.message)}</div>`; }
}

/* upload: chia phần 8 MB, gửi tuần tự (đường hầm giới hạn 100 MB mỗi request) */
async function upPart(uid, seq, blob){
  for(let a=0; a<4; a++){
    try{
      const r = await fetch(`/api/upload?id=${uid}&seq=${seq}`, {method:'POST', headers:{'X-Session':S.tok||'', 'Content-Type':'application/octet-stream'}, body:blob});
      const j = await r.json().catch(()=>({}));
      if(r.ok && j.ok) return j;
      if(r.status===401){ relock(); throw new Error('Đã khoá, nhập PIN rồi thử lại'); }
      throw new Error(j.error||('Lỗi '+r.status));
    }catch(e){ if(a===3) throw e; await new Promise(ok=>setTimeout(ok, 1500*(a+1))); }
  }
}
/* đồng ý ghi âm (quyết định #7, thẻ 15): bản của khách phải bấm [Ghi âm] trên màn xác nhận; trả null nếu huỷ/tạm đóng */
function recConsent(){
  const P = S.data?.rec || {};
  if(P.enabled === false) { sheet(`<h2>Biên bản từ ghi âm</h2><p class="lead">${esc(P.closed_text||'Tạm đóng.')}</p><button class="btn full" onclick="closeSheet()">Đã hiểu</button>`); return Promise.resolve(null); }
  if(!P.consent) return Promise.resolve({});
  return new Promise(ok=>{
    S._rc = v => { closeSheet(); ok(v); };
    sheet(`<h2>Xin đồng ý ghi âm</h2><p class="lead">${esc(P.consent_text||'')}</p>
      <div class="row" style="gap:10px;margin-top:14px"><button class="btn grow" onclick="S._rc(null)">Huỷ</button><button class="btn pri grow" onclick="S._rc({consent:'1'})">${ico('mic',16)} Ghi âm</button></div>`);
  });
}
async function meetUpload(file){
  if(!file) return;
  const cons = await recConsent(); if(cons === null){ const mf=$('#mfile'); if(mf) mf.value=''; return; }
  const uid = 'up'+Date.now().toString(36)+Math.random().toString(36).slice(2,6), CH = 8*1024*1024, n = Math.ceil(file.size/CH);
  sheet(`<h2>Tải file ghi âm</h2><p class="lead">${esc(file.name)} · ${(file.size/1048576).toFixed(1)} MB</p>
    <label class="field"><span>Bối cảnh (không bắt buộc)</span><input type="text" id="uhint" placeholder="Ví dụ: họp Leversphere, dự án Growth Q4, có anh Nam bên đối tác"></label>
    <div class="pbar big"><span id="upb" style="width:0%"></span></div><p class="meta" id="upt">Đang tải lên…</p>`);
  try{
    for(let i=0;i<n;i++){ await upPart(uid, i, file.slice(i*CH, (i+1)*CH)); const p = Math.round((i+1)/n*100); const b=$('#upb'); if(b){ b.style.width=p+'%'; $('#upt').textContent=`Đã tải ${p}%`; } }
    const started = file.lastModified ? new Date(file.lastModified - 0).toISOString().slice(0,19) : '';
    const r = await run('hop','tao',{upload_id:uid, name:file.name, hint:$('#uhint')?.value||'', source:'Tải file', ...cons},'',true);
    closeSheet(); toast(r.text, 4000); S.mt.at = 0; meetEnter(true);
  }catch(e){ const t=$('#upt'); if(t){ t.textContent = 'Lỗi: '+e.message; t.style.color='var(--danger)'; } else toast(e.message); }
}

/* ghi âm trong app */
async function recStart(){
  const cons = await recConsent(); if(cons === null) return;
  if(!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) return toast('Thiết bị này chưa cho ghi âm trong app. Anh dùng app ghi âm của máy rồi Tải file nhé.', 5000);
  let stream;
  try{ stream = await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:false, noiseSuppression:true, autoGainControl:true, channelCount:1}}); }
  catch(e){ return toast('Chưa có quyền dùng micro. Anh cho phép Telegram dùng micro trong Cài đặt của điện thoại rồi thử lại.', 6000); }
  const mime = ['audio/webm;codecs=opus','audio/mp4','audio/webm','audio/ogg'].find(t=>MediaRecorder.isTypeSupported?.(t)) || '';
  const rec = new MediaRecorder(stream, mime?{mimeType:mime, audioBitsPerSecond:48000}:{});
  const R = S.mt.rec = { uid:'rec'+Date.now().toString(36), seq:0, queue:Promise.resolve(), rec, stream, t0:Date.now(), paused:0, pauseAt:0,
    started:new Date(Date.now()-new Date().getTimezoneOffset()*60000).toISOString().slice(0,19), ext:(rec.mimeType||mime).includes('mp4')?'m4a':'webm', failed:0, sent:0, cons };
  rec.ondataavailable = e => { if(!e.data || !e.data.size) return; const seq = R.seq++; R.queue = R.queue.then(()=>upPart(R.uid, seq, e.data).then(()=>{ R.sent++; }).catch(()=>{ R.failed++; })); };
  rec.start(10000);
  try{ R.wake = await navigator.wakeLock?.request('screen'); }catch(e){}
  const ctx = new (window.AudioContext||window.webkitAudioContext)(), an = ctx.createAnalyser(); an.fftSize = 512; ctx.createMediaStreamSource(stream).connect(an); R.ctx = ctx; R.an = an;
  haptic('medium'); render(); recTick();
}
function recTick(){
  const R = S.mt.rec; if(!R) return; cancelAnimationFrame(R.raf);
  const el = $('#rtime'); if(el){ const s = ((R.pauseAt||Date.now()) - R.t0 - R.paused)/1000; el.textContent = fmtT(s); }
  const cv = $('#rwave');
  if(cv && R.an && !R.pauseAt){
    const g = cv.getContext('2d'), w = cv.width, h = cv.height, d = new Uint8Array(R.an.fftSize); R.an.getByteTimeDomainData(d);
    let peak = 0; for(const v of d) peak = Math.max(peak, Math.abs(v-128)/128);
    R.hist = (R.hist||[]).concat(peak).slice(-64);
    g.clearRect(0,0,w,h); g.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--rec').trim()||'#e5484d';
    const bw = w/64; R.hist.forEach((p,i)=>{ const bh = Math.max(4, Math.min(1, p*2.4)*h*0.9); g.beginPath(); g.roundRect?.(i*bw+bw*0.2, (h-bh)/2, bw*0.6, bh, 3); g.fill(); });
  }
  R.raf = requestAnimationFrame(recTick);
}
function vRecorder(){
  const R = S.mt.rec;
  return `<div class="recview">
    <div class="date">${R.pauseAt?'Đã tạm dừng':'Đang ghi âm'} · tự lưu lên máy mỗi 10 giây</div>
    <div id="rtime" class="rtime">00:00</div>
    <canvas id="rwave" width="640" height="120" class="rwave" aria-hidden="true"></canvas>
    <label class="field"><span>Tiêu đề (không bắt buộc)</span><input type="text" id="rtitle" value="${esc(R.title||'')}" oninput="S.mt.rec.title=this.value" placeholder="superHuy tự đặt nếu để trống"></label>
    <label class="field"><span>Bối cảnh giúp phân loại đúng</span><input type="text" id="rhint" value="${esc(R.hint||'')}" oninput="S.mt.rec.hint=this.value" placeholder="Ví dụ: họp Sellnity, dự án AI Agent Factory"></label>
    <div class="row" style="justify-content:center;gap:18px;margin-top:8px">
      <button class="round" aria-label="Huỷ bản ghi" onclick="recCancel()">${ico('x')}</button>
      <button class="recstop" aria-label="Dừng và làm biên bản" onclick="recStop()"><span></span></button>
      <button class="round" aria-label="${R.pauseAt?'Tiếp tục':'Tạm dừng'}" onclick="recPause()">${ico(R.pauseAt?'mic':'pause')}</button>
    </div>
    <p class="muted small" style="text-align:center;margin-top:14px">Giữ màn hình mở trong lúc ghi (điện thoại khoá màn hình có thể dừng micro). Dừng để superHuy làm biên bản.</p>
  </div>`;
}
function recPause(){
  const R = S.mt.rec; if(!R) return;
  if(R.pauseAt){ R.paused += Date.now()-R.pauseAt; R.pauseAt = 0; R.rec.resume(); } else { R.pauseAt = Date.now(); R.rec.pause(); }
  haptic(); render();
}
function recEnd(){ const R = S.mt.rec; cancelAnimationFrame(R.raf); try{ R.stream.getTracks().forEach(t=>t.stop()); }catch(e){} try{ R.ctx.close(); }catch(e){} try{ R.wake?.release(); }catch(e){} }
async function recStop(){
  const R = S.mt.rec; if(!R) return;
  const secs = ((R.pauseAt||Date.now()) - R.t0 - R.paused)/1000;
  await new Promise(ok=>{ R.rec.onstop = ok; R.rec.stop(); }); recEnd();
  $('#app').innerHTML = `<div class="recview"><div class="rtime" style="font-size:28px">Đang gửi bản ghi…</div><p class="meta" style="text-align:center">${fmtDur(secs)} âm thanh</p></div>`;
  await R.queue;
  S.mt.rec = null;
  if(secs < 3){ toast('Bản ghi quá ngắn'); return render(); }
  if(R.failed){ toast(`${R.failed} phần chưa gửi được do mạng, biên bản có thể thiếu một đoạn.`, 5000); }
  try{ const r = await run('hop','tao',{upload_id:R.uid, name:'rec.'+R.ext, title:R.title||'', hint:R.hint||'', started:R.started, source:'Ghi âm trong app', ...(R.cons||{})},'',true);
    toast(r.text, 4000); notifyH('success'); }catch(e){ toast(e.message, 5000); }
  S.mt.at = 0; render();
}
function recCancel(){
  const R = S.mt.rec; if(!R) return;
  sheet(`<h2>Huỷ bản ghi này?</h2><p class="lead">Âm thanh đã ghi sẽ không được làm biên bản.</p><div class="row"><button class="btn grow" onclick="closeSheet()">Ghi tiếp</button><button class="btn grow" style="color:var(--danger)" onclick="closeSheet();try{S.mt.rec.rec.stop()}catch(e){};recEnd();S.mt.rec=null;render()">Huỷ bản ghi</button></div>`);
}

/* chi tiết cuộc họp */
async function meetOpen(id, t){ S.mt.open = id; S.mt.view = 'recap'; S.mt.seekTo = t; S.tab = 'meet'; closeSheet(); render(); window.scrollTo(0,0); }
async function meetLoad(id, quiet){
  try{ const m = await run('hop','xem',{id},'',true); if(S.mt.open!==id) return; S.mt.m = m; if(S.tab==='meet' && !$('#sheet').classList.contains('on')){ const y = scrollY; $('#app').innerHTML = vMeetDetail(); meetBind(); if(quiet) scrollTo(0,y); } meetPoll(); }
  catch(e){ toast(e.message); S.mt.open = null; render(); }
}
function meetDetailEnter(){ if(!S.mt.m || S.mt.m.id!==S.mt.open) return meetLoad(S.mt.open); meetBind(); }
function meetBack(){ S.mt.open = null; S.mt.m = null; S.mt.at = 0; render(); }
const spkName = (m, k) => (m.speakers?.[k]?.name) || ('Người nói '+String(k).replace(/\D/g,''));
const spkColor = (m, k) => SPK_C[Object.keys(m.speakers||{}).indexOf(k) % SPK_C.length] || SPK_C[0];
const tc = t => (t===undefined||t===null||t==='') ? '' : `<button class="tchip" onclick="seek(${+t})" aria-label="Nghe lại từ ${fmtT(t)}">${ico('play',11)} ${fmtT(t)}</button>`;
function vMeetDetail(){
  const m = S.mt.m;
  if(!m || m.id!==S.mt.open) return `<button class="back" onclick="meetBack()">${ico('chev',18)} Họp</button><div class="card pad"><div class="skel" style="width:70%"></div><div class="skel"></div><div class="skel" style="width:50%"></div></div>`;
  const lab = m.labels||{}, r = m.recap||{}, busy = ['queued','working'].includes(m.status), v = S.mt.view;
  const head = `<button class="back" onclick="meetBack()">${ico('chev',18)} Họp</button>
    <div class="row" style="gap:6px;align-items:center;margin:6px 0 2px;flex-wrap:wrap">${orgBadge(lab.org, lab.project)}${lab.department?`<span class="meta" style="margin:0">› ${esc(lab.department)}</span>`:''}${lab.type?`<span class="meta" style="margin:0">· ${esc(lab.type)}</span>`:''}
      ${m.status==='done'?`<button class="addlink" onclick="meetLabels()">${ico('pen',14)} Phân loại</button><button class="addlink" onclick="meetShare()">${ico('upload',14)} Chia sẻ</button>`:''}</div>
    <h1 style="font-size:24px;margin:4px 0 4px">${esc(m.title || 'Cuộc họp')}</h1>
    <div class="meta">${(m.started||'').slice(11,16)} ${(m.started||'').slice(8,10)}/${(m.started||'').slice(5,7)} · ${fmtDur(m.duration)} · ${esc(m.source||'')}</div>
    <div class="player"><audio id="mau" src="${m.audio}" preload="metadata" controls></audio>
      <div class="row" style="gap:6px;margin-top:6px;align-items:center"><span class="meta" style="margin:0">Tốc độ</span>${[1,1.25,1.5,2].map(x=>`<button class="spd ${(S.mt.rate||1)===x?'on':''}" onclick="setRate(${x})">${x}×</button>`).join('')}</div></div>`;
  if(busy) return head + `<div class="card pad" style="margin-top:14px"><div class="ttl2">${esc(m.step||'Đang xử lý')}</div><div class="pbar big"><span style="width:${m.progress||3}%"></span></div>
    <p class="meta">Họp 1 giờ thường mất 3–6 phút. Anh có thể rời trang, xong superHuy sẽ báo qua Telegram.</p></div>`;
  if(m.status==='error') return head + `<div class="card pad" style="margin-top:14px"><div class="ttl2" style="color:var(--danger)">Chưa làm được biên bản</div><p class="meta">${esc(m.err||'')}</p>
    <button class="btn pri" onclick="meetRedo('all')">${ico('refresh')} Thử lại</button></div>`;
  const seg = `<div class="seg" style="margin:14px 0 12px">${[['recap','Biên bản'],['map','Sơ đồ'],['text','Lời thoại']].map(([k,l])=>`<button class="${v===k?'on':''}" onclick="S.mt.view='${k}';$('#mbody').innerHTML=meetBody();meetBindBody()">${l}</button>`).join('')}</div>`;
  return head + seg + `<div id="mbody">${meetBody()}</div>
    <div class="sec"><h2>Hỏi về cuộc họp này</h2></div>
    <form class="askbar" onsubmit="event.preventDefault();meetAsk($('#mdq').value,'${m.id}')"><span class="ic">${ico('spark',18)}</span><input id="mdq" placeholder="Ví dụ: ai phụ trách việc X, đã chốt ngân sách bao nhiêu?" autocomplete="off"><button class="btn pri sm">Hỏi</button></form><div id="mdans"></div>
    <div class="card list" style="margin-top:16px">
      ${m.obsidian_rel?`<div><span class="thumb">${ico('brain',20)}</span><div class="grow"><div style="font-weight:600">Đã lưu vào Obsidian</div><div class="meta">${esc(m.obsidian_rel)}</div></div></div>`:''}
      <button onclick="meetShare()"><span class="thumb">${ico('upload',20)}</span><div class="grow"><div style="font-weight:600">Chia sẻ biên bản</div><div class="meta">Trang web có sơ đồ, gửi qua Telegram, Zalo, email, nhóm Lark</div></div></button>
      <button onclick="meetRedo('recap')"><span class="thumb">${ico('refresh',20)}</span><div class="grow"><div style="font-weight:600">Biên tập lại biên bản</div><div class="meta">Giữ lời thoại, AI viết lại tóm tắt, quyết định, sơ đồ</div></div></button>
      <button onclick="meetRedo('all')"><span class="thumb">${ico('mic',20)}</span><div class="grow"><div style="font-weight:600">Chép lời lại từ đầu</div><div class="meta">Dùng khi lời thoại sai nhiều (sau khi thêm từ điển)</div></div></button>
      <button onclick="meetDelete()"><span class="thumb" style="color:var(--danger)">${ico('del',20)}</span><div class="grow"><div style="font-weight:600;color:var(--danger)">Xoá cuộc họp</div><div class="meta">Chuyển vào thùng rác trên máy</div></div></button>
    </div>`;
}
function meetBody(){
  const m = S.mt.m, r = m.recap||{}, v = S.mt.view;
  if(v==='text'){
    const segs = m.segments||[];
    return `<div class="spkrow">${Object.keys(m.speakers||{}).map(k=>`<button class="spk" style="--c:${spkColor(m,k)}" onclick="meetRename('${k}')"><i></i>${esc(spkName(m,k))} ${ico('pen',12)}</button>`).join('')}</div>
      <label class="row" style="gap:8px;align-items:center;margin:4px 0 10px"><input type="checkbox" ${S.mt.follow?'checked':''} onchange="S.mt.follow=this.checked"><span class="meta" style="margin:0">Tự cuộn theo âm thanh</span></label>
      <div class="tx" id="tx">${segs.map((s,i)=>`<div class="ln" data-i="${i}" data-s="${s.s}" onclick="seek(${s.s})"><span class="tt">${fmtT(s.s)}</span><div><b style="color:${spkColor(m,s.spk)}">${esc(spkName(m,s.spk))}</b><p>${esc(s.text)}</p></div></div>`).join('')}</div>`;
  }
  if(v==='map') return meetMap();
  const li = (arr, extra) => arr.map(x=>`<li><div class="grow">${esc(x.text)}${extra?extra(x):''}</div>${tc(x.t)}</li>`).join('');
  return `<p class="lead" style="margin:0 0 14px">${esc(r.summary||'')}</p>
    ${(r.decisions||[]).length?`<div class="mblk dec"><h3>${ico('check',17)} Quyết định</h3><ul>${li(r.decisions, x=>x.owner?`<div class="meta">${esc(x.owner)}</div>`:'')}</ul></div>`:''}
    ${(r.next_steps||[]).length?`<div class="mblk nxt"><h3>${ico('arrow',17)} Việc tiếp theo</h3><ul>${r.next_steps.map((x,i)=>`<li><div class="grow">${esc(x.text)}<div class="meta">${[x.owner, x.due?('hạn '+x.due.split('-').reverse().slice(0,2).join('/')):''].filter(Boolean).map(esc).join(' · ')}</div>
      <button class="addlink" onclick="meetTask(${i})">${ico('plus',14)} Tạo việc</button></div>${tc(x.t)}</li>`).join('')}</ul></div>`:''}
    ${(r.suggestions||[]).length?`<div class="mblk sgt"><h3>${ico('spark',17)} superHuy đề xuất</h3><ul>${li(r.suggestions)}</ul></div>`:''}
    ${(r.open_questions||[]).length?`<div class="mblk opn"><h3>? Còn bỏ ngỏ</h3><ul>${li(r.open_questions)}</ul></div>`:''}
    ${(r.sections||[]).length?`<div class="sec"><h2>Diễn biến</h2></div>${r.sections.map(s=>`<div class="card pad flow"><div class="row" style="align-items:center;gap:8px"><h3 class="grow">${esc(s.title)}</h3>${tc(s.t)}</div><ul>${li(s.points||[])}</ul></div>`).join('')}`:''}`;
}
function meetMap(){
  const m = S.mt.m, r = m.recap||{}, mm = r.mindmap, dur = m.duration||1;
  const secs = (r.sections||[]).map((s,i,a)=>({title:s.title, t:+s.t||0, e: i+1<a.length ? (+a[i+1].t||dur) : dur}));
  const tl = secs.length ? `<div class="sec" style="margin-top:0"><h2>Dòng thời gian</h2><span class="meta">${fmtDur(dur)}</span></div>
    <div class="tline">${secs.map((s,i)=>`<button style="flex:${Math.max(.04,(s.e-s.t)/dur)};--c:${SPK_C[i%SPK_C.length]}" onclick="seek(${s.t})" data-tip="${esc(s.title)} · ${fmtT(s.t)}"><span>${esc(s.title)}</span></button>`).join('')}</div>
    <div class="tlist">${secs.map((s,i)=>`<button onclick="seek(${s.t})"><i style="background:${SPK_C[i%SPK_C.length]}"></i><span class="grow">${esc(s.title)}</span><span class="meta" style="margin:0">${fmtT(s.t)}</span></button>`).join('')}</div>` : '';
  if(!mm || !(mm.children||[]).length) return tl || `<div class="card empty">Chưa có sơ đồ cho cuộc họp này.</div>`;
  // bố cục cây ngang: gốc bên trái, nhánh và ý xếp theo cột
  const COLW = 168, NW = 150, LH = 17, PAD = 10, GAP = 12, nodes = [], links = [];
  const wrap = (s, max=19) => { const w = String(s||'').split(/\s+/), out = []; let cur=''; w.forEach(x=>{ if((cur+' '+x).trim().length>max){ if(cur) out.push(cur); cur=x; } else cur=(cur+' '+x).trim(); }); if(cur) out.push(cur); return out.slice(0,3); };
  let y = 0;
  function place(n, depth){
    const hasT = depth>0 && n.t!==undefined && n.t!==null, lines = wrap(n.label), h = (lines.length + (hasT?1:0))*LH + PAD*2, kids = (n.children||[]).slice(0,8);
    const node = {lines, h, depth, t:n.t, x: depth*COLW};
    if(!kids.length){ node.y = y; y += h + GAP; }
    else { const ch = kids.map(k=>place(k, depth+1)); node.y = (ch[0].y + ch[ch.length-1].y + ch[ch.length-1].h)/2 - h/2; ch.forEach(c=>links.push([node,c])); }
    nodes.push(node); return node;
  }
  place({label: mm.label || m.title, children: mm.children}, 0);
  const W = (Math.max(...nodes.map(n=>n.depth))+1)*COLW, H = y;
  const svg = `<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Sơ đồ cuộc họp">
    ${links.map(([a,b])=>{ const x1=a.x+NW, y1=a.y+a.h/2, x2=b.x, y2=b.y+b.h/2, mx=(x1+x2)/2; return `<path d="M${x1} ${y1} C${mx} ${y1} ${mx} ${y2} ${x2} ${y2}" class="mlink"/>`; }).join('')}
    ${nodes.map(n=>`<g class="mnode d${Math.min(n.depth,2)} ${n.t!==undefined&&n.t!==null?'click':''}" ${n.t!==undefined&&n.t!==null?`onclick="seek(${+n.t})"`:''} transform="translate(${n.x},${n.y})">
      <rect width="${NW}" height="${n.h}" rx="12"/>${n.lines.map((l,i)=>`<text x="12" y="${PAD+LH*(i+1)-4}">${esc(l)}</text>`).join('')}
      ${n.t!==undefined&&n.t!==null&&n.depth?`<text x="12" y="${PAD+LH*(n.lines.length+1)-3}" class="mt">▶ ${fmtT(n.t)}</text>`:''}</g>`).join('')}</svg>`;
  return tl + `<div class="sec"><h2>Sơ đồ ý chính</h2><span class="meta">Chạm vào ý để nghe lại</span></div><div class="mmap">${svg}</div>`;
}
function meetBind(){
  const a = $('#mau'); if(!a) return;
  a.playbackRate = S.mt.rate||1;
  a.ontimeupdate = () => meetFollow(a.currentTime);
  if(S.mt.seekTo!==undefined && S.mt.seekTo!==null){ const t = S.mt.seekTo; S.mt.seekTo = null; a.addEventListener('loadedmetadata', ()=>{ a.currentTime = t; }, {once:true}); toast('Bấm ▶ để nghe đoạn '+fmtT(t)); }
  meetBindBody(); tipBind?.();
}
function meetBindBody(){ meetFollow($('#mau')?.currentTime||0, true); }
function meetFollow(t, force){
  const tx = $('#tx'); if(!tx) return;
  const lines = tx.querySelectorAll('.ln'); let cur = null;
  lines.forEach(l=>{ if(+l.dataset.s <= t+0.3) cur = l; });
  if(cur && (cur!==S.mt.curLn || force)){ S.mt.curLn?.classList.remove('on'); cur.classList.add('on'); S.mt.curLn = cur;
    if(S.mt.follow && !force){ const r = cur.getBoundingClientRect(); if(r.top < 140 || r.bottom > innerHeight-120) scrollBy({top: r.top - innerHeight/3, behavior:'smooth'}); } }
}
function seek(t){
  const a = $('#mau'); if(!a) return;
  a.currentTime = Math.max(0, (+t||0) - 1); a.play().catch(()=>{}); haptic();
  const p = $('.player'); if(p){ const r = p.getBoundingClientRect(); if(r.top < 0 || r.bottom > innerHeight) p.scrollIntoView({behavior:'smooth', block:'start'}); }
}
function setRate(x){ S.mt.rate = x; const a = $('#mau'); if(a) a.playbackRate = x; document.querySelectorAll('.spd').forEach(b=>b.classList.toggle('on', b.textContent===x+'×')); }
function meetRename(k){
  const m = S.mt.m, known = Object.keys(S.mt.tax?.people||{}).slice(0,30);
  sheet(`<h2>Đặt tên người nói</h2><p class="lead">${esc(spkName(m,k))} · ${esc(m.speakers?.[k]?.voice||'')}</p>
    <label class="field"><span>Tên</span><input type="text" id="spkn" list="ppl" value="${esc(m.speakers?.[k]?.name||'')}" placeholder="Ví dụ: Lan (Marketing)"></label><datalist id="ppl">${known.map(p=>`<option value="${esc(p)}">`).join('')}</datalist>
    <button class="btn pri full" onclick="meetRenameSave('${k}')">Lưu</button>`);
  setTimeout(()=>$('#spkn')?.focus(), 200);
}
async function meetRenameSave(k){
  const name = $('#spkn').value.trim(); if(!name) return toast('Nhập tên');
  try{ await run('hop','doi_ten',{mid:S.mt.m.id, spk:k, name},'',true); S.mt.m.speakers[k].name = name; closeSheet(); $('#mbody').innerHTML = meetBody(); meetBindBody(); toast('Đã đổi tên, Obsidian đã cập nhật'); }catch(e){ toast(e.message); }
}
function meetLabels(){
  const m = S.mt.m, l = {...(m.labels||{})}, tax = S.mt.tax||{}; S.mt.lab = l;
  const projs = [...new Set(Object.values(tax.projects||{}).flat())], depts = [...new Set(Object.values(tax.departments||{}).flat())];
  const paint = () => sheet(`<h2>Phân loại cuộc họp</h2><p class="lead">superHuy tự phân loại; anh sửa ở đây thì Obsidian tự cập nhật đúng thư mục, thẻ và liên kết.</p>
    <p class="lbl">Tổ chức</p><div class="chips" style="padding-top:0;flex-wrap:wrap;margin-bottom:12px">${Object.entries(ORG).map(([k,v])=>`<button class="chip ${l.org===k?'on':''}" onclick="S.mt.lab.org='${k}';S.mt.lpaint()">${v[0]}${v[1]?` · ${v[1]}`:''}</button>`).join('')}</div>
    <label class="field"><span>Dự án</span><input type="text" id="lp" list="lpl" value="${esc(l.project||'')}" oninput="S.mt.lab.project=this.value"></label><datalist id="lpl">${projs.map(p=>`<option value="${esc(p)}">`).join('')}</datalist>
    <label class="field"><span>Phòng ban</span><input type="text" id="ld" list="ldl" value="${esc(l.department||'')}" oninput="S.mt.lab.department=this.value"></label><datalist id="ldl">${depts.map(p=>`<option value="${esc(p)}">`).join('')}</datalist>
    <p class="lbl">Loại cuộc họp</p><div class="chips" style="padding-top:0;flex-wrap:wrap;margin-bottom:12px">${MTYPES.map(t=>`<button class="chip ${l.type===t?'on':''}" onclick="S.mt.lab.type='${t}';S.mt.lpaint()">${t}</button>`).join('')}</div>
    <button class="btn pri full" onclick="meetLabelsSave()">Lưu phân loại</button>`);
  S.mt.lpaint = () => { const y = $('#sheet').scrollTop; paint(); $('#sheet').scrollTop = y; }; paint();
}
async function meetLabelsSave(){
  const l = S.mt.lab;
  try{ await run('hop','nhan',{id:S.mt.m.id, org:l.org||'', project:l.project||'', department:l.department||'', type:l.type||''},'',true); S.mt.m.labels = l; closeSheet(); render(); toast('Đã lưu phân loại'); }catch(e){ toast(e.message); }
}
async function meetTask(i){
  const m = S.mt.m, x = (m.recap?.next_steps||[])[i]; if(!x) return;
  try{ await run('viec','tao',{title:x.text, due:x.due||'', assignee:x.owner||'', labels:[ORG[m.labels?.org]?.[0], m.labels?.project].filter(Boolean).join(','), notes:`Từ cuộc họp: ${m.title} (${(m.started||'').slice(0,10)}, phút ${fmtT(x.t)})`},'Tạo việc');
    toast('Đã tạo việc trong trang Việc'); S.tk && (S.tk.at = 0); }catch(e){ toast(e.message); }
}
async function meetRedo(what){ try{ const r = await run('hop','lam_lai',{mid:S.mt.m.id, what},'',true); toast(r.text); meetLoad(S.mt.m.id); }catch(e){ toast(e.message); } }
function meetDelete(){
  sheet(`<h2>Xoá cuộc họp này?</h2><p class="lead">Cuộc họp được chuyển vào thùng rác trên máy (data/meetings/_trash). Ghi chú trong Obsidian vẫn giữ.</p>
    <div class="row"><button class="btn grow" onclick="closeSheet()">Giữ lại</button><button class="btn grow" style="color:var(--danger)" onclick="meetDeleteGo()">Xoá</button></div>`);
}
async function meetDeleteGo(){ try{ await run('hop','xoa',{mid:S.mt.m.id},'',true); closeSheet(); meetBack(); toast('Đã xoá'); }catch(e){ toast(e.message); } }

/* ---------- chia sẻ biên bản họp: trang web, chat, email, Lark */
const SHARE_PARTS = [['summary','Tóm tắt'],['decisions','Quyết định'],['next_steps','Ai làm gì'],['mindmap','Sơ đồ'],['sections','Diễn biến'],['open_questions','Còn bỏ ngỏ'],['suggestions','Đề xuất của superHuy'],['transcript','Lời thoại'],['audio','Âm thanh']];
async function meetShare(){
  const m = S.mt.m; if(!m) return;
  S.sh = {mid:m.id, parts:['summary','decisions','next_steps','mindmap','sections','open_questions'], days:14, note:'', last:null, links:[], groups:null};
  shPaint(); shLoadLinks();
}
function shPaint(){
  const h = S.sh, y = $('#sheet').classList.contains('on') ? $('#sheet').scrollTop : 0;
  sheet(`<h2>Chia sẻ biên bản</h2><p class="lead">Chọn phần muốn gửi. superHuy tạo một trang web riêng (có dòng thời gian và sơ đồ) kèm tin nhắn soạn sẵn.</p>
    <p class="lbl">Gồm những phần</p><div class="chips" style="padding-top:0;flex-wrap:wrap;margin-bottom:14px">${SHARE_PARTS.map(([k,l])=>`<button class="chip ${h.parts.includes(k)?'on':''}" aria-pressed="${h.parts.includes(k)}" onclick="shToggle('${k}')">${l}</button>`).join('')}</div>
    ${h.parts.some(p=>['transcript','audio','suggestions'].includes(p))?`<p class="meta" style="margin:-6px 0 12px;color:var(--amber)">Lưu ý: lời thoại, âm thanh và đề xuất nội bộ sẽ hiện với người nhận.</p>`:''}
    <p class="lbl">Liên kết hiệu lực</p><div class="chips" style="padding-top:0;margin-bottom:14px">${[[3,'3 ngày'],[14,'14 ngày'],[30,'30 ngày']].map(([d,l])=>`<button class="chip ${h.days===d?'on':''}" onclick="S.sh.days=${d};shPaint()">${l}</button>`).join('')}</div>
    <label class="field"><span>Lời nhắn kèm (không bắt buộc)</span><textarea id="shNote" rows="2" placeholder="Ví dụ: Gửi team biên bản họp sáng nay, mọi người xem phần Ai làm gì nhé." oninput="S.sh.note=this.value">${esc(h.note)}</textarea></label>
    <p class="lbl">Gửi qua</p>
    <div class="shgrid">
      <button onclick="shGo('web')"><i style="--c:#7B5CF0">${ico('link',20)}</i>Trang web</button>
      <button onclick="shGo('tg')"><i style="--c:#2AABEE">${ico('send',20)}</i>Telegram</button>
      <button onclick="shGo('native')"><i style="--c:#0068FF">${ico('upload',20)}</i>Zalo, Messenger…</button>
      <button onclick="shGo('copy')"><i style="--c:#199e70">${ico('copy',20)}</i>Sao chép tin nhắn</button>
      <button onclick="shEmail()"><i style="--c:#d95926">${ico('mail',20)}</i>Email</button>
      <button onclick="shLark()"><i style="--c:#1F7AE0">${ico('lark',20)}</i>Nhóm Lark</button>
    </div>
    <div id="shOut">${h.last?shLastHtml():''}</div>
    <div id="shLinks">${shLinksHtml()}</div>`);
  $('#sheet').scrollTop = y;
}
/* thẻ 15 (họp 17/10): lời thoại/âm thanh chỉ kèm khi người dùng xác nhận lại */
function askOK(msg){ return new Promise(ok=>{ if(tg?.showConfirm){ try{ return tg.showConfirm(msg, r=>ok(!!r)); }catch(e){} } ok(window.confirm(msg)); }); }
async function shConfirm(){
  const h = S.sh, sens = h.parts.filter(p=>p==='transcript'||p==='audio');
  if(!sens.length) return '';
  const ok = await askOK('Liên kết sẽ kèm '+(sens.length===2?'lời thoại và âm thanh gốc':sens[0]==='audio'?'âm thanh gốc':'lời thoại')+' của cuộc họp. Ai có liên kết đều nghe/đọc được. Bạn chắc chắn chia sẻ?');
  if(!ok) throw new Error('Đã huỷ chia sẻ');
  return '1';
}
function shToggle(k){ const p = S.sh.parts; S.sh.parts = p.includes(k) ? p.filter(x=>x!==k) : [...p, k]; S.sh.last = null; shPaint(); }
async function shMake(){
  const h = S.sh; if(!h.parts.length) throw new Error('Chọn ít nhất 1 phần');
  if(h.last && h.last.key === h.parts.join()+h.days+h.note) return h.last;
  const confirm = await shConfirm();
  const r = await run('hop','chia_se_ui',{mid:h.mid, channel:'web', parts:h.parts.join(','), days:h.days, note:h.note, confirm},'',true);
  h.last = {...r, key:h.parts.join()+h.days+h.note}; shLoadLinks(); return h.last;
}
function shLastHtml(){ const l = S.sh.last; return `<div class="card pad shlink"><div class="meta" style="margin:0 0 6px">Liên kết hết hạn ${esc(l.expires)}</div><div class="url">${esc(l.url)}</div>
  <div class="row" style="margin-top:10px"><button class="btn sm" onclick="copyText(S.sh.last.url)">${ico('copy',16)} Chép link</button><button class="btn sm" onclick="openLink(S.sh.last.url)">${ico('arrow',16)} Xem trang</button></div></div>`; }
async function shGo(how){
  try{
    const l = await shMake(), out = $('#shOut'); if(out) out.innerHTML = shLastHtml();
    if(how==='tg'){ const u = `https://t.me/share/url?url=${encodeURIComponent(l.url)}&text=${encodeURIComponent(l.message.replace(/\n🔗[^\n]*$/,''))}`; tg?.openTelegramLink ? tg.openTelegramLink(u) : openLink(u); run('hop','da_gui',{token:l.token, how:'Telegram'},'',true).catch(()=>{}); }
    else if(how==='native'){ if(navigator.share){ try{ await navigator.share({title:'Biên bản họp', text:l.message}); run('hop','da_gui',{token:l.token, how:'chia sẻ'},'',true).catch(()=>{}); }catch(e){} } else { copyText(l.message); toast('Đã chép tin nhắn, mở Zalo/Messenger và dán vào'); } }
    else if(how==='copy'){ copyText(l.message); }
    else toast('Đã tạo trang chia sẻ');
  }catch(e){ toast(e.message); }
}
function shEmail(){
  const out = $('#shOut');
  out.innerHTML = `<div class="card pad" style="margin-top:12px"><label class="field"><span>Gửi tới (nhiều email cách nhau dấu phẩy)</span><input type="email" id="shTo" multiple placeholder="lan@sellnity.com, minh@sellnity.com" autocomplete="email"></label>
    <label class="field"><span>CC</span><input type="email" id="shCc" multiple placeholder="không bắt buộc"></label>
    <div class="chips" style="padding-top:0;margin-bottom:12px"><button class="chip on" id="shGm" onclick="this.classList.add('on');$('#shLk').classList.remove('on')">Gmail</button><button class="chip" id="shLk" onclick="this.classList.add('on');$('#shGm').classList.remove('on')">Lark Mail</button></div>
    <button class="btn pri full" id="shSend" onclick="shEmailGo()">${ico('send',18)} Gửi email</button></div>`;
  setTimeout(()=>$('#shTo')?.focus(), 100);
}
async function shEmailGo(){
  const to = $('#shTo').value.trim(), h = S.sh; if(!to.includes('@')) return toast('Nhập email người nhận');
  const b = $('#shSend'); b.disabled = true; b.textContent = 'Đang gửi…';
  try{ const confirm = await shConfirm();
    const r = await run('hop','chia_se_ui',{mid:h.mid, channel:'email', to, cc:$('#shCc').value.trim(), parts:h.parts.join(','), days:h.days, note:h.note, platform:$('#shLk').classList.contains('on')?'lark':'gmail', confirm},'',true);
    toast(r.text.split('.')[0]); notifyH('success'); $('#shOut').innerHTML = `<div class="card pad" style="margin-top:12px">✓ ${esc(r.text)}</div>`; shLoadLinks(); }
  catch(e){ toast(e.message); b.disabled = false; b.textContent = 'Gửi email'; }
}
async function shLark(){
  const out = $('#shOut'); out.innerHTML = `<div class="card pad" style="margin-top:12px"><div class="skel" style="width:60%"></div><div class="skel"></div></div>`;
  try{ if(!S.sh.groups) S.sh.groups = (await run('hop','lark_nhom',{},'',true)).items||[];
    const g = S.sh.groups;
    out.innerHTML = g.length ? `<div class="card list" style="margin-top:12px">${g.map(c=>`<button onclick="shLarkGo('${esc(c.id)}','${esc(c.name).replace(/'/g,'&#39;')}')"><span class="thumb">${ico('lark',20)}</span><div class="grow"><div style="font-weight:600">${esc(c.name)}</div><div class="meta">Bấm để gửi biên bản vào nhóm này</div></div></button>`).join('')}</div>`
      : `<div class="card pad" style="margin-top:12px">Bot superHuy chưa ở nhóm Lark nào. Thêm bot vào nhóm trên Lark rồi thử lại.</div>`;
  }catch(e){ out.innerHTML = `<div class="card pad" style="margin-top:12px">${esc(e.message)}</div>`; }
}
function shLarkGo(id, name){
  $('#shOut').innerHTML = `<div class="card pad" style="margin-top:12px"><p style="margin:0 0 10px">Gửi biên bản vào nhóm <b>${esc(name)}</b>?</p><div class="row"><button class="btn grow" onclick="shLark()">Chọn nhóm khác</button><button class="btn pri grow" id="shLg" onclick="shLarkSend('${esc(id)}')">${ico('send',16)} Gửi</button></div></div>`;
}
async function shLarkSend(id){
  const h = S.sh, b = $('#shLg'); b.disabled = true;
  try{ const confirm = await shConfirm(); const r = await run('hop','chia_se_ui',{mid:h.mid, channel:'lark', chat_id:id, parts:h.parts.join(','), days:h.days, note:h.note, confirm},'',true); toast(r.text); notifyH('success'); $('#shOut').innerHTML = `<div class="card pad" style="margin-top:12px">✓ ${esc(r.text)}</div>`; shLoadLinks(); }
  catch(e){ toast(e.message); b.disabled = false; }
}
async function shLoadLinks(){ try{ S.sh.links = (await run('hop','chia_se_ds',{mid:S.sh.mid},'',true)).items||[]; const el = $('#shLinks'); if(el) el.innerHTML = shLinksHtml(); }catch(e){} }
function shLinksHtml(){
  const L = (S.sh?.links||[]); if(!L.length) return '';
  const name = p => (SHARE_PARTS.find(x=>x[0]===p)||[p,p])[1];
  return `<p class="lbl" style="margin-top:20px">Đã chia sẻ</p><div class="card list">${L.map(l=>`<div style="align-items:flex-start"><span class="thumb">${ico('link',18)}</span><div class="grow" style="min-width:0">
    <div style="font-weight:600">${l.active?'Đang mở':'Đã '+(l.revoked?'thu hồi':'hết hạn')} · ${l.views} lượt xem</div>
    <div class="meta">Tạo ${esc(l.created)}, hết hạn ${esc(l.expires)} · ${l.parts.map(name).join(', ')}</div>
    ${(l.sent||[]).length?`<div class="meta">Đã gửi: ${esc(l.sent.slice(-3).join('; '))}</div>`:''}
    ${l.active?`<div class="row" style="margin-top:8px;gap:8px"><button class="btn sm" onclick="copyText('${esc(l.url)}')">${ico('copy',15)} Chép</button><button class="btn sm" style="color:var(--danger)" onclick="shRevoke('${esc(l.token)}')">Thu hồi</button></div>`:''}</div></div>`).join('')}</div>`;
}
async function shRevoke(t){ try{ const r = await run('hop','thu_hoi',{token:t},'',true); toast(r.text.split(',')[0]); shLoadLinks(); }catch(e){ toast(e.message); } }

/* ---------- Second Brain: kho tri thức Obsidian (superHuy tra cứu khi trả lời) */
async function openBrain(){
  S.br = S.br || {}; S.br.q = ''; S.br.hits = null;
  sheet(`<h2>Second Brain</h2><div class="card pad"><div class="skel" style="width:60%"></div><div class="skel"></div></div>`);
  try{ S.br.d = await run('brain','tongquan',{},'',true); }catch(e){ S.br.d = {err:e.message}; }
  brPaint();
}
function brPaint(){
  const d = S.br.d||{}, st = d.stats||{}, sy = d.sync||{}, y = $('#sheet').scrollTop;
  const row = (n, sub, act) => `<button onclick="${act}"><span class="thumb">${ico('brain',18)}</span><div class="grow" style="min-width:0"><div style="font-weight:600" class="clamp2">${esc(n)}</div><div class="meta">${esc(sub)}</div></div></button>`;
  sheet(`<h2>Second Brain</h2><p class="lead">Kho Obsidian là bộ não thứ hai của anh. Trước khi trả lời, đề xuất hay biên tập họp, superHuy tra các ghi chú liên quan và nêu tên ghi chú đã dùng.</p>
    ${d.err?`<div class="card pad">${esc(d.err)}</div>`:`
    <div class="hstat brstat"><div><b>${st.notes||0}</b><span>ghi chú</span></div><div><b>${st.own||0}</b><span>anh tự viết</span></div><div><b>${st.external||0}</b><span>tài liệu nguồn ngoài</span></div><div><b>${(d.memory||0)+(d.memory_extra||0)}</b><span>điều superHuy nhớ</span></div></div>
    <div class="card pad" style="margin:12px 0"><div class="row" style="align-items:center;gap:10px"><span class="dot ${sy.enabled?'ok':''}"></span><div class="grow"><div style="font-weight:600">${sy.enabled?'Đồng bộ hai chiều với Obsidian trên Mac':'Chưa bật đồng bộ'}</div>
      <div class="meta">${sy.last_commit?'Lần đồng bộ gần nhất '+esc(sy.last_commit)+' · ':''}tự động mỗi 10 phút</div></div><button class="btn sm" id="brSync" onclick="brSync()">${ico('refresh',15)} Đồng bộ</button></div></div>`}
    ${(d.sources||[]).length?`<p class="lbl" style="margin-top:4px">Nguồn tri thức</p><div class="card list" id="brSrc">${d.sources.map(brSrcRow).join('')}</div><div id="brSrcOut"></div>`:''}
    <form class="askbar" style="margin-top:14px" onsubmit="event.preventDefault();brSearch($('#brQ').value)"><span class="ic">${ico('brain',18)}</span><input id="brQ" value="${esc(S.br.q||'')}" placeholder="Tìm trong Obsidian…" autocomplete="off"><button class="btn pri sm">Tìm</button></form>
    <div id="brHits">${brHitsHtml()}</div>
    ${(d.mac||[]).length?`<p class="lbl" style="margin-top:18px">Anh vừa viết trên Obsidian</p><div class="card list">${d.mac.map(n=>row(n.title, (n.folder||'Gốc')+' · '+n.when, `brOpen('${esc(n.path).replace(/'/g,'&#39;')}')`)).join('')}</div>`:''}
    ${(d.recent||[]).length?`<p class="lbl" style="margin-top:18px">Ghi chú mới nhất</p><div class="card list">${d.recent.slice(0,8).map(n=>row(n.title, n.folder, `brOpen('${esc(n.folder+'/'+n.title+'.md').replace(/'/g,'&#39;')}')`)).join('')}</div>`:''}
    <div class="card pad" style="margin-top:18px"><div style="font-weight:600;margin-bottom:4px">Dạy superHuy ngay trong Obsidian</div>
      <p class="meta" style="margin:0">Mở ghi chú <b>${esc((d.memory_note||'').replace(/\.md$/,''))}</b>, viết vào mục <b>Anh bổ sung</b> (mỗi ý một dòng). superHuy đọc mục này mỗi lần trả lời. Mọi ghi chú khác anh viết cũng được tra cứu tự động.</p>
      <p class="meta" style="margin:8px 0 0">Trong chat, nói “lưu lại vào second brain” để superHuy ghi kết luận vừa bàn thành ghi chú.</p></div>`);
  $('#sheet').scrollTop = y;
}
function brHitsHtml(){
  const h = S.br.hits; if(h===null || h===undefined) return '';
  if(!h.length) return `<div class="card empty" style="margin-top:10px">Không thấy ghi chú nào khớp.</div>`;
  return `<div class="card list" style="margin-top:10px">${h.map(x=>`<button onclick="brOpen('${esc(x.path).replace(/'/g,'&#39;')}')"><span class="thumb">${ico('brain',18)}</span><div class="grow" style="min-width:0"><div style="font-weight:600">${esc(x.title)}${x.head?` <span class="meta" style="margin:0">› ${esc(x.head)}</span>`:''}</div>
    <div class="meta clamp2">${esc(x.snippet)}</div><div class="meta">${x.own?'Anh viết':'superHuy lưu'} · sửa ${esc(x.updated)}</div></div></button>`).join('')}</div>`;
}
async function brSearch(q){ q = (q||'').trim(); if(!q) return; S.br.q = q; $('#brHits').innerHTML = `<div class="card pad" style="margin-top:10px"><div class="skel"></div></div>`;
  try{ S.br.hits = (await run('brain','tim',{query:q},'',true)).items||[]; }catch(e){ S.br.hits = []; toast(e.message); } $('#brHits').innerHTML = brHitsHtml(); }
async function brSync(){ const b = $('#brSync'); b.disabled = true; try{ const r = await run('brain','dongbo',{},'',true); toast(r.text.split('.')[0]); S.br.d = await run('brain','tongquan',{},'',true); brPaint(); }catch(e){ toast(e.message); b.disabled = false; } }
function mdLite(t){
  return esc(t).replace(/```[\s\S]*?```/g,'').split('\n').map(l=>{
    let m; if((m=l.match(/^(#{1,4})\s+(.*)/))) return `<h${Math.min(m[1].length+1,4)} style="margin:14px 0 6px">${m[2]}</h${Math.min(m[1].length+1,4)}>`;
    if((m=l.match(/^\s*[-*+]\s+(\[[ x]\]\s*)?(.*)/))) return `<div style="display:flex;gap:8px;margin:3px 0"><span style="color:var(--muted)">${m[1]?(m[1].includes('x')?'☑':'☐'):'•'}</span><span>${m[2]}</span></div>`;
    if(l.startsWith('&gt;')) return `<div style="border-left:3px solid var(--line);padding-left:10px;color:var(--muted)">${l.replace(/^&gt;\s?/,'')}</div>`;
    return l.trim() ? `<p style="margin:6px 0">${l}</p>` : '';
  }).join('').replace(/\[\[([^\]|]+)(\|[^\]]+)?\]\]/g,'<b style="color:var(--jade)">$1</b>').replace(/\*\*([^*]+)\*\*/g,'<b>$1</b>');
}
async function brOpen(path){
  try{ const n = await run('brain','doc',{path},'',true);
    sheet(`<button class="back" onclick="brPaint()">${ico('chev',18)} Second Brain</button><h2 style="margin-top:6px">${esc(n.title)}</h2><div class="meta">${esc(n.path)} · sửa ${esc(n.updated)}</div>
      <div class="notebody" style="margin-top:12px;font-size:15px;line-height:1.6">${mdLite(n.body)}</div>`); }
  catch(e){ toast(e.message); }
}

const SRC_IC = {obsidian:['brain','#8B5CF6'], gemini:['spark','#1A73E8']};
function brSrcRow(x){
  const [ic,c] = SRC_IC[x.id]||['link','#7A7387'];
  const act = x.id==='gemini' ? (x.connected
      ? `<button class="btn sm" onclick="brSrcSync('gemini')" ${x.syncing?'disabled':''}>${ico('refresh',15)} ${x.syncing?'Đang nạp':'Nạp lại'}</button>`
      : `<button class="btn pri sm" onclick="brGemConnect()">Kết nối</button>`) : '';
  return `<div style="align-items:center"><span class="thumb" style="color:${c}">${ico(ic,20)}</span><div class="grow" style="min-width:0">
    <div style="font-weight:600">${esc(x.name)} ${x.connected?'<span class="dot ok" style="display:inline-block;width:8px;height:8px;margin-left:4px"></span>':''}</div>
    <div class="meta">${esc(x.detail||'')}${x.last_sync?' · '+esc(x.last_sync):''}</div>
    ${x.last_error?`<div class="meta" style="color:var(--danger)">${esc(x.last_error)}</div>`:''}
    ${x.id==='gemini'&&x.connected?`<div class="row" style="gap:8px;margin-top:6px"><button class="addlink" onclick="brGemList()">Xem notebook</button><button class="addlink" onclick="brGemConnect()">Đăng nhập lại</button><button class="addlink" style="color:var(--danger)" onclick="brGemOff()">Ngắt</button></div>`:''}</div>${act}</div>`;
}
async function brGemConnect(){
  const out = $('#brSrcOut');
  try{ const r = await run('brain','gemini_ma',{},'',true);
    out.innerHTML = `<div class="card pad" style="margin-top:10px"><div style="font-weight:600;margin-bottom:6px">Kết nối Gemini Notebook</div>
      <ol class="meta" style="margin:0 0 10px;padding-left:18px;line-height:1.7"><li>Trên Mac, bấm đúp <b>Ket-noi-Gemini-Notebook.command</b> (thư mục agent-army › deploy).</li>
      <li>Chrome mở ra: anh đăng nhập đúng Gmail chứa các notebook.</li><li>Khi Terminal hỏi, dán mã dưới đây. Mã dùng 1 lần, hết hạn sau ${r.expires_min} phút.</li></ol>
      <div class="row" style="align-items:center;gap:10px"><div class="gemcode">${esc(r.code)}</div><button class="btn sm" onclick="copyText('${esc(r.code)}')">${ico('copy',15)} Chép mã</button></div>
      <p class="meta" style="margin:10px 0 0">superHuy chỉ đọc notebook để tham chiếu; phiên đăng nhập chỉ lưu trên máy chủ của anh. Google chưa có API chính thức nên superHuy dùng thư viện mã nguồn mở notebooklm-py.</p></div>`;
  }catch(e){ toast(e.message); }
}
async function brSrcSync(id){ try{ await run('brain','dongbo_nguon',{source:id},'Nạp lại '+(id==='gemini'?'Gemini Notebook':id)); toast('Đã nạp xong'); S.br.d = await run('brain','tongquan',{},'',true); brPaint(); }catch(e){ toast(e.message); } }
async function brGemList(){
  try{ const r = await run('brain','notebook_ds',{},'',true), out = $('#brSrcOut');
    out.innerHTML = `<div class="card list" style="margin-top:10px">${(r.items||[]).map(n=>`<button onclick="S.dockOpen=true;dock();$('#dIn').value='Hỏi notebook ${esc(n.title).replace(/'/g,'&#39;')}: ';$('#dIn').focus()"><span class="thumb">${esc(n.emoji)||ico('spark',18)}</span><div class="grow"><div style="font-weight:600">${esc(n.title)}</div><div class="meta">${n.sources} nguồn · ${n.notes} ghi chú · bấm để hỏi notebook này</div></div></button>`).join('')||'<div class="empty">Chưa nạp notebook nào.</div>'}</div>`;
  }catch(e){ toast(e.message); }
}
function brGemOff(){
  $('#brSrcOut').innerHTML = `<div class="card pad" style="margin-top:10px"><p style="margin:0 0 10px">Ngắt Gemini Notebook? superHuy xoá phiên đăng nhập trên máy chủ.</p>
    <div class="row"><button class="btn grow" onclick="brGemOffGo(true)">Ngắt, giữ dữ liệu đã nạp</button><button class="btn grow" style="color:var(--danger)" onclick="brGemOffGo(false)">Ngắt và xoá dữ liệu</button></div></div>`;
}
async function brGemOffGo(keep){ try{ const r = await run('brain','gemini_ngat',{keep_data:keep},'',true); toast(r.text); S.br.d = await run('brain','tongquan',{},'',true); brPaint(); }catch(e){ toast(e.message); } }
async function chatSave(i){
  const m = S.data.chat||[], a = m[i]; if(!a) return;
  const q = [...m.slice(0,i)].reverse().find(x=>x.role==='user')?.content||'';
  try{ const r = await run('brain','ghi',{title:(q||a.content).slice(0,80), content:(q?`Câu hỏi: ${q}\n\n`:'')+a.content, kind:'kien-thuc'},'',true); a.saved = true; toast('Đã lưu vào Obsidian'); if(S.tab==='chat') render(); }
  catch(e){ toast(e.message); }
}

/* ---------- bong bóng trợ lý: gọi superHuy ở mọi trang */
function dock(){
  let d = $('#dock');
  if(!d){ d = document.createElement('div'); d.id = 'dock'; document.body.appendChild(d); }
  const hide = S.tab==='chat' || !!S.mt.rec;
  if(hide){ d.innerHTML = ''; return; }
  if(!S.dockOpen){ d.innerHTML = ''; return; }
  const msgs = (S.data.chat||[]).slice(-12);
  d.innerHTML = `<div class="dpanel" role="dialog" aria-label="Trợ lý superHuy">
    <div class="dhead"><span class="dav">${ico('spark',16)}</span><b class="grow">superHuy</b>
      <button class="iconbtn sm" aria-label="Mở toàn màn hình" onclick="S.dockOpen=false;go('chat')">${ico('arrow',18)}</button>
      <button class="iconbtn sm" aria-label="Thu nhỏ" onclick="aiToggle(false)">${ico('x',18)}</button></div>
    <div class="dmsgs" id="dmsgs">${msgs.length ? msgs.map(x=>`<div class="msg ${x.role==='user'?'me':'bot'}">${esc(x.content)}</div>`).join('') : `<div class="meta" style="padding:4px">Hỏi nhanh hoặc nhờ việc ở bất kỳ trang nào. superHuy tự làm và báo lại.</div><div class="dsug">${['Hôm nay anh có những việc gì?','Lên lịch trình hôm nay giúp anh','Cuộc họp gần nhất đã chốt những gì?','Ghi chi 120k ăn trưa','Email nào cần anh trả lời?'].map(q=>`<button onclick="$('#dIn').value='${q}';dockAsk()">${q}</button>`).join('')}</div>`}
      ${S.chatWait?`<div class="msg bot typing"><span></span><span></span><span></span></div>`:''}</div>
    <form class="dform" onsubmit="event.preventDefault();dockAsk()"><input id="dIn" placeholder="Nhắn superHuy…" autocomplete="off"><button class="send" aria-label="Gửi">${ico('arrow',18)}</button></form></div>`;
  const ms = $('#dmsgs'); if(ms) ms.scrollTop = ms.scrollHeight;
}
function aiToggle(open){
  if(S.tab==='chat'){ go('home'); }
  S.dockOpen = open===undefined ? !S.dockOpen : open; haptic('medium'); nav(); dock();
  if(S.dockOpen) setTimeout(()=>$('#dIn')?.focus(), 160);
}
async function dockAsk(){
  const v = $('#dIn')?.value.trim(); if(!v || S.chatWait) return;
  S.data.chat = [...(S.data.chat||[]), {role:'user', content:v}]; S.chatWait = true; dock();
  try{ const j = await api('/api/chat', {text:v}); const r = await waitJob(j.job, 'superHuy đang làm', null, true);
    S.data.chat.push({role:'assistant', content:r.text, actions:r.actions||[]}); if((r.actions||[]).length){ S.tk.at = 0; S.fn.at = 0; S.gr.at = 0; S.mt.at = 0; } }
  catch(e){ S.data.chat.push({role:'assistant', content:'⚠️ '+e.message}); }
  S.chatWait = false; dock(); setTimeout(()=>$('#dIn')?.focus(), 50);
}

/* ---------- Trợ lý */
function vChat(){
  const m = S.data.chat||[];
  const sug = ['Lên lịch trình hôm nay giúp anh, tối ưu cho các mục tiêu','Sáng nay anh chạy 8km rồi, nay cân 86,4kg','Giao Linh báo cáo Q4 trước thứ 6','Cafe 45k, ăn trưa 120k','Tuần này anh nên tập gì để chuẩn bị cho VMM?','Email nào cần anh trả lời hôm nay?'];
  return `
  <div class="row" style="justify-content:space-between;align-items:flex-end"><div><div class="date">Siêu trợ lý điều phối mọi trợ lý</div><h1 style="margin-bottom:10px">superHuy</h1></div>
  ${m.length?`<button class="btn" onclick="resetChat()">Cuộc mới</button>`:''}</div>
  <div class="chat">
    ${m.length ? m.map((x,i)=>`<div class="msg ${x.role==='user'?'me':'bot'}">${esc(x.content)}</div>${x.role==='assistant'&&x.content.length>120&&!x.content.startsWith('⚠️')?`<button class="savebtn" onclick="chatSave(${i})" ${x.saved?'disabled':''}>${ico('brain',14)} ${x.saved?'Đã lưu vào Obsidian':'Lưu vào Second Brain'}</button>`:''}${(x.actions||[]).length?`<div class="acts">${x.actions.filter((a,i,arr)=>arr.findIndex(b=>b.label===a.label)===i).map(a=>`<span class="${a.ok?'':'err'}">${a.ok?'✓':'!'} ${esc(a.label.split(': ').pop())}</span>`).join('')}</div>`:''}`).join('') : `
      <div class="hello"><p>Nói như với một trợ lý riêng. superHuy tự làm: lên lịch trình ngày, tạo và giao việc, ghi thu chi, đánh dấu thói quen, ghi cân nặng, đọc email, Lark, lịch… và ghi nhớ để ngày càng hiểu anh.</p>
      <div class="sug">${sug.map(q=>`<button onclick="ask('${esc(q)}')">${esc(q)}</button>`).join('')}</div></div>`}
    ${S.chatWait?`<div class="msg bot typing" aria-label="Đang trả lời"><span></span><span></span><span></span></div>`:''}
  </div>
  <div class="composer"><form id="cf"><textarea id="msgIn" rows="1" placeholder="Nhắn cho superHuy…" aria-label="Tin nhắn"></textarea><button class="send" aria-label="Gửi">${ico('arrow',20)}</button></form></div>`;
}
function bindComposer(){
  const f = $('#cf'), t = $('#msgIn'); if(!f) return;
  t.oninput = () => { t.style.height='auto'; t.style.height = Math.min(t.scrollHeight,120)+'px'; };
  t.onkeydown = e => { if(e.key==='Enter' && !e.shiftKey && !('ontouchstart' in window)){ e.preventDefault(); f.requestSubmit(); } };
  f.onsubmit = e => { e.preventDefault(); const v=t.value.trim(); if(v) ask(v); };
}
async function ask(text){
  if(S.tab!=='chat'){ S.tab='chat'; }
  S.data.chat = [...(S.data.chat||[]), {role:'user', content:text}]; S.chatWait = true; render();
  try{
    const j = await api('/api/chat', {text});
    const r = await waitJob(j.job, 'superHuy đang làm', null);
    S.data.chat.push({role:'assistant', content:r.text, actions:r.actions||[]});
    if((r.actions||[]).length){ S.tk.at = 0; S.fn.at = 0; S.gr.at = 0; }
  }catch(e){ S.data.chat.push({role:'assistant', content:'⚠️ '+e.message}); }
  S.chatWait = false; if(S.tab==='chat') render();
  refresh().catch(()=>{});
}
async function resetChat(){ try{ await api('/api/chat/reset', {}); }catch(e){} S.data.chat=[]; render(); }

/* ---------- Studio */
function rowContent(c){
  const k = KIND[c.kind]||[c.kind,'save'];
  const st = c.status==='posted' ? '<span class="badge posted">Đã đăng</span>' : (c.posts||[]).length ? '<span class="badge shared">Đã chia sẻ</span>' : '<span class="badge draft">Nháp</span>';
  const th = c.image ? `<img class="thumb" src="${c.image}" alt="" loading="lazy">` : `<span class="thumb">${ico(k[1],20)}</span>`;
  return `<button onclick="openContent('${c.id}')">${th}<div class="grow"><div class="ttl2">${esc(c.title)}</div><div class="meta">${k[0]} lúc ${esc((c.created||'').slice(11,16))} ngày ${esc((c.created||'').slice(8,10))}/${esc((c.created||'').slice(5,7))}</div></div>${st}</button>`;
}
function vStudio(embed){
  const all = S.data.contents||[], list = all.filter(c=>!S.kind || c.kind===S.kind);
  const f = [['','Tất cả'],['post','Bài viết'],['bantin','Ảnh bản tin'],['video','Video']];
  return `
  ${embed?`<div class="sec"><h2>Thư viện</h2><span class="meta">${all.length} nội dung</span></div>`:`<div class="date">${all.length} nội dung do đội agent tạo</div><h1>Studio</h1>`}
  <div class="chips" style="padding-top:0;margin-bottom:12px">${f.map(([k,l])=>`<button class="chip ${S.kind===k?'on':''}" onclick="S.kind='${k}';render()">${l}</button>`).join('')}</div>
  ${list.length ? `<div class="grid">${list.map(c=>{
    const k = KIND[c.kind]||[c.kind,'save'];
    const st = c.status==='posted' ? '<span class="badge posted">Đã đăng</span>' : (c.posts||[]).length ? '<span class="badge shared">Đã chia sẻ</span>' : '<span class="badge draft">Nháp</span>';
    const pic = c.image ? `<img src="${c.image}" alt="" loading="lazy">` : c.video ? `<video src="${c.video}#t=1" muted playsinline preload="metadata"></video>` : `<span class="glyph">${ico(k[1],30)}</span>`;
    return `<button class="card tile" onclick="openContent('${c.id}')"><div class="pic">${pic}${c.video?`<span class="play"><span>${ico('play',18)}</span></span>`:''}${st}</div>
      <div class="info"><div class="ttl2" style="font-size:14px">${esc(c.title)}</div><div class="meta">${k[0]}</div></div></button>`;
  }).join('')}</div>` : `<div class="card empty">Chưa có nội dung loại này. Vào tab Tin và bấm “Viết bài” để bắt đầu.</div>`}`;
}

/* ---------- Nội dung: săn tin + duyệt quẹt + bộ nội dung (reels, group, fanpage) */
const TRK = {tin:'Theo chủ đề', founder:'Founder & startup AI', roimaxx:'Agentic · Roimaxx', leversphere:'AI-native · Leversphere', tay:'Anh gửi'};
const ITYPE = {tin:'Tin', case_study:'Case study', best_practice:'Best practice', tinh_nang:'Tính năng mới', y_tuong:'Ý tưởng', bao_cao:'Báo cáo'};
const CSTYLE = {auto:'Tự chọn', founder:'Kể chuyện founder', tin:'Tin nóng', bai_hoc:'3 bài học'};
const COUT = {reel:'Video reels', group:'Bài group', page:'Bài fanpage'};
const ago = iso => { if(!iso) return ''; const m = Math.max(0, (Date.now()-Date.parse(iso))/60000|0); return m<1?'vừa xong':m<60?`${m} phút trước`:m<1440?`${m/60|0} giờ trước`:`${m/1440|0} ngày trước`; };
const cq = () => S.data.cq || {new:[], working:[], done:[], cfg:{}, counts:{}};
function cqQueue(){ const f = S.ctrack||''; return cq().new.filter(n=>!f || n.track===f); }
function vContent(){
  const v = ['tao','cl','repo'].includes(S.cview) ? S.cview : 'duyet', q = cq();
  const busy = q.working.filter(w=>w.status!=='error').length;
  const head = `<div class="date">${q.new.length} tin chờ duyệt${busy?`, ${busy} bộ đang tạo`:''}</div>
    <div class="row" style="align-items:center;margin-bottom:14px"><h1 class="grow" style="margin:2px 0 0">Nội dung</h1>
      <button class="iconbtn" aria-label="Dán bài hoặc link" onclick="cPaste()">${ico('link',20)}</button>
      <button class="iconbtn" aria-label="Chủ đề và định dạng" onclick="cSettings()">${ico('gear',20)}</button></div>
    <div class="seg" style="margin-bottom:14px"><button class="${v==='duyet'?'on':''}" onclick="S.cview='duyet';render()">Duyệt tin</button><button class="${v==='cl'?'on':''}" onclick="S.cview='cl';render()">Chiến lược</button><button class="${v==='repo'?'on':''}" onclick="S.cview='repo';render()">Repo${S.rp?.new?.length?` ${S.rp.new.length}`:''}</button><button class="${v==='tao'?'on':''}" onclick="S.cview='tao';render()">Đã tạo ${q.done.length||''}</button></div>`;
  if(v==='cl') return head + vStrategy();
  if(v==='repo') return head + vRepo();
  const work = `<div id="cwork" style="margin-top:${v==='duyet'?18:0}px">${cWorkHtml()}</div>`;
  return head + (v==='duyet' ? cSwipeHtml() + work : work + cDoneHtml());
}
function cWorkHtml(){
  const w = cq().working; if(!w.length) return '';
  return `<div class="card list" style="margin-bottom:14px">${w.map(i=>`<div class="wk">${i.status==='error'?`<span class="thumb" style="color:var(--danger)">${ico('x',20)}</span>`:'<div class="spin"></div>'}
    <div class="grow"><div class="ttl2">${esc(i.headline_vi)}</div><div class="meta">${i.status==='error'?esc('Lỗi: '+(i.err||'')):i.status==='working'?esc(i.step||'Đang viết kịch bản, dựng video và bài đăng…'):'Đang xếp hàng'}</div>${i.status==='working'?`<div class="pbar" style="margin-top:6px"><i style="width:${i.pct||3}%"></i></div>`:''}</div>
    ${i.status==='error'?`<button class="btn sm" onclick="cApprove('${i.id}')">Thử lại</button>`:''}</div>`).join('')}</div>`;
}
function cSwipeHtml(){
  const q = cq(), c = q.counts||{}, f = S.ctrack||'', list = cqQueue();
  const chips = `<div class="chips" style="padding-top:0;margin-bottom:10px"><button class="chip ${!f?'on':''}" onclick="S.ctrack='';render()">Tất cả ${q.new.length}</button>${Object.keys(TRK).filter(k=>c[k]).map(k=>`<button class="chip ${f===k?'on':''}" onclick="S.ctrack='${k}';render()">${TRK[k]} ${c[k]}</button>`).join('')}</div>`;
  if(!list.length) return chips + `<div class="done"><b>Đã duyệt hết tin</b>superHuy tự săn tin lúc 7h10 và 15h10. Muốn có ngay thì bấm săn tin, hoặc dán một bài anh thấy hay.
    <div class="row" style="justify-content:center;margin-top:16px"><button class="btn pri" onclick="cScan()">${ico('refresh')} Săn tin ngay</button><button class="btn" onclick="cPaste()">${ico('link')} Dán bài</button></div></div>`;
  const top = list.slice(0,3).reverse();
  return chips + `<div class="stack" id="cstack">${top.map((n,i)=>{ const depth = top.length-1-i;
    return `<article class="card mcard ccard ${depth===1?'back1':depth===2?'back2':''}" data-id="${n.id}">
      ${depth===0?'<span class="stamp yes">Tạo reels</span><span class="stamp no">Bỏ qua</span>':''}
      <div class="row" style="gap:6px;align-items:center"><span class="trk ${n.track}">${esc(TRK[n.track]||n.track)}</span><span class="topic">${esc(n.topic)}</span><span class="grow"></span><span class="meta" style="margin:0">${esc(ago(n.published||n.at))}</span></div>
      <h3>${esc(n.headline_vi)}</h3>
      <p class="sum">${esc(n.summary_vi)}</p>
      ${n.cao?`<div class="caobox"><div class="row" style="gap:6px;align-items:center;margin-bottom:4px"><b>Góc nhìn CAO</b><span class="itype">${esc(ITYPE[n.cao.loai]||'Tin')}</span><span class="grow"></span>${rel(n.cao)}</div><p>${esc((n.cao.phan_tich||[])[0]||n.cao.dieu_moi||'')}</p></div>`
        : n.why_hot?`<div class="aisug">${ico('spark',15)}<span>${esc(n.why_hot)}</span></div>`:''}
      <div class="row" style="margin-top:auto;align-items:center"><span class="meta grow" style="margin:0">${esc(src(n.source))}</span><button class="btn sm" onpointerdown="event.stopPropagation()" onclick="event.stopPropagation();cCao('${n.id}')">${ico('spark',16)} ${n.cao?'Phân tích':'Phân tích CAO'}</button>${n.url?`<button class="btn sm" onpointerdown="event.stopPropagation()" onclick="event.stopPropagation();openLink('${esc(n.url)}')">${ico('link',16)} Bài gốc</button>`:''}</div>
    </article>`; }).join('')}</div>
    <div class="swipebar"><button class="round" aria-label="Bỏ qua" onclick="cSwipe(-1)">${ico('x')}</button>
      <button class="iconbtn" aria-label="Tuỳ chỉnh rồi tạo" onclick="cCustom()">${ico('pen',20)}</button>
      <button class="round yes" aria-label="Tạo reels" onclick="cSwipe(1)">${ico('film')}</button></div>
    <p class="muted small" style="text-align:center;margin:10px 0 0">Quẹt phải để tạo video bản tin và bài đăng, quẹt trái để bỏ qua. Nút bút để chọn kiểu, độ dài.</p>
    ${rptBox(list[0])}`;
}
function cDoneHtml(){
  const d = cq().done, all = S.data.contents||[];
  const byId = Object.fromEntries(all.map(c=>[c.id,c]));
  const packs = d.length ? `<div class="card list" style="margin-bottom:6px">${d.map(i=>{ const ids = i.pack?.ids||{}, r = byId[ids.reel], th = i.pack?.image;
    return `<button onclick="cPack('${i.id}')">${th?`<img class="thumb" src="${th}" alt="" loading="lazy">`:`<span class="thumb">${ico('film',20)}</span>`}
      <div class="grow"><div class="ttl2">${esc(i.headline_vi)}</div><div class="meta">${Object.keys(ids).map(k=>COUT[k]).join(', ')} · ${esc(ago(i.done_at))}</div></div>
      ${r?.status==='posted'?'<span class="badge posted">Đã đăng</span>':'<span class="badge draft">Chưa đăng</span>'}</button>`; }).join('')}</div>`
    : `<div class="card empty">Chưa có bộ nội dung nào. Quẹt phải một tin ở “Duyệt tin” để superHuy tạo reels và bài đăng.</div>`;
  return `<div class="sec" style="margin-top:4px"><h2>Bộ nội dung</h2></div>` + packs + vStudio(true);
}
function contentEnter(){ bindCSwipe(); cPoll(); }
function bindCSwipe(){
  const card = document.querySelector('.ccard:not(.back1):not(.back2)'); if(!card) return;
  let x0=null, dx=0;
  const yes = card.querySelector('.stamp.yes'), no = card.querySelector('.stamp.no');
  card.onpointerdown = e => { x0 = e.clientX; dx = 0; card.setPointerCapture(e.pointerId); card.style.transition='none'; };
  card.onpointermove = e => { if(x0===null) return; dx = e.clientX - x0; card.style.transform = `translateX(${dx}px) rotate(${dx/18}deg)`; yes.style.opacity = Math.max(0, dx/110); no.style.opacity = Math.max(0, -dx/110); };
  card.onpointerup = card.onpointercancel = () => { if(x0===null) return; x0=null; card.style.transition='transform .25s ease';
    if(Math.abs(dx) > 110) cSwipe(dx>0?1:-1); else { card.style.transform=''; yes.style.opacity=0; no.style.opacity=0; } };
}
function cSwipe(dir, opts){
  const card = document.querySelector('.ccard:not(.back1):not(.back2)'); if(!card) return;
  const id = card.dataset.id;
  haptic(dir>0?'medium':'light');
  card.style.transition='transform .28s ease, opacity .28s'; card.style.transform=`translateX(${dir*480}px) rotate(${dir*18}deg)`; card.style.opacity=0;
  if(card.dataset.kind==='repo') return setTimeout(()=> dir>0 ? rpApply(id) : rpSkip(id), 220);
  setTimeout(()=> dir>0 ? cApprove(id, opts) : cSkip(id), 220);
}
function cMove(id, status){
  const q = cq(), i = q.new.findIndex(n=>n.id===id); if(i<0) return null;
  const it = q.new.splice(i,1)[0]; q.counts[it.track] = Math.max(0,(q.counts[it.track]||1)-1);
  if(status){ it.status = status; q.working.push(it); }
  return it;
}
async function cSkip(id){
  const it = cMove(id); render();
  try{ await run('noidung','boqua',{iid:id},'',true); }catch(e){ toast(e.message); }
  if(it) toastUndo('Đã bỏ qua', ()=>run('noidung','hoantac',{iid:id},'',true).then(cReload));
}
async function cApprove(id, opts={}){
  const q = cq(); let it = cMove(id, 'queued');
  if(!it){ const w = q.working.find(x=>x.id===id); if(w){ w.status='queued'; w.err=''; } }
  closeSheet(); render();
  try{ const r = await run('noidung','duyet',{id, ...opts},'',true); toast(r.text||'Đã duyệt', 3200); cPoll(true); }
  catch(e){ toast(e.message); cReload(); }
}
function toastUndo(m, fn){
  const t=$('#toast'); t.innerHTML = `${esc(m)} <button class="link" style="color:var(--jade);font-weight:700;margin-left:10px">Hoàn tác</button>`;
  t.style.display='block'; t.querySelector('button').onclick = ()=>{ t.style.display='none'; fn(); };
  clearTimeout(t._h); t._h=setTimeout(()=>t.style.display='none', 4000);
}
async function cReload(){ try{ S.data.cq = await run('noidung','tongquan',{},'',true); if(S.tab==='content' && !$('#sheet').classList.contains('on')) render(); }catch(e){} }
function cPoll(now){
  clearTimeout(S.cqTimer);
  const pending = () => cq().working.some(w=>w.status==='queued'||w.status==='working');
  if(!pending() && !now) return;
  S.cqTimer = setTimeout(async ()=>{
    const before = new Set(cq().done.map(d=>d.id));
    try{ S.data.cq = await run('noidung','tongquan',{},'',true); }catch(e){ return; }
    const fresh = cq().done.filter(d=>!before.has(d.id));
    if(fresh.length){ notifyH('success'); toast(`Đã tạo xong: ${fresh[0].headline_vi}`, 3500); try{ await refresh(); }catch(e){} return cPoll(); }
    const w = $('#cwork'); if(w && S.tab==='content') w.innerHTML = cWorkHtml();
    if(S.tab==='home' || S.tab==='content') cPoll();
  }, now ? 2500 : 8000);
}
async function cScan(){
  toast('superHuy đang săn tin theo chủ đề và case founder AI, khoảng 1 phút', 3500);
  try{ const r = await run('noidung','quet',{},'Săn tin'); await cReload(); toast(r.text, 4000); if(S.tab!=='content') refresh(); }catch(e){ toast(e.message); }
}
function cCustom(){
  const card = document.querySelector('.ccard:not(.back1):not(.back2)'); if(!card) return;
  const n = cq().new.find(x=>x.id===card.dataset.id), c = cq().cfg||{};
  S.copt = {style: c.style||'auto', reel_len: c.reel_len||60, outputs: [...(c.outputs||['reel','group','page'])]};
  const paint = () => sheet(`<h2>Tạo nội dung từ tin này</h2><p class="lead">${esc(n.headline_vi)}</p>
    <p class="lbl">Kiểu triển khai</p><div class="chips" style="padding-top:0;flex-wrap:wrap;margin-bottom:12px">${Object.entries(CSTYLE).map(([k,l])=>`<button class="chip ${S.copt.style===k?'on':''}" onclick="S.copt.style='${k}';S.cpaint()">${l}</button>`).join('')}</div>
    <p class="lbl">Độ dài video</p><div class="seg" style="margin-bottom:12px">${[30,45,60,90].map(x=>`<button class="${S.copt.reel_len===x?'on':''}" onclick="S.copt.reel_len=${x};S.cpaint()">${x} giây</button>`).join('')}</div>
    <p class="lbl">Tạo gì</p><div class="chips" style="padding-top:0;flex-wrap:wrap;margin-bottom:12px">${Object.entries(COUT).map(([k,l])=>`<button class="chip ${S.copt.outputs.includes(k)?'on':''}" onclick="S.copt.outputs=S.copt.outputs.includes('${k}')?S.copt.outputs.filter(o=>o!=='${k}'):[...S.copt.outputs,'${k}'];S.cpaint()">${l}</button>`).join('')}</div>
    <label class="field"><span>Chỉ đạo thêm (không bắt buộc)</span><textarea id="cangle" placeholder="Ví dụ: nhấn mạnh bài học cho founder POD muốn chuyển sang AI-native">${esc(S.copt.angle||'')}</textarea></label>
    <button class="btn pri full" onclick="S.copt.angle=$('#cangle').value;if(!S.copt.outputs.length)return toast('Chọn ít nhất một đầu ra');cSwipe(1,{style:S.copt.style,reel_len:S.copt.reel_len,outputs:S.copt.outputs.join(','),angle:S.copt.angle});closeSheet()">${ico('film')} Duyệt và tạo</button>`);
  S.cpaint = () => { const a = $('#cangle'); if(a) S.copt.angle = a.value; const y = $('#sheet').scrollTop; paint(); $('#sheet').scrollTop = y; };
  paint();
}
function cPaste(){
  sheet(`<h2>Dán bài hoặc link</h2><p class="lead">Bài báo, bài trong group Facebook, câu chuyện founder anh thấy hay. Với Facebook, anh sao chép phần chữ của bài rồi dán vào đây (Facebook cần đăng nhập nên superHuy không tự đọc được link).</p>
    <label class="field"><span>Link (không bắt buộc)</span><input id="purl" type="url" placeholder="https://"></label>
    <label class="field"><span>Nội dung bài</span><textarea id="ptext" style="min-height:180px" placeholder="Dán nội dung bài vào đây"></textarea></label>
    <label class="pick"><input type="checkbox" id="pnow" checked><div class="grow"><div style="font-weight:600">Tạo reels và bài đăng ngay</div><div class="meta">Bỏ chọn để chỉ thêm vào hàng chờ duyệt</div></div></label>
    <button class="btn pri full" id="pgo" style="margin-top:6px">Gửi cho superHuy</button>`);
  $('#pgo').onclick = async ()=>{
    const text = $('#ptext').value.trim(), url = $('#purl').value.trim();
    if(!text && !url) return toast('Dán nội dung hoặc link trước đã');
    $('#pgo').disabled = true; $('#pgo').textContent = 'superHuy đang đọc bài…';
    try{ const r = await run('noidung','them',{text, url, make_now: $('#pnow').checked},'Đọc bài anh gửi'); closeSheet(); toast(r.text, 4000); await cReload(); cPoll(true); }
    catch(e){ toast(e.message, 5000); $('#pgo').disabled = false; $('#pgo').textContent = 'Gửi cho superHuy'; }
  };
}

/* ---------- Phóng viên công nghệ superHuy: hỏi đào sâu từng bài */
const RPT_Q = ['Bối cảnh và ai đứng sau chuyện này?','Số liệu nào đáng chú ý, có đáng tin không?','Đối thủ và thị trường đang phản ứng ra sao?','Áp dụng gì cho Leversphere?','Cơ hội nào cho Roimaxx?','Ý tưởng nội dung từ bài này'];
function rptBox(n){
  if(!n) return '';
  return `<div class="rptbox" data-id="${n.id}"><div class="row" style="align-items:center;gap:8px;margin-bottom:8px"><span class="rptav">${ico('chat',15)}</span><b class="grow" style="font-size:14.5px">Hỏi phóng viên superHuy về bài này</b>${n.chat_n?`<button class="link" onclick="rptOpen('${n.id}')">${n.chat_n} câu đã hỏi</button>`:''}</div>
    <div class="chips" style="padding-top:0;margin-bottom:8px">${RPT_Q.slice(0,4).map(q=>`<button class="chip" onclick="rptAsk('${n.id}','${q}')">${q}</button>`).join('')}</div>
    <form class="rptform" onsubmit="event.preventDefault();rptAsk('${n.id}',$('#rptIn').value)"><input id="rptIn" placeholder="Đào sâu: ai, vì sao, số liệu, áp dụng cho anh…" autocomplete="off" enterkeyhint="send"><button class="send" aria-label="Hỏi">${ico('arrow',18)}</button></form></div>`;
}
function rptPaint(){
  const r = S.rpt; if(!r) return;
  const msgs = r.chat||[], last = [...msgs].reverse().find(m=>m.role==='assistant');
  const y = $('#sheet').classList.contains('on') ? $('#sheet').scrollTop : 0;
  sheet(`<div class="row" style="align-items:center;gap:8px;margin-bottom:4px"><span class="rptav">${ico('chat',15)}</span><span class="meta" style="margin:0">Phóng viên superHuy · ${esc(src(r.source||''))}</span></div>
    <h2 style="margin-bottom:12px">${esc(r.headline||'')}</h2>
    <div class="rptthread">${msgs.map((m,i)=>m.role==='user'?`<div class="rq">${esc(m.content)}</div>`
      :`<div class="ra"><div class="mdbody">${mdRender(m.content)}</div>
        ${(m.sources||[]).length?`<div class="rsrc">${m.sources.map(x=>`<button onclick="openLink('${esc(x.url)}')">${ico('link',13)} ${esc(x.source||'')}: ${esc((x.title||'').slice(0,70))}</button>`).join('')}</div>`:''}
        <div class="row" style="gap:8px;margin-top:8px"><button class="btn sm" onclick="rptSave(${i})">${ico('brain',14)} Lưu vào Second Brain</button><button class="btn sm" onclick="copyText(S.rpt.chat[${i}].content)">${ico('copy',14)} Chép</button></div></div>`).join('')}
      ${r.wait?`<div class="ra"><div class="msg bot typing"><span></span><span></span><span></span></div><p class="meta" style="margin:6px 0 0">Đang đọc bài, tìm tin liên quan và phân tích…</p></div>`:''}</div>
    ${!r.wait?`<div class="chips" style="padding-top:4px;flex-wrap:wrap;margin:10px 0">${((last&&last.followups&&last.followups.length)?last.followups:RPT_Q).map(q=>`<button class="chip" onclick="rptAsk('${r.id}',this.textContent)">${esc(q)}</button>`).join('')}</div>`:''}
    <form class="rptform" style="position:sticky;bottom:0" onsubmit="event.preventDefault();rptAsk('${r.id}',$('#rptIn2').value)"><input id="rptIn2" placeholder="Hỏi tiếp phóng viên…" autocomplete="off" enterkeyhint="send" ${r.wait?'disabled':''}><button class="send" aria-label="Hỏi" ${r.wait?'disabled':''}>${ico('arrow',18)}</button></form>
    ${r.status==='new'?`<button class="btn full" style="margin-top:10px" onclick="closeSheet();cCustomFor('${r.id}')">${ico('film',16)} Làm bản tin video theo góc vừa đào sâu</button>`:''}`);
  const sh = $('#sheet'); sh.scrollTop = r.wait || r.jump ? sh.scrollHeight : y; r.jump = false;
}
async function rptOpen(id){
  S.rpt = {id, chat:[], wait:false}; rptPaint();
  try{ Object.assign(S.rpt, await run('noidung','hoi_bai_ds',{iid:id},'',true)); S.rpt.jump = true; rptPaint(); }catch(e){ toast(e.message); }
}
async function rptAsk(id, q){
  q = (q||'').trim(); if(!q) return toast('Anh nhập câu hỏi trước nhé');
  if(!S.rpt || S.rpt.id!==id){ S.rpt = {id, chat:[], wait:false}; try{ Object.assign(S.rpt, await run('noidung','hoi_bai_ds',{iid:id},'',true)); }catch(e){} }
  if(S.rpt.wait) return;
  S.rpt.chat = [...(S.rpt.chat||[]), {role:'user', content:q}]; S.rpt.wait = true; rptPaint(); haptic('light');
  try{ const r = await run('noidung','hoi_bai',{iid:id, question:q},'',true); S.rpt.chat = r.chat; const n = cq().new.find(x=>x.id===id); if(n) n.chat_n = r.chat.filter(m=>m.role==='user').length; }
  catch(e){ S.rpt.chat.push({role:'assistant', content:'⚠️ '+e.message}); }
  S.rpt.wait = false; S.rpt.jump = true; if($('#sheet').classList.contains('on')) rptPaint();
}
async function rptSave(i){ try{ const r = await run('noidung','hoi_bai_luu',{iid:S.rpt.id, idx:i},'',true); toast(r.text+': '+r.path, 3500); notifyH('success'); }catch(e){ toast(e.message); } }
function cCustomFor(id){
  const q = cq(), i = q.new.findIndex(n=>n.id===id); if(i<0) return;
  const last = [...(S.rpt?.chat||[])].reverse().find(m=>m.role==='user');
  q.new.unshift(q.new.splice(i,1)[0]); render();
  setTimeout(()=>{ cCustom(); S.copt.angle = last ? `Khai thác theo góc: ${last.content}` : ''; S.cpaint(); }, 200);
}
/* ---------- Chiến lược: phân tích CAO, tài liệu sống Roimaxx / Leversphere */
const rel = c => { const r = c?.roimaxx?.lien_quan||0, l = c?.leversphere?.lien_quan||0; return `<span class="relpill" title="Mức liên quan">R ${r} · L ${l}</span>`; };
function caoHtml(c, head){
  if(!c) return '';
  const bl = xs => (xs||[]).filter(Boolean).map(x=>`<li>${esc(x)}</li>`).join('');
  const rx = c.roimaxx||{}, lv = c.leversphere||{};
  return `${head||''}
    <div class="row" style="gap:6px;align-items:center;margin:0 0 10px"><span class="itype">${esc(ITYPE[c.loai]||'Tin')}</span><span class="meta" style="margin:0">Độ tin cậy: ${esc(c.do_tin_cay||'')}</span></div>
    <p class="lead" style="margin:0 0 12px">${esc(c.tom_tat||'')}</p>
    ${c.dieu_moi?`<div class="mblk opn"><h3>${ico('spark',16)} Điều mới</h3><p style="margin:0">${esc(c.dieu_moi)}</p></div>`:''}
    <div class="mblk sgt"><h3>${ico('brain',16)} Phân tích CAO</h3><ul>${bl(c.phan_tich)}</ul></div>
    <div class="mblk dec"><h3>Roimaxx <span class="meta" style="margin:0 0 0 6px">liên quan ${rx.lien_quan??'?'}/10</span></h3><p style="margin:0 0 6px">${esc(rx.y_nghia||'')}</p><ul>${bl(rx.goi_y)}</ul></div>
    <div class="mblk nxt"><h3>Leversphere <span class="meta" style="margin:0 0 0 6px">liên quan ${lv.lien_quan??'?'}/10</span></h3><p style="margin:0 0 6px">${esc(lv.y_nghia||'')}</p><ul>${bl(lv.ung_dung)}</ul>${lv.kpi?`<div class="meta">KPI: ${esc(lv.kpi)}</div>`:''}</div>
    ${(c.hanh_dong||[]).length?`<div class="sec" style="margin-top:6px"><h2 style="font-size:17px">Hành động</h2></div><div class="card list">${c.hanh_dong.map((a,i)=>`<div style="align-items:center"><div class="grow"><div style="font-weight:600">${esc(a.viec||'')}</div><div class="meta">${esc([a.ai,a.khi].filter(Boolean).join(' · '))}</div></div><button class="btn sm" onclick="clTask(${i})">${ico('plus',14)} Tạo việc</button></div>`).join('')}</div>`:''}
    ${(c.rui_ro||[]).length?`<details style="margin:12px 0"><summary>Rủi ro cần lưu ý</summary><ul>${bl(c.rui_ro)}</ul></details>`:''}
    ${c.cau_hoi?`<div class="note" style="margin:12px 0">${esc(c.cau_hoi)}</div>`:''}`;
}
async function cCao(id){
  const n = cq().new.find(x=>x.id===id) || cq().done.find(x=>x.id===id); if(!n) return;
  let c = n.cao;
  if(!c){ sheet(`<h2>Phân tích CAO</h2><div class="card pad"><div class="spin"></div><p class="meta">superHuy đang đọc bài và phân tích theo 2 lăng kính Roimaxx và Leversphere…</p></div>`);
    try{ const r = await run('noidung','phan_tich',{iid:id},'',true); c = n.cao = r.cao; }catch(e){ closeSheet(); return toast(e.message); } }
  S.clCur = {cao:c, title:n.headline_vi, url:n.url, item:n.id};
  sheet(caoHtml(c, `<div class="meta" style="margin-bottom:4px">${esc(TRK[n.track]||'')} · ${esc(src(n.source))}</div><h2 style="margin-bottom:10px">${esc(n.headline_vi)}</h2>`) +
    `<div class="row" style="margin-top:6px">${n.url?`<button class="btn grow" onclick="openLink('${esc(n.url)}')">${ico('link',16)} Bài gốc</button>`:''}<button class="btn grow" onclick="rptOpen('${n.id}')">${ico('chat',16)} Hỏi phóng viên</button>${n.status==='new'?`<button class="btn pri grow" onclick="closeSheet();cApprove('${n.id}')">${ico('film',16)} Làm bản tin video</button>`:''}</div>`);
}
async function clTask(i){
  const a = (S.clCur?.cao?.hanh_dong||[])[i]; if(!a) return;
  try{ await run('viec','tao',{title:a.viec, notes:`Từ phân tích CAO: ${S.clCur.title}${S.clCur.url?' — '+S.clCur.url:''}`, labels:'Chiến lược'},'Tạo việc'); toast('Đã tạo việc'); S.tk && (S.tk.at = 0); }catch(e){ toast(e.message); }
}
/* ---------- Repo tham khảo: repo GitHub nổi bật mỗi tuần -> áp dụng cho superHuy */
const RPK_ICO = {nguon:'refresh', kien_thuc:'brain', quy_tac:'check', nang_cap:'code'};
const kfmt = n => n>=1000 ? (n/1000).toFixed(n>=10000?0:1).replace('.0','')+'k' : String(n||0);
async function rpLoad(){ try{ S.rp = await run('noidung','repo_ds',{},'',true); }catch(e){ S.rp = {new:[],applied:[],tickets:[],rules:[],watch:[],kinds:{},verdict:{},benefits:{},status:{}}; toast(e.message); }
  if(S.tab==='content' && S.cview==='repo' && !$('#sheet').classList.contains('on')) render(); }
function vRepo(){
  const d = S.rp;
  if(!d){ rpLoad(); return `<div class="card pad"><div class="skel" style="width:60%"></div><div class="skel"></div><div class="skel" style="width:40%"></div></div>`; }
  const sv = S.rpView||'swipe', open = d.open_tickets||0;
  const seg = `<div class="chips" style="padding-top:0;margin-bottom:10px"><button class="chip ${sv==='swipe'?'on':''}" onclick="S.rpView='swipe';render()">Tuần này ${d.new.length}</button><button class="chip ${sv==='up'?'on':''}" onclick="S.rpView='up';render()">Nâng cấp${open?` ${open}`:''}</button><button class="chip ${sv==='done'?'on':''}" onclick="S.rpView='done';render()">Đã áp dụng ${d.applied.length}</button></div>`;
  if(sv==='up') return seg + rpUpHtml();
  if(sv==='done') return seg + rpDoneHtml();
  return seg + rpSwipeHtml();
}
function rpSwipeHtml(){
  const d = S.rp, list = d.new;
  if(!list.length) return `<div class="done"><b>${d.scanning?'superHuy đang săn repo…':'Đã duyệt hết repo tuần này'}</b>Mỗi thứ Hai superHuy săn repo GitHub nổi bật, phân tích và đề xuất cách nâng cấp superHuy. Anh cũng có thể dán link một repo.
    <div class="row" style="justify-content:center;margin-top:16px"><button class="btn pri" onclick="rpScan()">${ico('refresh')} Săn repo ngay</button><button class="btn" onclick="rpAdd()">${ico('link')} Dán repo</button></div></div>`;
  const top = list.slice(0,3).reverse();
  return `<div class="stack rpstack" id="cstack">${top.map((n,i)=>{ const depth = top.length-1-i, a = n.a||{};
    return `<article class="card mcard ccard rpcard ${depth===1?'back1':depth===2?'back2':''}" data-id="${n.id}" data-kind="repo">
      ${depth===0?'<span class="stamp yes">Áp dụng</span><span class="stamp no">Bỏ qua</span>':''}
      <div class="row" style="gap:6px;align-items:center;flex-wrap:wrap"><span class="vd ${a.ket_luan}">${esc(d.verdict[a.ket_luan]||'')}</span><span class="fit">Phù hợp ${a.phu_hop??'?'}/10</span><span class="grow"></span><span class="meta stars" style="margin:0">${ico('star',13)}${kfmt(n.stars)}${n.stars_week?` · +${kfmt(n.stars_week)} tuần`:''}</span></div>
      <div><h3>${esc(a.ten_vi||n.full_name)}</h3><div class="meta rpname">${esc(n.full_name)}${n.lang?` · ${esc(n.lang)}`:''}${n.license?` · ${esc(n.license)}`:''}</div></div>
      <p class="sum rpsum">${esc(a.nhan_dinh||a.la_gi||n.desc)}</p>
      <div class="rpprops">${(a.de_xuat||[]).slice(0,3).map(p=>`<div class="rpprop ${p.loai}">${ico(RPK_ICO[p.loai]||'spark',15)}<span class="grow">${esc(p.tieu_de)}</span><span class="pk">${p.loai==='nang_cap'?'Phiếu':'Làm ngay'}</span></div>`).join('')}</div>
      <div class="row" style="margin-top:auto;align-items:center"><span class="meta grow" style="margin:0">${esc(n.via||'')}</span><button class="btn sm" onpointerdown="event.stopPropagation()" onclick="event.stopPropagation();rpOpen('${n.id}')">${ico('spark',16)} Chi tiết</button><button class="btn sm" onpointerdown="event.stopPropagation()" onclick="event.stopPropagation();openLink('${esc(n.url)}')">${ico('code',16)} GitHub</button></div>
    </article>`; }).join('')}</div>
    <div class="swipebar"><button class="round" aria-label="Bỏ qua" onclick="cSwipe(-1)">${ico('x')}</button>
      <button class="iconbtn" aria-label="Dán repo" onclick="rpAdd()">${ico('link',20)}</button>
      <button class="round yes" aria-label="Áp dụng cho superHuy" onclick="cSwipe(1)">${ico('check')}</button></div>
    <p class="muted small" style="text-align:center;margin:10px 0 0">Quẹt phải để áp dụng cho superHuy: việc an toàn làm ngay, việc đụng tới code thành phiếu nâng cấp có kế hoạch và kiểm thử trước khi triển khai.</p>`;
}
function rpMove(id, status){
  const d = S.rp, i = d.new.findIndex(n=>n.id===id); if(i<0) return null;
  const it = d.new.splice(i,1)[0]; if(status){ it.status = status; d.applied.unshift(it); } return it;
}
async function rpSkip(id){
  rpMove(id); render();
  try{ await run('noidung','repo_bo',{rid:id},'',true); }catch(e){ toast(e.message); }
  toastUndo('Đã bỏ qua repo', ()=>run('noidung','repo_hoantac',{rid:id},'',true).then(()=>{ S.rp=null; render(); }));
}
async function rpApply(id, picks=''){
  const it = rpMove(id, 'applied') || S.rp.applied.find(x=>x.id===id); closeSheet(); render();
  toast(`Đang áp dụng ${it?.a?.ten_vi||'repo'} cho superHuy…`, 3000);
  try{ const r = await run('noidung','repo_apdung',{rid:id, picks},'',true); notifyH('success'); toast(r.text||'Đã áp dụng', 4000); S.rp = null; rpLoad(); }
  catch(e){ toast(e.message); S.rp = null; rpLoad(); }
}
async function rpOpen(id){
  let n; try{ n = await run('noidung','repo_xem',{rid:id},'',true); }catch(e){ return toast(e.message); }
  const a = n.a||{}, d = S.rp||{verdict:{},benefits:{},kinds:{},status:{}}; S.rpCur = n;
  const props = (a.de_xuat||[]).map((p,i)=>`<label class="rpopt ${p.loai}"><input type="checkbox" ${n.status==='new'?'checked':'disabled'} data-i="${i}">
    <div class="grow"><div class="row" style="gap:6px;align-items:center;margin-bottom:3px"><span class="itype">${ico(RPK_ICO[p.loai]||'spark',13)} ${esc(d.kinds[p.loai]||p.loai)}</span><span class="meta" style="margin:0">Công sức ${esc(p.cong_suc||'')}</span></div>
    <b>${esc(p.tieu_de)}</b><div class="meta" style="margin:2px 0 0">${esc(p.mo_ta||'')}</div>
    ${(p.loi_ich||[]).length?`<div class="row" style="gap:4px;margin-top:6px;flex-wrap:wrap">${p.loi_ich.map(b=>`<span class="bn">${esc(d.benefits[b]||b)}</span>`).join('')}</div>`:''}
    ${p.rui_ro?`<div class="meta" style="margin:6px 0 0">Rủi ro: ${esc(p.rui_ro)}</div>`:''}</div></label>`).join('');
  const applied = n.applied ? `<div class="sec"><h2>Đã áp dụng</h2></div><div class="card pad">${(n.applied.done||[]).map(x=>`<div class="mdli"><span>${ico('check',14)}</span><span>${esc(x)}</span></div>`).join('')}
    ${(n.ticket_rows||[]).map(t=>`<button class="btn sm" style="margin:6px 6px 0 0" onclick="rpTicket('${t.id}')">${ico('code',14)} ${esc(t.title)} · ${esc(d.status[t.status]||t.status)}</button>`).join('')}</div>` : '';
  sheet(`<div class="row" style="gap:6px;align-items:center;margin-bottom:6px"><span class="vd ${a.ket_luan}">${esc(d.verdict[a.ket_luan]||'')}</span><span class="fit">Phù hợp ${a.phu_hop??'?'}/10</span></div>
    <h2 style="margin-bottom:2px">${esc(a.ten_vi||n.full_name)}</h2><div class="meta">${esc(n.full_name)} · ${kfmt(n.stars)} sao${n.stars_week?` (+${kfmt(n.stars_week)} tuần này)`:''}${n.lang?` · ${esc(n.lang)}`:''}${n.license?` · ${esc(n.license)}`:''}${n.pushed?` · cập nhật ${esc(n.pushed)}`:''}</div>
    <div class="card pad" style="margin-top:12px"><b>Là gì</b><p class="mdp">${esc(a.la_gi||n.desc||'')}</p>
      ${(a.diem_noi_bat||[]).length?`<b>Điểm đáng học</b>${a.diem_noi_bat.map(x=>`<div class="mdli"><span>•</span><span>${esc(x)}</span></div>`).join('')}`:''}
      ${a.chat_luong?`<b style="display:block;margin-top:8px">Độ chín</b><p class="mdp">${esc(a.chat_luong)}</p>`:''}</div>
    <div class="caobox"><b>Nhận định</b><p style="-webkit-line-clamp:unset">${esc(a.nhan_dinh||'')}</p></div>
    <div class="sec"><h2>Đề xuất cho superHuy</h2></div><div class="card list rpopts">${props||'<div class="empty">Không có đề xuất.</div>'}</div>
    <p class="muted small" style="margin:8px 2px 0">Làm ngay: theo dõi bản phát hành, lưu best practice vào Second Brain, thêm quy tắc vận hành. Phiếu nâng cấp: superHuy lập kế hoạch, lập trình viên làm và kiểm thử rồi mới triển khai.</p>
    ${applied}
    <div class="row" style="margin-top:12px"><button class="btn grow" onclick="openLink('${esc(n.url)}')">${ico('code',16)} GitHub</button>${n.status==='new'?`<button class="btn pri grow" onclick="rpApplyPicked('${n.id}')">${ico('check',16)} Áp dụng mục đã chọn</button>`:''}</div>`);
}
function rpApplyPicked(id){
  const picks = [...document.querySelectorAll('.rpopts input:checked')].map(x=>x.dataset.i).join(',');
  if(!picks) return toast('Anh chọn ít nhất 1 đề xuất');
  rpApply(id, picks);
}
function rpUpHtml(){
  const d = S.rp, st = d.status||{};
  const groups = [['moi','dang_lam'],['xong','bo']];
  const tk = d.tickets.length ? groups.map((g,gi)=>{ const rows = d.tickets.filter(t=>g.includes(t.status)); if(!rows.length) return '';
    return `${gi?'<div class="sec"><h2>Đã xử lý</h2></div>':''}<div class="card list">${rows.map(t=>`<button onclick="rpTicket('${t.id}')"><span class="thumb">${ico('code',20)}</span>
      <div class="grow" style="min-width:0"><div class="ttl2">${esc(t.title)}</div><div class="meta">${esc(t.repo)} · công sức ${esc(t.effort)} · ${t.steps} bước · ${esc(ago(t.at))}</div></div><span class="tkst ${t.status}">${esc(st[t.status]||t.status)}</span></button>`).join('')}</div>`; }).join('')
    : `<div class="card empty">Chưa có phiếu nâng cấp. Quẹt phải một repo có đề xuất đụng tới code, superHuy sẽ lập phiếu kèm kế hoạch chi tiết.</div>`;
  const rules = d.rules.length ? `<div class="card list">${d.rules.map(r=>`<div class="wk"><div class="grow"><div class="ttl2" style="${r.on===false?'opacity:.5':''}">${esc(r.text)}</div><div class="meta">Từ ${esc(r.repo)} · ${esc(ago(r.at))}</div></div>
      <button class="btn sm" onclick="rpRule('${r.id}','quytac_bat')">${r.on===false?'Bật':'Tắt'}</button><button class="iconbtn" aria-label="Xoá quy tắc" onclick="rpRule('${r.id}','quytac_xoa')">${ico('del',18)}</button></div>`).join('')}</div>`
    : `<div class="card empty">Chưa có quy tắc nào.</div>`;
  const watch = d.watch.length ? `<div class="card list">${d.watch.map(w=>`<div class="wk"><span class="thumb">${ico('refresh',18)}</span><div class="grow"><div class="ttl2">${esc(w.full_name)}</div><div class="meta">${w.new?`Bản mới: ${esc(w.new)}`:w.last?`Bản hiện tại: ${esc(w.last)}`:'Chưa có bản phát hành'}</div></div>
      <button class="btn sm" onclick="openLink('${esc(w.url)}/releases')">Xem</button><button class="iconbtn" aria-label="Bỏ theo dõi" onclick="rpUnwatch('${esc(w.full_name)}')">${ico('x',18)}</button></div>`).join('')}</div>`
    : `<div class="card empty">Chưa theo dõi repo nào.</div>`;
  return `<div class="sec" style="margin-top:4px"><h2>Phiếu nâng cấp</h2></div>${tk}
    <div class="sec"><h2>Quy tắc vận hành đã thêm</h2></div><p class="muted small" style="margin:-4px 2px 8px">superHuy làm theo các quy tắc đang bật khi trò chuyện và xử lý việc.</p>${rules}
    <div class="sec"><h2>Repo đang theo dõi</h2></div>${watch}`;
}
function rpDoneHtml(){
  const d = S.rp;
  return d.applied.length ? `<div class="card list">${d.applied.map(n=>`<button onclick="rpOpen('${n.id}')"><span class="thumb">${ico('code',20)}</span><div class="grow" style="min-width:0"><div class="ttl2">${esc(n.a?.ten_vi||n.full_name)}</div>
    <div class="meta">${esc(n.full_name)} · ${(n.applied?.done||[]).length} việc · ${esc(ago(n.applied?.at))}</div></div><span class="chev">${ico('chev',18)}</span></button>`).join('')}</div>`
    : `<div class="card empty">Chưa áp dụng repo nào. Quẹt phải ở “Tuần này”.</div>`;
}
async function rpTicket(id){
  let t; try{ t = await run('noidung','phieu_xem',{tid:id},'',true); }catch(e){ return toast(e.message); }
  const st = (S.rp||{}).status||{moi:'Chờ làm',dang_lam:'Đang làm',xong:'Đã xong',bo:'Bỏ'};
  sheet(`<div class="meta" style="margin-bottom:4px">Phiếu nâng cấp · ${esc(st[t.status]||t.status)}</div>
    <div class="mdbody">${mdRender(t.markdown.replace(/^---[\s\S]*?---\n/,'').replace(/\[([^\]]+)\]\([^)]+\)/g,'$1'))}</div>
    <div class="sec"><h2>Trạng thái</h2></div><div class="chips" style="padding-top:0">${Object.entries(st).map(([k,l])=>`<button class="chip ${t.status===k?'on':''}" onclick="rpTicketSet('${t.id}','${k}')">${esc(l)}</button>`).join('')}</div>
    <div class="row" style="margin-top:12px"><button class="btn grow" onclick="rpCopy()">${ico('pen',16)} Chép kế hoạch</button><button class="btn grow" onclick="openLink('${esc(t.url)}')">${ico('code',16)} Repo gốc</button></div>`);
  S.rpTk = t;
}
async function rpCopy(){ try{ await navigator.clipboard.writeText(S.rpTk?.markdown||''); toast('Đã chép kế hoạch'); }catch(e){ toast('Không chép được trên máy này'); } }
async function rpTicketSet(id, st){ try{ const r = await run('noidung','phieu_trangthai',{tid:id, status:st},'',true); toast(r.text||'Đã cập nhật'); S.rp = null; rpLoad(); rpTicket(id); }catch(e){ toast(e.message); } }
async function rpRule(id, act){ try{ await run('noidung',act,{rule_id:id},'',true); S.rp = null; rpLoad(); }catch(e){ toast(e.message); } }
async function rpUnwatch(n){ try{ await run('noidung','bo_theodoi',{full_name:n},'',true); S.rp = null; rpLoad(); }catch(e){ toast(e.message); } }
async function rpScan(){
  toast('superHuy đang săn repo GitHub tuần này và phân tích, khoảng 3-5 phút', 4500);
  S.rp && (S.rp.scanning = true); render();
  try{ const r = await run('noidung','repo_quet',{force:true},'Săn repo'); toast(r.text||'Xong', 3500); }catch(e){ toast(e.message); }
  S.rp = null; rpLoad();
}
function rpAdd(){
  sheet(`<h2>Phân tích một repo</h2><p class="meta">Dán link repo GitHub, superHuy sẽ đọc README, đánh giá và đề xuất cách áp dụng.</p>
    <label class="field" style="margin-top:12px"><span>Link repo</span><input id="rpUrl" type="url" inputmode="url" placeholder="https://github.com/chu/repo"></label>
    <button class="btn pri" style="width:100%" onclick="rpAddGo()">${ico('spark',16)} Phân tích</button>`);
  setTimeout(()=>$('#rpUrl')?.focus(), 200);
}
async function rpAddGo(){
  const u = $('#rpUrl').value.trim(); if(!u) return;
  $('#sheetBody').innerHTML = `<h2>Đang phân tích…</h2><div class="card pad"><div class="spin"></div><p class="meta">superHuy đang đọc ${esc(u)}</p></div>`;
  try{ const r = await run('noidung','repo_them',{url:u},'Phân tích repo'); S.rp = null; await rpLoad(); rpOpen(r.id); }catch(e){ closeSheet(); toast(e.message); }
}
function vStrategy(){
  const d = S.cl;
  if(!d){ clLoad(); return `<div class="card pad"><div class="skel" style="width:60%"></div><div class="skel"></div><div class="skel" style="width:40%"></div></div>`; }
  const f = S.clLens||'', list = (d.insights||[]).filter(r=>!f || r.lens===f || ((r.cao?.[f]?.lien_quan)||0)>=7);
  return `<p class="lead" style="margin:0 0 12px">superHuy săn case study, best practice, tính năng mới và ý tưởng về agentic commerce, phân tích như một CAO, rồi tích luỹ thành 2 tài liệu sống, cập nhật mỗi thứ Hai.</p>
    <div class="cldocs">${d.docs.map(x=>`<article class="card pad cldoc ${x.lens}"><div class="row" style="align-items:center;gap:8px"><span class="trk ${x.lens}">${esc(d.lenses[x.lens])}</span><span class="grow"></span><span class="meta" style="margin:0">${x.version?`Bản ${x.version} · ${esc(ago(x.updated))}`:'Chưa có'}</span></div>
      <h3>${esc(x.title)}</h3><p class="clamp3">${esc(x.summary||'superHuy sẽ viết bản đầu tiên từ các phân tích CAO.')}</p>
      <div class="row" style="margin-top:auto"><button class="btn pri sm grow" onclick="clDoc('${x.lens}')" ${x.version?'':'disabled'}>${ico('brain',15)} Đọc</button><button class="btn sm" onclick="clUpdate('${x.lens}')">${ico('refresh',15)} Cập nhật</button></div></article>`).join('')}</div>
    <div class="sec"><h2>Phân tích gần đây</h2><button class="link" onclick="clScan()">${ico('refresh',15)} Săn thêm</button></div>
    <div class="chips" style="padding-top:0;margin-bottom:10px"><button class="chip ${!f?'on':''}" onclick="S.clLens='';render()">Tất cả ${d.counts.all}</button>${Object.entries(d.lenses).map(([k,l])=>`<button class="chip ${f===k?'on':''}" onclick="S.clLens='${k}';render()">${esc(l)}</button>`).join('')}</div>
    ${list.length?`<div class="card list">${list.map(r=>`<button onclick="clInsight('${r.id}')"><div class="grow" style="min-width:0"><div class="row" style="gap:6px;align-items:center;margin-bottom:3px"><span class="itype">${esc(ITYPE[r.cao?.loai]||'Tin')}</span>${rel(r.cao)}<span class="meta" style="margin:0">${esc(ago(r.at))}</span></div>
      <div class="ttl2">${esc(r.headline)}</div><div class="meta clamp2">${esc((r.cao?.phan_tich||[])[0]||r.cao?.tom_tat||'')}</div></div><span class="chev">${ico('chev',18)}</span></button>`).join('')}</div>`
      :`<div class="card empty">Chưa có phân tích nào. Bấm “Săn thêm”, hoặc bật 2 tuyến Agentic commerce và Chuyển đổi trong cài đặt (biểu tượng bánh răng).</div>`}`;
}
async function clLoad(){ try{ S.cl = await run('noidung','chien_luoc',{},'',true); }catch(e){ S.cl = {docs:[], insights:[], lenses:{}, counts:{all:0}}; toast(e.message); } if(S.tab==='content' && S.cview==='cl' && !$('#sheet').classList.contains('on')) render(); }
async function clScan(){
  toast('superHuy đang săn tin agentic commerce và phân tích CAO, khoảng 2-4 phút', 4000);
  try{ for(const t of ['roimaxx','leversphere']) await run('noidung','quet',{track:t},'Săn tin chiến lược'); S.cl = null; await cReload(); clLoad(); }catch(e){ toast(e.message); }
}
async function clInsight(id){
  try{ const r = await run('noidung','insight',{iid:id},'',true); S.clCur = {cao:r.cao, title:r.headline, url:r.url};
    sheet(caoHtml(r.cao, `<div class="meta" style="margin-bottom:4px">${esc(src(r.source))} · ${esc(ago(r.at))}</div><h2 style="margin-bottom:10px">${esc(r.headline)}</h2>`) +
      `<div class="row" style="margin-top:6px">${r.url?`<button class="btn grow" onclick="openLink('${esc(r.url)}')">${ico('link',16)} Bài gốc</button>`:''}<button class="btn grow" onclick="closeSheet();S.dockOpen=true;dock();$('#dIn').value='Về phân tích “${esc(r.headline).replace(/'/g,'&#39;')}”: ';$('#dIn').focus()">${ico('chat',16)} Hỏi thêm</button></div>`);
  }catch(e){ toast(e.message); }
}
function mdRender(t){
  const lines = String(t||'').split('\n'), out = []; let tb = [];
  const flush = () => { if(!tb.length) return; const rows = tb.filter(r=>!/^\s*\|?\s*:?-{2,}/.test(r)).map(r=>r.trim().replace(/^\||\|$/g,'').split('|').map(c=>c.trim()));
    out.push(`<div class="mdtable"><table>${rows.map((r,i)=>`<tr>${r.map(c=>i?`<td>${inl(c)}</td>`:`<th>${inl(c)}</th>`).join('')}</tr>`).join('')}</table></div>`); tb = []; };
  const inl = x => esc(x).replace(/\*\*([^*]+)\*\*/g,'<b>$1</b>').replace(/\[\[([^\]|]+)(\|[^\]]+)?\]\]/g,'<b style="color:var(--jade)">$1</b>');
  let code = null;
  for(const l of lines){
    if(/^\s*```/.test(l)){ if(code===null){ flush(); code = []; } else { out.push(`<pre class="mdcode"><code>${esc(code.join('\n'))}</code></pre>`); code = null; } continue; }
    if(code!==null){ code.push(l); continue; }
    if(/^\s*\|/.test(l)){ tb.push(l); continue; } flush();
    let m;
    if((m=l.match(/^(#{1,4})\s+(.*)/))) out.push(`<h${Math.min(m[1].length+1,4)} class="mdh">${inl(m[2])}</h${Math.min(m[1].length+1,4)}>`);
    else if((m=l.match(/^\s*[-*+]\s+(\[[ x]\]\s*)?(.*)/))) out.push(`<div class="mdli"><span>${m[1]?(m[1].includes('x')?'☑':'☐'):'•'}</span><span>${inl(m[2])}</span></div>`);
    else if((m=l.match(/^\s*(\d+)[.)]\s+(.*)/))) out.push(`<div class="mdli"><span>${m[1]}.</span><span>${inl(m[2])}</span></div>`);
    else if(l.startsWith('>')) out.push(`<div class="mdq">${inl(l.replace(/^>\s?(\[![a-z]+\]\s*)?/,''))}</div>`);
    else if(l.trim()) out.push(`<p class="mdp">${inl(l)}</p>`);
  }
  if(code!==null) out.push(`<pre class="mdcode"><code>${esc(code.join('\n'))}</code></pre>`);
  flush(); return out.join('');
}
async function clDoc(lens){
  try{ const d = await run('noidung','tai_lieu',{lens},'',true); S.clDocCur = d;
    sheet(`<div class="meta" style="margin-bottom:4px">${esc(d.name)} · Bản ${d.version} · ${esc(ago(d.updated))}</div><h2 style="margin-bottom:10px">${esc(d.title)}</h2>
      ${d.summary?`<div class="note" style="margin-bottom:12px">${esc(d.summary)}</div>`:''}
      ${(d.changes||[]).length?`<details style="margin-bottom:12px"><summary>Thay đổi trong bản này</summary><ul>${d.changes.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></details>`:''}
      <div class="mdbody">${mdRender(d.md)}</div>
      ${d.obsidian?`<p class="meta" style="margin-top:14px">Đã lưu trong Obsidian: ${esc(d.obsidian)}</p>`:''}
      <div class="row" style="margin-top:10px"><button class="btn grow" onclick="copyText(S.clDocCur.md)">${ico('copy',16)} Sao chép</button><button class="btn grow" onclick="closeSheet();S.dockOpen=true;dock();$('#dIn').value='Theo tài liệu ${esc(d.title).replace(/'/g,'&#39;')}, ';$('#dIn').focus()">${ico('chat',16)} Hỏi superHuy</button></div>`);
  }catch(e){ toast(e.message); }
}
async function clUpdate(lens){
  toast('superHuy đang viết lại tài liệu từ các phân tích mới nhất, khoảng 1-2 phút', 4000);
  try{ const r = await run('noidung','cap_nhat_tai_lieu',{lens},'Cập nhật tài liệu chiến lược'); toast(r.text, 3500); S.cl = null; clLoad(); }catch(e){ toast(e.message); }
}

/* ---------- Reel Studio: xem, chỉnh nhanh, dựng lại có tiến độ, phiên bản, công thức, skill News Studio */
const ST_QUICK = ['Giọng nam, đọc vừa phải','Giọng nữ','Đọc chậm, rõ hơn','Nhanh hơn kiểu reels','Tắt nhạc nền','Hook 3 giây đầu mạnh hơn','Thêm số liệu cụ thể','Rút còn 30 giây'];
const ST_MAIN = {hook:'text', headline:'title', stat:'value', quote:'quote', list:'title', analysis:'label', cta:'text', image:'caption'};
const fmtS = t => `${String(Math.floor((t||0)/60)).padStart(2,'0')}:${String(Math.floor((t||0)%60)).padStart(2,'0')}`;
async function studioOpen(cid, iid){
  S.st = {cid, iid, tab: S.st?.cid===cid ? S.st.tab : 'edit', preview:null};
  sheet(`<h2>Reel Studio</h2><div class="card pad"><div class="spin"></div></div>`);
  try{ S.st.d = await run('noidung','studio',{cid},'',true); stPaint(); stPoll(); }catch(e){ closeSheet(); toast(e.message); }
}
function stPaint(keep){
  const st = S.st, d = st.d, r = d.render||{}, busy = r.status==='running', o = d.options, set = st.set || {...d.settings};
  st.set = set;
  const cur = d.versions.find(v=>v.id===d.current) || d.versions[d.versions.length-1];
  const pv = st.preview ? d.versions.find(v=>v.id===st.preview) : null, show = pv || {video:d.video, image:d.image, chapters:d.chapters};
  const y = $('#sheet').scrollTop;
  const parts = Object.keys(S.cpack?.parts||{}).filter(k=>k!=='reel');
  sheet(`<div class="row" style="align-items:center;gap:8px;margin-bottom:2px"><span class="itype">Reel Studio</span>${d.recipe?`<span class="meta" style="margin:0">Công thức: ${esc(d.recipe)}</span>`:''}<span class="grow"></span>${parts.map(k=>`<button class="link" onclick="cPack('${st.iid}','${k}')">${COUT[k]}</button>`).join(' ')}</div>
    <h2 style="margin:4px 0 10px">${esc(d.title.replace('Reels: ',''))}</h2>
    <div class="stwrap"><video id="vplayer" class="media reel" src="${show.video||''}" controls playsinline preload="metadata" poster="${show.image||''}"></video></div>
    ${d.voice_engine==='silent'&&!pv?`<div class="note" style="margin-bottom:10px;border-color:var(--danger)">Bản này chưa có giọng đọc (lỗi bộ đọc giọng cũ). Bấm “Dựng lại” để có thuyết minh.</div>`:''}
    ${d.versions.length?`<div class="stvers">${d.versions.slice().reverse().map((v,i)=>`<button class="${(st.preview||d.current)===v.id?'on':''}" onclick="stPreview('${v.id}')"><b>Bản ${d.versions.length-i}${v.id===d.current?' ★':''}</b><span>${fmtS(v.duration)} · ${esc(o.voices[v.settings?.voice]?.split(' ')[0]||'')}${v.voice_engine==='silent'?' · không tiếng':''}</span><em>${esc((v.note||'').slice(0,34))}</em></button>`).join('')}</div>`:''}
    ${pv&&pv.id!==d.current?`<button class="btn pri full" style="margin-bottom:10px" onclick="stChoose('${pv.id}')">${ico('check',16)} Dùng bản này làm bản chính</button>`:''}
    ${(show.chapters||[]).length?`<div class="vchap">${show.chapters.map(x=>`<button onclick="vSeek(${x.t})"><span>${fmtS(x.t)}</span>${esc(x.label)}</button>`).join('')}</div>`:''}
    <div class="stbar"><button class="btn pri sm" onclick="vDownload('${d.id}')">${ico('upload',15)} Lưu về máy</button><button class="btn sm" onclick="vSendTg('${d.id}')">${ico('send',15)} Telegram</button><button class="btn sm" onclick="openPublish('${d.id}')">${ico('send',15)} Đăng</button></div>
    <div id="stProg">${stProgHtml(r)}</div>
    <div class="stquick"><form class="rptform" onsubmit="event.preventDefault();stQuick($('#stQ').value)"><input id="stQ" placeholder="Muốn sửa gì? Ví dụ: giọng nam, hook mạnh hơn, bỏ nhạc…" autocomplete="off" ${busy?'disabled':''}><button class="send" aria-label="Chỉnh" ${busy?'disabled':''}>${ico('arrow',18)}</button></form>
      <div class="chips" style="padding-top:8px">${ST_QUICK.map(q=>`<button class="chip" ${busy?'disabled':''} onclick="stQuick('${q}')">${q}</button>`).join('')}</div></div>
    <div class="seg" style="margin:6px 0 12px">${[['edit','Cài đặt'],['script','Kịch bản'],['cap','Caption'],['recipe','Công thức']].map(([k,l])=>`<button class="${st.tab===k?'on':''}" onclick="S.st.tab='${k}';stPaint(true)">${l}</button>`).join('')}</div>
    <div id="stTab">${stTabHtml()}</div>`);
  if(keep) $('#sheet').scrollTop = y;
}
function stProgHtml(r){
  if(r.status==='running'){ const el = r.started ? Math.max(0, Math.round((Date.now()-Date.parse(r.started))/1000)) : 0;
    return `<div class="card pad stprog"><div class="row" style="align-items:center;gap:10px"><div class="spin"></div><b class="grow">Đang dựng bản mới · ${r.pct||0}%</b><span class="meta" style="margin:0">${el}s</span></div>
      <div class="pbar big"><span style="width:${r.pct||2}%"></span></div><div class="meta" style="margin:4px 0 0">${esc(r.step||'')}${r.note?` · theo yêu cầu: “${esc(r.note)}”`:''}</div></div>`; }
  if(r.status==='error') return `<div class="card pad stprog err"><b style="color:var(--danger)">Chưa dựng được</b><p class="meta" style="margin:4px 0 8px">${esc(r.error||'')}</p><button class="btn sm" onclick="stRender({})">${ico('refresh',14)} Thử lại</button></div>`;
  return '';
}
function stTabHtml(){
  const st = S.st, d = st.d, o = d.options, s = st.set, busy = (d.render||{}).status==='running';
  if(st.tab==='edit') return `<p class="lbl">Giọng thuyết minh</p><div class="seg" style="margin-bottom:10px">${Object.entries(o.voices).map(([k,l])=>`<button class="${s.voice===k?'on':''}" onclick="S.st.set.voice='${k}';stPaint(true)">${esc(l.split(' (')[0])}</button>`).join('')}</div>
    <p class="lbl">Tốc độ đọc</p><div class="seg" style="margin-bottom:10px">${Object.entries(o.speeds).map(([k,l])=>`<button class="${s.speed===k?'on':''}" onclick="S.st.set.speed='${k}';stPaint(true)">${esc(l)}</button>`).join('')}</div>
    <p class="lbl">Nhạc nền</p><div class="seg" style="margin-bottom:10px">${Object.entries(o.music).map(([k,l])=>`<button class="${s.music===k?'on':''}" onclick="S.st.set.music='${k}';stPaint(true)">${esc(l)}</button>`).join('')}</div>
    <p class="lbl">Độ dài</p><div class="seg" style="margin-bottom:10px">${o.lens.map(x=>`<button class="${+s.len===x?'on':''}" onclick="S.st.set.len=${x};stPaint(true)">${x}s</button>`).join('')}</div>
    <label class="pick"><input type="checkbox" id="stRw" ${st.rw?'checked':''} onchange="S.st.rw=this.checked"><div class="grow"><div style="font-weight:600">Viết lại kịch bản</div><div class="meta">Bỏ chọn để giữ nội dung, chỉ đổi giọng, nhịp, nhạc</div></div></label>
    <button class="btn pri full" ${busy?'disabled':''} onclick="stRender(S.st.set, S.st.rw)">${ico('refresh',16)} Dựng lại với cài đặt này</button>`;
  if(st.tab==='script'){ const sc = (d.script||{}).scenes||[];
    if(!sc.length) return `<div class="card empty">Bản này chưa có kịch bản bản tin. Bấm “Dựng lại” (tab Cài đặt, chọn Viết lại kịch bản) để tạo.</div>`;
    return `<p class="meta" style="margin:0 0 10px">Sửa trực tiếp lời đọc và chữ trên màn hình từng cảnh, rồi dựng lại (không cần AI viết lại).</p>${sc.map((x,i)=>{ const k = ST_MAIN[x.type], v = k ? (x.on_screen||{})[k] : '';
      return `<div class="card pad stscene"><div class="row" style="align-items:center;gap:8px;margin-bottom:6px"><span class="itype">${i+1}. ${esc(x.type)}</span></div>
        ${k?`<label class="field" style="margin-bottom:8px"><span>Chữ trên màn hình</span><input type="text" data-i="${i}" data-k="${k}" class="stOn" value="${esc(v||'')}"></label>`:''}
        <label class="field" style="margin:0"><span>Lời đọc</span><textarea data-i="${i}" class="stVo" rows="2">${esc(x.voiceover||'')}</textarea></label></div>`; }).join('')}
      <button class="btn pri full" ${busy?'disabled':''} onclick="stScript()">${ico('refresh',16)} Dựng lại theo kịch bản đã sửa</button>`; }
  if(st.tab==='cap') return `<label class="field"><span>Caption đăng kèm</span><textarea id="stCap" style="min-height:140px">${esc(d.caption||'')}</textarea></label>
    <div class="row" style="margin-bottom:12px"><button class="btn grow" onclick="stCaption()">${ico('check',16)} Lưu</button><button class="btn grow" onclick="copyText($('#stCap').value)">${ico('copy',16)} Sao chép</button></div>
    ${d.first_comment?`<p class="lbl">Comment đầu (chứa link nguồn)</p><div class="card out" style="margin-bottom:8px">${esc(d.first_comment)}</div><button class="btn full" onclick="copyText(S.st.d.first_comment)">${ico('copy',16)} Sao chép comment</button>`:''}`;
  const R = st.rc;
  if(!R){ stRecipes(); return `<div class="card pad"><div class="skel"></div></div>`; }
  return `<div class="note" style="margin-bottom:12px">Ưng bản này? Lưu thành <b>công thức</b>: superHuy ghi cài đặt, cấu trúc cảnh và quy tắc rút ra từ các lần anh chỉnh vào Second Brain, rồi dùng cho mọi video sau. Các công thức gộp thành skill <b>News Studio</b>.</div>
    <label class="field"><span>Tên công thức</span><input type="text" id="rcName" placeholder="Ví dụ: Bản tin 60s giọng nam nhịp vừa"></label>
    <label class="field"><span>Ghi chú thêm (không bắt buộc)</span><textarea id="rcNote" rows="2" placeholder="Ví dụ: luôn mở bằng con số, kết bằng câu hỏi cho seller"></textarea></label>
    <label class="pick"><input type="checkbox" id="rcDef" checked><div class="grow"><div style="font-weight:600">Đặt làm mặc định</div><div class="meta">Video sau tự theo công thức này</div></div></label>
    <button class="btn pri full" id="rcGo" onclick="stSaveRecipe()">${ico('brain',16)} Lưu công thức vào Second Brain</button>
    ${(R.items||[]).length?`<p class="lbl" style="margin-top:16px">Công thức đã lưu</p><div class="card list">${R.items.slice().reverse().map(x=>`<div style="align-items:center"><div class="grow"><div style="font-weight:600">${esc(x.name)}${x.default?' <span class="itype">Mặc định</span>':''}</div><div class="meta">${esc(x.summary||'')}</div></div>
      ${x.default?'':`<button class="btn sm" onclick="stRecipeDef('${x.id}')">Mặc định</button>`}<button class="iconbtn sm" aria-label="Xoá" onclick="stRecipeDel('${x.id}')">${ico('x',16)}</button></div>`).join('')}</div>`:''}
    <div class="card pad" style="margin-top:12px"><div class="row" style="align-items:center"><div class="grow"><div style="font-weight:600">Skill News Studio</div><div class="meta">${R.skill?'Cập nhật '+esc(ago(R.skill)):'Chưa có'} · SKILL.md trong Obsidian › Skills/news-studio</div></div><button class="btn sm" onclick="stSkill()">Xem</button></div></div>`;
}
function stPreview(vid){ S.st.preview = vid===S.st.d.current ? null : vid; stPaint(true); const v = $('#vplayer'); v && v.play().catch(()=>{}); }
async function stChoose(vid){ try{ S.st.d = await run('noidung','chon_ban',{cid:S.st.cid, vid},'',true); S.st.preview = null; toast('Đã chọn làm bản chính'); stPaint(true); cReload(); }catch(e){ toast(e.message); } }
async function stRender(set, rewrite){
  try{ S.st.d = await run('noidung','dung_lai',{cid:S.st.cid, voice:set.voice||'', speed:set.speed||'', music:set.music||'', length:set.len||0, rewrite:!!rewrite},'',true); S.st.preview = null; stPaint(true); stPoll(); haptic('medium'); }
  catch(e){ toast(e.message); }
}
async function stQuick(q){
  q = (q||'').trim(); if(!q) return toast('Anh nói muốn sửa gì nhé');
  const inp = $('#stQ'); if(inp){ inp.value = ''; inp.disabled = true; }
  $('#stProg').innerHTML = stProgHtml({status:'running', pct:1, step:'superHuy đang hiểu yêu cầu và sửa kịch bản…', note:q, started:new Date().toISOString()});
  try{ const r = await run('noidung','chinh_nhanh',{cid:S.st.cid, instruction:q},'',true); S.st.d = r; S.st.set = null; S.st.preview = null; toast(r.text, 3500); stPaint(true); stPoll(); }
  catch(e){ toast(e.message, 4500); try{ S.st.d = await run('noidung','studio',{cid:S.st.cid},'',true); }catch(_){} stPaint(true); }
}
async function stScript(){
  const sc = JSON.parse(JSON.stringify(S.st.d.script.scenes));
  document.querySelectorAll('.stVo').forEach(t=>{ sc[+t.dataset.i].voiceover = t.value.trim(); });
  document.querySelectorAll('.stOn').forEach(t=>{ const x = sc[+t.dataset.i]; x.on_screen = {...(x.on_screen||{}), [t.dataset.k]: t.value.trim()}; });
  try{ S.st.d = await run('noidung','sua_kich_ban',{cid:S.st.cid, scenes:JSON.stringify(sc.map(x=>({voiceover:x.voiceover, on_screen:x.on_screen})))},'',true); S.st.preview = null; toast('Đang dựng lại theo kịch bản mới'); stPaint(true); stPoll(); }
  catch(e){ toast(e.message); }
}
async function stCaption(){ try{ await run('noidung','caption',{cid:S.st.cid, caption:$('#stCap').value},'',true); S.st.d.caption = $('#stCap').value; toast('Đã lưu caption'); }catch(e){ toast(e.message); } }
function stPoll(){
  clearTimeout(S.stTimer);
  if((S.st?.d?.render||{}).status!=='running') return;
  S.stTimer = setTimeout(async ()=>{
    if(!S.st || !$('#sheet').classList.contains('on') || !$('#stProg')) return;
    try{ const d = await run('noidung','studio',{cid:S.st.cid},'',true); const was = S.st.d.render?.status; S.st.d = d;
      if(d.render?.status==='running'){ $('#stProg').innerHTML = stProgHtml(d.render); return stPoll(); }
      if(was==='running'){ S.st.set = null; stPaint(true); if(d.render?.status==='done'){ notifyH('success'); toast(`Xong bản mới (${fmtS(d.duration)}). Bấm ▶ để xem.`, 3500); const v = $('#vplayer'); v && v.scrollIntoView({behavior:'smooth', block:'center'}); } else toast('Dựng chưa thành công'); cReload(); }
    }catch(e){ stPoll(); }
  }, 2000);
}
async function stRecipes(){ try{ S.st.rc = await run('noidung','cong_thuc_ds',{},'',true); }catch(e){ S.st.rc = {items:[]}; } if(S.st.tab==='recipe') $('#stTab').innerHTML = stTabHtml(); }
async function stSaveRecipe(){
  const b = $('#rcGo'); b.disabled = true; b.textContent = 'superHuy đang rút công thức…';
  try{ const r = await run('noidung','cong_thuc_luu',{cid:S.st.cid, name:$('#rcName').value.trim(), notes:$('#rcNote').value.trim(), make_default:$('#rcDef').checked},'Lưu công thức reels'); toast(r.text, 4000); notifyH('success'); S.st.rc = null; S.st.d.recipe = r.default?r.name:S.st.d.recipe; stPaint(true); }
  catch(e){ toast(e.message); b.disabled = false; b.textContent = 'Lưu công thức vào Second Brain'; }
}
async function stRecipeDef(id){ try{ const r = await run('noidung','cong_thuc_macdinh',{rid:id},'',true); toast(r.text); S.st.rc = null; stPaint(true); }catch(e){ toast(e.message); } }
async function stRecipeDel(id){ try{ await run('noidung','cong_thuc_xoa',{rid:id},'',true); S.st.rc = null; stPaint(true); }catch(e){ toast(e.message); } }
async function stSkill(){
  try{ const s = await run('noidung','skill_xem',{},'',true);
    sheet(`<button class="back" onclick="studioOpen('${S.st.cid}','${S.st.iid}')">${ico('chev',18)} Reel Studio</button><h2 style="margin:6px 0 4px">Skill News Studio</h2>
      <div class="meta" style="margin-bottom:10px">${s.updated?'Cập nhật '+esc(ago(s.updated))+' · ':''}${s.obsidian?esc(s.obsidian):''}</div>
      ${s.md?`<div class="mdbody">${mdRender(s.md.replace(/^---[\s\S]*?---\n/,''))}</div><button class="btn full" style="margin-top:10px" onclick="copyText(S.stSkillMd)">${ico('copy',16)} Sao chép SKILL.md</button>`:`<div class="card empty">Chưa có skill. Lưu ít nhất 1 công thức, superHuy sẽ soạn skill từ đó.</div>`}
      <button class="btn pri full" style="margin-top:10px" id="skGo" onclick="stSkillBuild()">${ico('refresh',16)} Cập nhật skill từ công thức và phản hồi</button>`); S.stSkillMd = s.md; }
  catch(e){ toast(e.message); }
}
async function stSkillBuild(){ const b = $('#skGo'); b.disabled = true; b.textContent = 'superHuy đang soạn skill…'; try{ await run('noidung','skill_capnhat',{},'Cập nhật skill News Studio'); stSkill(); }catch(e){ toast(e.message); b.disabled = false; } }

/* ---------- Xem trước và lưu video */
function vPlayer(c){
  const m = c.meta||{}, ch = m.chapters||[];
  return `<div class="vwrap"><video id="vplayer" class="media reel" src="${c.video}" controls playsinline preload="metadata" poster="${c.image||''}"></video></div>
    ${ch.length?`<div class="vchap" role="list">${ch.map((x,i)=>`<button role="listitem" onclick="vSeek(${x.t})"><span>${String(Math.floor(x.t/60)).padStart(2,'0')}:${String(Math.floor(x.t%60)).padStart(2,'0')}</span>${esc(x.label)}</button>`).join('')}</div>`:''}
    <div class="vacts">
      <button class="btn pri" onclick="vDownload('${c.id}')">${ico('upload',16)} Lưu về máy</button>
      <button class="btn" onclick="vSendTg('${c.id}')">${ico('send',16)} Gửi Telegram</button>
      <button class="btn" onclick="vFull()">${ico('play',16)} Toàn màn hình</button>
      <button class="btn" onclick="vRedo('${c.id}')">${ico('refresh',16)} Dựng lại</button>
    </div>
    <p class="meta" style="margin:0 0 12px">${m.duration?`${Math.round(m.duration)} giây · `:''}${m.engine==='newscast'?'Bản tin đồ hoạ':'Reels chữ'}${m.voice_engine==='silent'?' · chưa có giọng đọc':''}</p>`;
}
function vSeek(t){ const v = $('#vplayer'); if(!v) return; v.currentTime = t; v.play().catch(()=>{}); }
function vFull(){ const v = $('#vplayer'); if(!v) return; (v.requestFullscreen||v.webkitEnterFullscreen||v.webkitRequestFullscreen)?.call(v); v.play().catch(()=>{}); }
function vPlayVer(u){ const v = $('#vplayer'); if(!v) return; v.src = u; v.play().catch(()=>{}); v.scrollIntoView({behavior:'smooth', block:'center'}); }
async function vDownload(cid){
  try{ const r = await run('noidung','tai_video',{cid},'',true), url = r.url.startsWith('http') ? r.url : location.origin + r.url;
    if(tg?.downloadFile && tg.isVersionAtLeast?.('8.0')){ tg.downloadFile({url, file_name:r.file_name}, ok=>{ if(ok) toast('Đang tải video về máy'); }); }
    else { const a = document.createElement('a'); a.href = url; a.download = r.file_name; document.body.appendChild(a); a.click(); a.remove(); toast('Đang tải video. Nếu không thấy, dùng “Gửi Telegram”.', 3500); }
  }catch(e){ toast(e.message); }
}
async function vSendTg(cid){ try{ const r = await run('noidung','gui_video',{cid},'',true); toast(r.text, 4000); notifyH('success'); }catch(e){ toast(e.message); } }
function vRedo(cid){
  const c = cq().cfg||{}, m = S.cpack?.parts?.reel?.meta||{};
  S.vr = {voice: c.voice||'NamMinh', len: m.len||c.reel_len||60, music: c.music!==false, rewrite:false};
  const paint = () => { const v = S.vr; sheet(`<h2>Dựng lại video</h2><p class="lead">Bản hiện tại được giữ trong “Phiên bản trước”.</p>
    <p class="lbl">Giọng đọc</p><div class="seg" style="margin-bottom:12px"><button class="${v.voice==='NamMinh'?'on':''}" onclick="S.vr.voice='NamMinh';S.vrp()">Giọng nam</button><button class="${v.voice==='HoaiMy'?'on':''}" onclick="S.vr.voice='HoaiMy';S.vrp()">Giọng nữ</button></div>
    <p class="lbl">Độ dài</p><div class="seg" style="margin-bottom:12px">${[30,45,60,90].map(x=>`<button class="${v.len===x?'on':''}" onclick="S.vr.len=${x};S.vrp()">${x} giây</button>`).join('')}</div>
    <label class="pick"><input type="checkbox" ${v.music?'checked':''} onchange="S.vr.music=this.checked"><div class="grow"><div style="font-weight:600">Nhạc nền bản tin</div></div></label>
    <label class="pick"><input type="checkbox" ${v.rewrite?'checked':''} onchange="S.vr.rewrite=this.checked"><div class="grow"><div style="font-weight:600">Viết lại kịch bản</div><div class="meta">Bỏ chọn để giữ kịch bản, chỉ dựng lại hình và giọng</div></div></label>
    <label class="field"><span>Chỉ đạo thêm (khi viết lại)</span><textarea id="vrangle" placeholder="Ví dụ: nhấn mạnh tác động tới seller POD Việt Nam">${esc(v.angle||'')}</textarea></label>
    <button class="btn pri full" onclick="vRedoGo('${cid}')">${ico('refresh')} Dựng lại</button>`); };
  S.vrp = () => { const a = $('#vrangle'); if(a) S.vr.angle = a.value; const y = $('#sheet').scrollTop; paint(); $('#sheet').scrollTop = y; }; paint();
}
async function vRedoGo(cid){
  const v = S.vr; v.angle = $('#vrangle')?.value||'';
  closeSheet(); toast('superHuy đang dựng lại video, khoảng 2-5 phút. Anh cứ dùng app bình thường.', 4500);
  try{ const r = await run('noidung','dung_lai',{cid, voice:v.voice, music:v.music, reel_len:v.len, rewrite:v.rewrite, angle:v.angle},'Dựng lại video'); toast(r.text, 3500); await refresh(); const it = S.cpack?.item?.id; if(it) cPack(it,'reel'); }
  catch(e){ toast(e.message, 5000); }
}

function cSettings(){
  const c = cq().cfg||{};
  S.cset = {topics:[...(c.topics||[])], tin: c.tracks?.tin!==false, founder: c.tracks?.founder!==false, roimaxx: c.tracks?.roimaxx!==false, leversphere: c.tracks?.leversphere!==false, music: c.music!==false, reel_len: c.reel_len||60, style: c.style||'auto', voice: c.voice||'NamMinh', outputs:[...(c.outputs||['reel','group','page'])], fast: c.fast!==false};
  const paint = () => { const s = S.cset; sheet(`<h2>Chủ đề và định dạng</h2>
    <p class="lbl">Tuyến săn tin</p>
    <label class="pick"><input type="checkbox" ${s.tin?'checked':''} onchange="S.cset.tin=this.checked"><div class="grow"><div style="font-weight:600">Tin theo chủ đề</div><div class="meta">Tin nóng theo các chủ đề bên dưới</div></div></label>
    <label class="pick"><input type="checkbox" ${s.founder?'checked':''} onchange="S.cset.founder=this.checked"><div class="grow"><div style="font-weight:600">Founder & startup AI</div><div class="meta">Case thành công: hành trình founder, gọi vốn, định giá, tăng trưởng</div></div></label>
    <label class="pick"><input type="checkbox" ${s.roimaxx?'checked':''} onchange="S.cset.roimaxx=this.checked"><div class="grow"><div style="font-weight:600">Agentic commerce · Roimaxx</div><div class="meta">Mô hình kinh doanh enabler, agents factory, agency chuyển đổi AI, giao thức mới — kèm phân tích CAO</div></div></label>
    <label class="pick"><input type="checkbox" ${s.leversphere?'checked':''} onchange="S.cset.leversphere=this.checked"><div class="grow"><div style="font-weight:600">AI-native · Leversphere</div><div class="meta">Case study, best practice, công cụ AI cho công ty POD — kèm phân tích CAO</div></div></label>
    <p class="lbl" style="margin-top:12px">Chủ đề (${s.topics.length})</p>
    <div class="chips" style="padding-top:0;flex-wrap:wrap;margin-bottom:8px">${s.topics.map((t,i)=>`<button class="chip rm" onclick="S.cset.topics.splice(${i},1);S.cspaint()" aria-label="Bỏ chủ đề ${esc(t)}">${esc(t)} ${ico('x',14)}</button>`).join('')}</div>
    <div class="row" style="margin-bottom:14px"><input id="tnew" class="grow" placeholder="Thêm chủ đề, ví dụ: AI agent cho ecommerce" style="padding:11px 13px;border-radius:12px;border:0;background:var(--fill);color:var(--text);font:inherit">
      <button class="btn" onclick="const v=$('#tnew').value.trim();if(v){S.cset.topics.push(v);S.cspaint()}">${ico('plus')} Thêm</button></div>
    <p class="lbl">Mặc định khi quẹt phải</p>
    <div class="seg" style="margin-bottom:10px">${[30,45,60,90].map(x=>`<button class="${s.reel_len===x?'on':''}" onclick="S.cset.reel_len=${x};S.cspaint()">${x} giây</button>`).join('')}</div>
    <div class="chips" style="padding-top:0;flex-wrap:wrap;margin-bottom:10px">${Object.entries(CSTYLE).map(([k,l])=>`<button class="chip ${s.style===k?'on':''}" onclick="S.cset.style='${k}';S.cspaint()">${l}</button>`).join('')}</div>
    <div class="chips" style="padding-top:0;flex-wrap:wrap;margin-bottom:10px">${Object.entries(COUT).map(([k,l])=>`<button class="chip ${s.outputs.includes(k)?'on':''}" onclick="S.cset.outputs=S.cset.outputs.includes('${k}')?S.cset.outputs.filter(o=>o!=='${k}'):[...S.cset.outputs,'${k}'];S.cspaint()">${l}</button>`).join('')}</div>
    <div class="seg" style="margin-bottom:10px"><button class="${s.voice==='NamMinh'?'on':''}" onclick="S.cset.voice='NamMinh';S.cspaint()">Giọng nam</button><button class="${s.voice==='HoaiMy'?'on':''}" onclick="S.cset.voice='HoaiMy';S.cspaint()">Giọng nữ</button></div>
    <label class="pick"><input type="checkbox" ${s.fast?'checked':''} onchange="S.cset.fast=this.checked"><div class="grow"><div style="font-weight:600">Nhịp nhanh kiểu reels</div><div class="meta">Đọc nhanh hơn, cắt khoảng lặng giữa cảnh để giữ người xem</div></div></label>
    <label class="pick"><input type="checkbox" ${s.music?'checked':''} onchange="S.cset.music=this.checked"><div class="grow"><div style="font-weight:600">Nhạc nền bản tin</div><div class="meta">Nhạc nhịp tin tức tự né khi có giọng đọc</div></div></label>
    <div class="note" style="margin-top:8px">Video được dựng như một bản tin: hook 3 giây đầu, đồ hoạ dữ liệu (con số, so sánh, dòng thời gian, trích dẫn), ảnh minh hoạ thật, phụ đề sáng theo giọng đọc, góc nhìn chuyên gia và câu hỏi cuối. Link nguồn để ở comment đầu.</div>
    <button class="btn pri full" id="csave">Lưu</button>`);
    $('#csave').onclick = async ()=>{ const s = S.cset;
      if(!s.outputs.length) return toast('Chọn ít nhất một đầu ra');
      try{ const r = await run('noidung','caidat',{topics:s.topics.join(','), tin:s.tin, founder:s.founder, roimaxx:s.roimaxx, leversphere:s.leversphere, music:s.music, reel_len:s.reel_len, style:s.style, voice:s.voice, outputs:s.outputs.join(','), fast:s.fast},'',true);
        S.data.cq.cfg = r.cfg; closeSheet(); toast('Đã lưu chủ đề và định dạng'); }catch(e){ toast(e.message); } };
  };
  S.cspaint = () => { const t = $('#tnew')?.value||''; const y = $('#sheet').scrollTop; paint(); $('#sheet').scrollTop = y; if($('#tnew')) $('#tnew').value = t.trim()&&S.cset.topics.includes(t.trim())?'':t; }; paint();
}
async function cPack(iid, part){
  let d; try{ d = await run('noidung','bo',{iid},'',true); }catch(e){ return toast(e.message); }
  S.cpack = d; const parts = d.parts||{}, keys = ['reel','group','page'].filter(k=>parts[k]);
  if(!keys.length) return toast('Bộ nội dung này không còn trong thư viện');
  part = keys.includes(part) ? part : keys[0];
  if(part==='reel') return studioOpen(parts.reel.id, iid);
  const c = parts[part], m = c.meta||{};
  sheet(`<div class="meta" style="margin-bottom:4px">${esc(TRK[d.item.track]||'')} · ${esc(CSTYLE[m.style]||'')}</div><h2 style="margin-bottom:12px">${esc(d.item.headline_vi)}</h2>
    <div class="seg" style="margin-bottom:14px">${keys.map(k=>`<button class="${k===part?'on':''}" onclick="cPack('${iid}','${k}')">${k==='reel'?'Reel Studio':COUT[k]}</button>`).join('')}</div>
    ${c.video?vPlayer(c):''}
    ${part!=='reel'&&c.image?`<img class="media" src="${c.image}" alt="">`:''}
    <label class="field"><span>${part==='reel'?'Caption đăng kèm':'Nội dung bài'}, sửa trực tiếp</span><textarea id="ctext" style="min-height:${part==='reel'?120:240}px">${esc(c.text)}</textarea></label>
    <div class="row" style="margin:-4px 0 12px"><button class="btn" onclick="saveEdit('${c.id}')">${ico('check')} Lưu sửa</button><button class="btn" onclick="copyText($('#ctext').value)">${ico('copy')} Sao chép</button></div>
    ${m.first_comment?`<p class="lbl">Comment đầu tiên (chứa link nguồn, để bài không bị giảm phân phối)</p><div class="card out" style="margin-bottom:8px">${esc(m.first_comment)}</div><button class="btn" style="margin-bottom:12px" onclick="copyText(S.cpack.parts['${part}'].meta.first_comment)">${ico('copy')} Sao chép comment</button>`:''}
    ${m.reel?`<details style="margin-bottom:12px"><summary>Kịch bản reels</summary><div class="card out">${esc(m.reel)}</div></details>`:''}
    ${part==='reel'&&(m.versions||[]).length?`<details style="margin-bottom:12px"><summary>Phiên bản trước (${m.versions.length})</summary>${m.versions.slice().reverse().map(v=>`<div class="row" style="align-items:center;margin:8px 0"><span class="grow meta" style="margin:0">${esc((v.at||'').slice(11,16)+' '+(v.at||'').slice(8,10)+'/'+(v.at||'').slice(5,7))}${v.duration?' · '+Math.round(v.duration)+' giây':''}</span>${v.video?`<button class="btn sm" onclick="vPlayVer('${v.video}')">${ico('play',14)} Xem</button>`:''}</div>`).join('')}</details>`:''}
    <button class="btn pri full" onclick="openPublish('${c.id}')">${ico('send')} Đăng lên…</button>`);
}

/* ---------- Thêm */
function vMore(){
  const con = S.data.connections||[], ags = (S.data.agents||[]);
  return `
  <div class="date">Mọi tiện ích, kết nối và cài đặt</div><h1>Tất cả</h1>
  <div class="apps">${appsGrid().replace(/<button onclick="go\('more'\)"[\s\S]*?<\/button>/,'')}</div>
  <div class="sec" style="margin-top:6px"><h2>Kết nối</h2></div>
  <div class="card list">${con.map(c=>`<button onclick="openAction('${c.action[0]}','${c.action[1]}')"><span class="st ${c.ok?'ok':'no'}"></span><div class="grow"><div style="font-weight:600">${esc(c.name)}</div><div class="meta">${esc(c.detail)}</div></div><span class="chev">${ico('chev',18)}</span></button>`).join('')}</div>
  <div class="sec"><h2>Công cụ của các agent</h2></div>
  <div class="card list">${ags.map(a=>`<button onclick="openAgent('${a.id}')"><span class="thumb">${ico(AGENT_ICON[a.id]||'spark',20)}</span><div class="grow"><div style="font-weight:600">${esc(a.name)}</div><div class="meta">${esc(a.desc)}</div></div><span class="chev">${ico('chev',18)}</span></button>`).join('')}</div>
  <div class="sec"><h2>Nơi đăng</h2></div>
  <div class="card list">${(S.data.targets||[]).map(t=>`<button onclick="openLink('${esc(t.url||'')}')"><span class="thumb">${ico(t.type==='page'?'news':t.type==='group'?'chat':'home',20)}</span><div class="grow"><div style="font-weight:600">${esc(t.name)}</div><div class="meta">${t.auto?'Đăng tự động':'Sao chép rồi mở trang để dán'}</div></div><span class="chev">${ico('chev',18)}</span></button>`).join('')}</div>
  <div class="sec"><h2>Bảo mật</h2></div>
  <div class="card list"><button onclick="go('me')"><span class="thumb">${ico('users',20)}</span><div class="grow"><div style="font-weight:600">Hồ sơ, Face ID / vân tay, giao diện</div><div class="meta">Không gian của tôi.</div></div><span class="chev">${ico('chev',18)}</span></button>
    <button onclick="lockNow(true)"><span class="thumb">${ico('lock',20)}</span><div class="grow"><div style="font-weight:600">Khóa ngay</div><div class="meta">Đăng xuất app và khóa super bot. Mở lại bằng mã PIN.</div></div></button>
    <button onclick="openQC()"><span class="thumb">${ico('check',20)}</span><div class="grow"><div style="font-weight:600">Tình trạng hệ thống</div><div class="meta">QC tự kiểm tra 5 phút/lần và nhắn bạn ngay khi có lỗi.</div></div><span class="chev">${ico('chev',18)}</span></button>
    <button onclick="openAction('caidat','doipin')"><span class="thumb">${ico('gear',20)}</span><div class="grow"><div style="font-weight:600">Đổi mã PIN</div><div class="meta">Chỉ tài khoản Telegram của bạn mở được app. App tự khóa khi không dùng 10 phút.</div></div><span class="chev">${ico('chev',18)}</span></button></div>
  <p class="muted small" style="margin:18px 4px">Giọng đọc video: ${esc(S.data.settings?.voice||'NamMinh')}. Đổi trong Công cụ › Cài đặt.</p>`;
}


