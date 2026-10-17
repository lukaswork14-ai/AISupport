/* ---------- sheet */
function sheet(html){ $('#sheetBody').innerHTML = html; $('#scrim').classList.add('on'); $('#sheet').classList.add('on'); $('#sheet').scrollTop = 0; tg?.BackButton?.show(); }
function closeSheet(){ $('#sheet').classList.remove('on'); $('#scrim').classList.remove('on'); tg?.BackButton?.hide(); document.querySelectorAll('#sheet video').forEach(v=>v.pause()); }
$('#scrim').onclick = closeSheet; tg?.BackButton?.onClick(closeSheet);

function resultHtml(r){
  if(!r) return '';
  let h = '';
  if(r.image) h += `<img class="media" src="${r.image}" alt="">`;
  if(r.video) h += `<video class="media" src="${r.video}" controls playsinline></video>`;
  if(r.text) h += `<div class="card out">${esc(r.text)}</div>`;
  if(r.open_url) h += `<button class="btn pri full" style="margin-top:12px" onclick="openLink('${esc(r.open_url)}')">${ico('link')} Mở trang cho phép</button>`;
  if(r.content_id) h += `<button class="btn pri full" style="margin-top:12px" onclick="openContent('${r.content_id}')">Mở trong Studio</button>`;
  return h;
}
function openAgent(id){
  const a = (S.data.agents||[]).find(x=>x.id===id); if(!a) return;
  sheet(`<h2>${esc(a.name)}</h2><p class="lead">${esc(a.desc)}</p>
    <div class="card list">${a.actions.map(x=>`<button onclick="openAction('${a.id}','${x.id}')"><div class="grow"><div style="font-weight:600">${esc(x.label)}</div>${x.desc?`<div class="meta">${esc(x.desc)}</div>`:''}</div><span class="chev">${ico('chev',18)}</span></button>`).join('') || '<div class="empty">Agent này chạy tự động, chưa có thao tác tay.</div>'}</div>`);
}
async function openQC(){
  sheet(`<h2>Tình trạng hệ thống</h2><p class="lead">Đang kiểm tra máy chủ, link app và các kết nối…</p><div class="card pad"><div class="skel" style="width:60%"></div><div class="skel"></div><div class="skel" style="width:80%"></div></div>`);
  try{
    const r = await run('caidat','tinhtrang',{},'Kiểm tra hệ thống');
    if(!document.querySelector('#sheet.on')) return;
    const t = x => x.at ? new Date(x.at*1000).toLocaleTimeString('vi-VN',{hour:'2-digit',minute:'2-digit'}) : '';
    sheet(`<h2>Tình trạng hệ thống</h2><p class="lead">${esc(r.text||'')}</p>
      <div class="card list">${(r.items||[]).map(x=>`<div class="row" style="padding:12px 14px;align-items:flex-start;flex-wrap:nowrap"><span style="width:10px;height:10px;border-radius:50%;margin-top:6px;flex:none;background:${x.ok?'var(--jade)':'#e5484d'}"></span><div class="grow"><div style="font-weight:600">${esc(x.name)}</div><div class="meta">${x.ok?'Ổn định':esc(x.detail)} · ${t(x)}</div></div></div>`).join('')}</div>`);
  }catch(e){ sheet(`<h2>Tình trạng hệ thống</h2><p class="lead">${esc(e.message)}</p>`); }
}
function openAction(agentId, actionId){
  const a = (S.data.agents||[]).find(x=>x.id===agentId); const x = a?.actions.find(y=>y.id===actionId);
  if(!x){ toast('Không tìm thấy công cụ'); return; }
  const field = p => {
    const v = p.default ?? '';
    if(p.type==='select') return `<select name="${p.name}">${(p.options||[]).map(o=>{const val=o.value??o, lab=o.label??(o||'Tất cả'); return `<option value="${esc(val)}" ${val==v?'selected':''}>${esc(lab)}</option>`}).join('')}</select>`;
    if(p.type==='textarea') return `<textarea name="${p.name}" placeholder="${esc(p.hint||'')}">${esc(v)}</textarea>`;
    if(p.type==='bool') return `<input type="checkbox" name="${p.name}" ${v?'checked':''} style="width:22px;height:22px;accent-color:var(--jade)">`;
    if(p.type==='password') return `<input type="password" autocomplete="off" name="${p.name}" placeholder="${esc(p.hint||'')}">`;
    return `<input type="${p.type==='number'?'number':'text'}" name="${p.name}" value="${esc(v)}" placeholder="${esc(p.hint||'')}" autocapitalize="off" autocorrect="off" spellcheck="false">`;
  };
  sheet(`<h2>${esc(x.label)}</h2>${x.desc?`<p class="lead">${esc(x.desc)}</p>`:'<div style="height:12px"></div>'}
    <form id="af">${x.params.map(p=>`<label class="field"><span>${esc(p.label)}${p.required?' *':''}</span>${field(p)}</label>`).join('')}
    <button class="btn pri full" type="submit">Chạy</button></form><div id="aout"></div>`);
  $('#af').onsubmit = async e => {
    e.preventDefault();
    const fd = new FormData(e.target), params = {};
    x.params.forEach(p => { params[p.name] = p.type==='bool' ? !!e.target[p.name].checked : fd.get(p.name); });
    const b = e.target.querySelector('button[type=submit]'); b.disabled = true; b.innerHTML = '<span class="spin"></span> Đang chạy';
    try{ const r = await run(agentId, actionId, params, x.label); $('#aout').innerHTML = resultHtml(r); refresh().catch(()=>{}); }
    catch(err){ $('#aout').innerHTML = `<div class="card out" style="color:var(--danger)">${esc(err.message)}</div>`; }
    b.disabled = false; b.textContent = 'Chạy lại';
  };
}
function openContent(id){
  const c = (S.data.contents||[]).find(x=>x.id===id); if(!c) return toast('Không tìm thấy nội dung');
  const k = KIND[c.kind]||[c.kind,'save'];
  const posts = (c.posts||[]).map(p=>{ const t=(S.data.targets||[]).find(x=>x.id===p.target); return `<div class="meta">${esc(t?.name||p.target)}: ${p.mode==='api'?'đã đăng':'đã mở để dán'} lúc ${esc((p.at||'').slice(11,16))}</div>`; }).join('');
  sheet(`<div class="meta" style="margin-bottom:4px">${k[0]}</div><h2 style="margin-bottom:14px">${esc(c.title)}</h2>
    ${c.video?`<video class="media" src="${c.video}" controls playsinline></video>`:''}
    ${c.image?`<img class="media" src="${c.image}" alt="">`:''}
    <label class="field"><span>Nội dung, sửa trực tiếp</span><textarea id="ctext" style="min-height:220px">${esc(c.text)}</textarea></label>
    ${c.meta?.reel?`<details><summary>Kịch bản reels</summary><div class="card out">${esc(c.meta.reel)}</div></details>`:''}
    <div class="row" style="margin:6px 0 12px">
      <button class="btn" onclick="saveEdit('${c.id}')">${ico('check')} Lưu sửa</button>
      <button class="btn" onclick="copyText($('#ctext').value)">${ico('copy')} Sao chép</button>
      <button class="btn" onclick="act.obsidian('${c.id}')">${ico('brain')} Obsidian</button>
    </div>
    ${c.meta?.reel_data?`<button class="btn full" style="margin-bottom:8px" onclick="act.videoBai('${c.id}')">${ico('film')} Dựng video reels từ kịch bản</button>`:''}
    <button class="btn pri full" onclick="openPublish('${c.id}')">${ico('send')} Đăng lên…</button>
    ${posts?`<div class="sec"><h2 style="font-size:15px">Đã đăng ở</h2></div>${posts}`:''}`);
}
async function saveEdit(id){ try{ await run('studio','sua',{content_id:id, text:$('#ctext').value}); toast('Đã lưu sửa'); refresh(); }catch(e){ toast(e.message); } }
function openPublish(id){
  const c = (S.data.contents||[]).find(x=>x.id===id);
  const txt = $('#ctext')?.value; if(txt && txt!==c.text){ run('studio','sua',{content_id:id, text:txt}).then(refresh); c.text = txt; }
  S.pubText = c.text;
  sheet(`<h2>Đăng “${esc(c.title)}”</h2><p class="lead">Page có token sẽ đăng tự động. Group và trang cá nhân: app sao chép nội dung rồi mở đúng trang để bạn dán.</p>
    ${(S.data.targets||[]).map(t=>`<label class="pick"><input type="checkbox" value="${t.id}" ${(t.default_for||[]).includes(c.kind)?'checked':''}>
      <div class="grow"><div style="font-weight:600">${esc(t.name)}</div><div class="meta">${t.auto?'Đăng tự động':'Sao chép rồi mở trang'}</div></div></label>`).join('')}
    <button class="btn pri full" id="pubBtn" style="margin-top:6px">Đăng</button><div id="pubOut" style="margin-top:12px"></div>`);
  $('#pubBtn').onclick = async ()=>{
    const ids = [...document.querySelectorAll('#sheet .pick input:checked')].map(i=>i.value);
    if(!ids.length) return toast('Chọn ít nhất một nơi đăng');
    $('#pubBtn').disabled = true;
    try{
      const r = await run('dang','dang',{content_id:id, targets:ids.join(',')}, 'Đăng bài');
      $('#pubOut').innerHTML = `<div class="card list">${(r.items||[]).map(x=>`<div><div class="grow"><div style="font-weight:600">${esc(x.name)}</div><div class="meta">${x.mode==='api'?(x.ok?'Đã đăng':esc(x.error)):'Ảnh và nội dung đã gửi vào chat Telegram'}</div></div>${
        x.mode==='manual'?`<button class="btn pri" onclick="copyText(S.pubText);openLink('${esc(x.url)}')">Sao chép và mở</button>`:x.link?`<button class="btn" onclick="openLink('${esc(x.link)}')">Xem</button>`:''}</div>`).join('')}</div>`;
      refresh();
    }catch(e){ $('#pubOut').innerHTML = `<div class="card out" style="color:var(--danger)">${esc(e.message)}</div>`; }
    $('#pubBtn').disabled = false;
  };
}

/* ---------- thao tác nhanh */
const act = {
  async scan(){ toast('Agent săn tin đang quét, khoảng 40 giây'); try{ await run('tin','top',{refresh:true},'Quét tin hot'); await refresh(); toast('Đã có 5 tin mới'); }catch(e){ toast(e.message); } },
  async bantin(){ try{ const r = await run('studio','bantin',{},'Tạo ảnh bản tin'); await refresh(); openContent(r.content_id); }catch(e){ toast(e.message); } },
  async video(){ toast('Đang dựng video bản tin, 1–2 phút'); try{ const r = await run('studio','video',{},'Dựng video bản tin'); await refresh(); openContent(r.content_id); }catch(e){ toast(e.message); } },
  write(n){
    sheet(`<h2>Viết bài cho tin số ${n}</h2><p class="lead">Agent viết bài đăng, ảnh minh họa và kịch bản reels theo văn phong của bạn.</p>
      <label class="field"><span>Góc nhìn hoặc lưu ý thêm (không bắt buộc)</span><textarea id="angle" placeholder="Ví dụ: nhấn mạnh cơ hội cho seller POD"></textarea></label>
      <button class="btn pri full" id="wBtn">${ico('pen')} Viết bài</button>`);
    $('#wBtn').onclick = async ()=>{ const angle = $('#angle').value; closeSheet(); toast('Đang viết bài, khoảng 30–60 giây');
      try{ const r = await run('studio','viet',{n, angle},'Viết bài tin số '+n); await refresh(); openContent(r.content_id); }catch(e){ toast(e.message); } };
  },
  async videoBai(id){ closeSheet(); toast('Đang dựng video reels, khoảng 1 phút'); try{ const r = await run('studio','video_bai',{content_id:id},'Dựng video reels'); await refresh(); openContent(r.content_id); }catch(e){ toast(e.message); } },
  async saveNews(n){ try{ const r = await run('tin','luu',{n}); toast('Đã lưu vào Obsidian'); }catch(e){ toast(e.message); } },
  async obsidian(id){ try{ await run('studio','obsidian',{content_id:id}); toast('Đã lưu vào Obsidian'); }catch(e){ toast(e.message); } },
};

/* ---------- lời mời họp */
S.inv = null;
function invOn(){ const c = Object.fromEntries((S.data.connections||[]).map(x=>[x.id, x.ok])); return !!(c.gcal_write || c.larkcal); }
function dayLabel(iso){ const d = new Date(iso+'T00:00:00'), t = new Date(); t.setHours(0,0,0,0);
  const diff = Math.round((d - t)/86400000); if(diff===0) return 'Hôm nay'; if(diff===1) return 'Ngày mai';
  return ['CN','T2','T3','T4','T5','T6','T7'][d.getDay()] + ' ' + d.getDate() + '/' + (d.getMonth()+1); }
function invSection(){
  if(!invOn()) return '';
  const inv = S.inv, n = inv?.items?.length||0;
  const head = `<div class="sec"><h2>Lời mời họp${n?` <span class="tag mid" style="vertical-align:3px;margin-left:4px">${n} chờ duyệt</span>`:''}</h2></div>`;
  if(!inv) return head + `<div class="card" id="inv"><div class="tl"><div class="skel" style="width:65%"></div></div></div>`;
  if(!n) return head + `<div class="card empty" id="inv">Không có lời mời họp nào đang chờ bạn trả lời.</div>`;
  return head + `<div class="card" id="inv">${inv.items.map((v,i)=>`<div class="inv" id="inv${i}"><div class="d"><b>${esc(dayLabel(v.date))}</b><span>${esc(v.time)}</span></div>
    <div class="grow"><div class="t">${esc(v.title)}</div><div class="meta">${v.source==='lark'?'Lark':'Google'}${v.organizer?' · '+esc(v.organizer):''}${v.status==='maybe'?' · đang “có thể”':''}</div>
    ${v.conflicts?.length?`<div class="warn">Trùng với: ${esc(v.conflicts.join(', '))}</div>`:''}
    <div class="rs"><button class="btn sm" onclick="rsvp(${i},'no')">Từ chối</button><button class="btn sm" onclick="rsvp(${i},'maybe')">Có thể</button><button class="btn sm pri" onclick="rsvp(${i},'yes')">${ico('check',16)} Đồng ý</button></div></div></div>`).join('')}</div>`;
}
async function loadInv(force){
  if(!invOn() || S.invLoading) return;
  if(S.inv && Date.now() - S.inv.at < (force ? 20000 : 5*60*1000)) return;
  S.invLoading = true;
  try{ const r = await run('lich','loimoi',{},'',true); S.inv = {items:r.items||[], at:Date.now()}; }
  catch(e){ S.inv = {items:[], at:Date.now()}; }
  S.invLoading = false;
  if(S.tab==='home' && !document.querySelector('#sheet.on')){ const el = $('#invWrap'); if(el) el.innerHTML = invSection(); }
}
async function rsvp(i, st){
  const v = S.inv.items[i]; if(!v) return;
  haptic(st==='yes'?'medium':'light');
  const el = $('#inv'+i); el?.classList.add('gone');
  try{ const r = await run('lich','traloi',{source:v.source, event_id:v.id, status:st},'Trả lời lời mời');
    S.inv.items = S.inv.items.filter(x=>x!==v); S.cal = {}; toast(r.text); notifyH('success'); render(); }
  catch(e){ el?.classList.remove('gone'); toast(e.message); }
}

/* ---------- khóa PIN */
const LOCK = { len:6, buf:'', pre:'', busy:false, resolve:null };
function lockOn(){ return document.body.classList.contains('locked'); }
function paintDots(){ $('#dots').innerHTML = Array.from({length:LOCK.len}, (_,i)=>`<i class="${i<LOCK.buf.length?'on':''}"></i>`).join(''); }
function setSub(t, err){ const e = $('#lockSub'); e.textContent = t; e.classList.toggle('err', !!err); }
function showLock(a){
  LOCK.len = a.pin_len||6; LOCK.pre = a.pre; LOCK.buf = ''; LOCK.busy = false;
  try{ closeSheet(); }catch(e){}
  $('#lockMark').innerHTML = '<img class="brandimg" src="/icons/huy-192.png?v=3" alt="">';
  $('#keys').innerHTML = [1,2,3,4,5,6,7,8,9].map(n=>`<button data-k="${n}" aria-label="Số ${n}">${n}</button>`).join('')
    + `${IN_TG?'<button class="ghost" data-k="x">Đóng</button>':'<span></span>'}<button data-k="0" aria-label="Số 0">0</button><button class="ghost" data-k="del" aria-label="Xóa">${ico('del',26)}</button>`;
  $('#keys').querySelectorAll('button:not(.ghost)').forEach(b => b.insertAdjacentHTML('beforeend','<span class="rip"></span>'));
  $('#lockHint').innerHTML = (!IN_TG && !STANDALONE && /iPhone|iPad/.test(navigator.userAgent)) ? `Cài lên iPhone: trong Safari bấm <b>Chia sẻ</b> rồi <b>Thêm vào Màn hình chính</b>. Lần sau chỉ cần mở biểu tượng superHuy và nhập PIN.` : '';
  paintDots();
  setSub(a.wait ? `Tạm khóa do nhập sai nhiều lần. Thử lại sau ${Math.ceil(a.wait/60)} phút.` : 'Nhập mã PIN để mở', !!a.wait);
  document.body.classList.add('locked');
  const pkOk = !IN_TG && window.PublicKeyCredential && lsGet('sy_pk')==='1';
  $('#lockPk').hidden = !pkOk;
  if(pkOk && !a.wait) setTimeout(()=>{ if(lockOn() && !LOCK.buf) pkLogin(); }, 350);
  return new Promise(r => LOCK.resolve = r);
}
function lsGet(k){ try{ return localStorage.getItem(k); }catch(e){ return null; } }
function lsSet(k,v){ try{ v==null ? localStorage.removeItem(k) : localStorage.setItem(k,v); }catch(e){} }
const b64u = { enc: b => btoa(String.fromCharCode(...new Uint8Array(b))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=+$/,''), dec: s => Uint8Array.from(atob(s.replace(/-/g,'+').replace(/_/g,'/') + '==='.slice((s.length+3)%4)), c=>c.charCodeAt(0)) };
async function pkLogin(){
  if(LOCK.busy || !lockOn()) return; LOCK.busy = true; setSub('Xác nhận bằng Face ID / vân tay…');
  try{
    const o = await api('/api/passkey/login/options');
    const pk = o.publicKey; pk.challenge = b64u.dec(pk.challenge); pk.allowCredentials = (pk.allowCredentials||[]).map(c=>({...c, id:b64u.dec(c.id)}));
    const cred = await navigator.credentials.get({publicKey: pk});
    const r = await api('/api/passkey/login', {id: cred.id, clientDataJSON: b64u.enc(cred.response.clientDataJSON), authenticatorData: b64u.enc(cred.response.authenticatorData), signature: b64u.enc(cred.response.signature), device: deviceId()});
    S.tok = r.session; notifyH('success'); S.enter = true; document.body.classList.add('unlocking'); document.body.classList.remove('locked');
    setTimeout(()=>document.body.classList.remove('unlocking'), 520); LOCK.busy = false; LOCK.resolve?.(r.session); return;
  }catch(e){ setSub(/NotAllowed|AbortError|timed out/i.test(String(e.name||e.message)) ? 'Nhập mã PIN để mở' : (e.message||'Không đăng nhập được, nhập PIN'), false); }
  LOCK.busy = false;
}
async function pkRegister(){
  const name = ($('#pkName')?.value||'').trim() || ((/iPhone/.test(navigator.userAgent)?'iPhone':/iPad/.test(navigator.userAgent)?'iPad':/Macintosh/.test(navigator.userAgent)?'Mac':/Android/.test(navigator.userAgent)?'Android':'Máy tính') + ' của ' + (S.first||'tôi'));
  try{
    if(!window.PublicKeyCredential) throw new Error('Trình duyệt này chưa hỗ trợ passkey');
    const o = await api('/api/passkey/register/options', {name: S.first||'Huy'});
    const pk = o.publicKey; pk.challenge = b64u.dec(pk.challenge); pk.user.id = b64u.dec(pk.user.id); pk.excludeCredentials = (pk.excludeCredentials||[]).map(c=>({...c, id:b64u.dec(c.id)}));
    const cred = await navigator.credentials.create({publicKey: pk});
    const r = await api('/api/passkey/register', {clientDataJSON: b64u.enc(cred.response.clientDataJSON), attestationObject: b64u.enc(cred.response.attestationObject), name});
    lsSet('sy_pk','1'); toast(r.text, 4500); notifyH('success'); S.me=null; meLoad();
  }catch(e){ toast(/NotAllowed|AbortError/i.test(String(e.name||'')) ? 'Anh đã huỷ' : e.message, 4500); }
}
async function pinKey(k){
  if(LOCK.busy || !lockOn()) return;
  if(k==='x'){ try{ tg?.close(); }catch(e){} return; }
  if(k==='del'){ LOCK.buf = LOCK.buf.slice(0,-1); paintDots(); return; }
  if(LOCK.buf.length >= LOCK.len) return;
  LOCK.buf += k; haptic('light'); paintDots();
  const kb = $('#keys').querySelector(`button[data-k="${k}"]`); if(kb){ kb.classList.remove('hit'); void kb.offsetWidth; kb.classList.add('hit'); }
  if(LOCK.buf.length < LOCK.len) return;
  LOCK.busy = true; setSub('Đang kiểm tra…');
  try{
    let r;
    const body = () => ({pre:LOCK.pre, pin:LOCK.buf, app:!IN_TG, device:deviceId()});
    try{ r = await api('/api/pin', body()); }
    catch(e){ if(!/hết hạn/i.test(e.message)) throw e;  // vé tạm hết hạn (để app mở lâu): xin vé mới rồi thử lại 1 lần
      const a = await authStart(); LOCK.pre = a.pre; r = await api('/api/pin', body()); }
    if(r.ok){ S.tok = r.session; LOCK.buf=''; notifyH('success'); S.enter = true;
      document.body.classList.add('unlocking'); document.body.classList.remove('locked');
      setTimeout(()=>document.body.classList.remove('unlocking'), 520); LOCK.resolve?.(r.session); return; }
    notifyH('error'); const d = $('#dots'); d.classList.remove('shake'); void d.offsetWidth; d.classList.add('shake');
    LOCK.buf = ''; setTimeout(paintDots, 200); setSub(r.msg || 'Sai mã PIN', true);
  }catch(e){ LOCK.buf=''; paintDots(); setSub(e.message, true); }
  LOCK.busy = false;
}
$('#keys').addEventListener('click', e => { const b = e.target.closest('button[data-k]'); if(b) pinKey(b.dataset.k); });
document.addEventListener('keydown', e => { if(!lockOn()) return; if(/^\d$/.test(e.key)) pinKey(e.key); else if(e.key==='Backspace') pinKey('del'); });
function deviceId(){ try{ let d = localStorage.getItem('sh_dev'); if(!d){ d = (crypto.randomUUID?.() || String(Math.random()).slice(2)) ; localStorage.setItem('sh_dev', d); } return d; }catch(e){ return ''; } }
const authStart = () => IN_TG ? api('/api/auth', {initData: tg.initData}) : api('/api/app/hello', {});
async function unlockFlow(){
  try{ const t = sessionStorage.getItem('sh_tok'); if(t && !IN_TG){ S.tok = t; await api('/api/bootstrap'); sessionStorage.removeItem('sh_tok'); return; } }catch(e){ S.tok = null; }
  const a = await authStart();
  S.first = a.user?.first_name || S.first;
  if(a.need_pin) await showLock(a); else S.tok = a.session;
}
let relocking = false;
async function relock(){
  if(relocking || lockOn()) return; relocking = true; S.tok = null;
  try{ await unlockFlow(); S.data = await api('/api/bootstrap'); S.inv = null; render(); }
  catch(e){ $('#app').innerHTML = `<div class="center"><div><p style="font-weight:600;color:var(--text)">Chưa mở được app</p><p>${esc(e.message)}</p></div></div>`; document.body.classList.remove('locked'); }
  relocking = false;
}
async function lockNow(server){
  if(server){ try{ await api('/api/lock', {}); }catch(e){} }
  S.tok = null; relock();
}
// tự khóa: không thao tác 10 phút, hoặc rời app quá 3 phút
const IDLE_MS = 10*60*1000, AWAY_MS = 3*60*1000; let lastAct = Date.now(), hiddenAt = 0;
['pointerdown','keydown','touchstart'].forEach(ev => addEventListener(ev, ()=>{ lastAct = Date.now(); }, {passive:true}));
setInterval(()=>{ if(S.tok && !lockOn() && Date.now() - lastAct > IDLE_MS) lockNow(false); }, 30000);
document.addEventListener('visibilitychange', ()=>{
  if(document.hidden){ hiddenAt = Date.now(); return; }
  if(S.tok && !lockOn() && hiddenAt && Date.now() - hiddenAt > AWAY_MS) lockNow(false);
});

/* ---------- lịch tự cập nhật real-time khi app đang mở */
setInterval(()=>{
  if(document.hidden || lockOn() || !S.tok || S.tab!=='home' || document.querySelector('#sheet.on')) return;
  loadCal(true); loadInv(true);
}, 60000);
document.addEventListener('visibilitychange', ()=>{ if(!document.hidden && S.tok && !lockOn() && S.tab==='home'){ loadCal(true); loadInv(true); } });

/* ---------- tương tác kiểu iOS: kéo tấm trượt xuống để đóng, kéo trang xuống để làm mới */
(function(){
  const sh = $('#sheet'); let y0 = null, dy = 0, t0 = 0;
  const start = e => { const fromGrab = e.target.closest('.grab'); if(!fromGrab && sh.scrollTop > 0) return; y0 = e.touches[0].clientY; dy = 0; t0 = Date.now(); };
  const move = e => { if(y0 === null) return; dy = e.touches[0].clientY - y0; if(dy <= 0 || (sh.scrollTop > 0 && !e.target.closest('.grab'))){ dy = 0; return; }
    sh.classList.add('drag'); sh.style.transform = `translateY(${dy < 0 ? 0 : dy * (dy > 140 ? .8 : 1)}px)`; $('#scrim').style.opacity = Math.max(0, 1 - dy / 400); if(e.cancelable) e.preventDefault(); };
  const end = () => { if(y0 === null) return; const v = dy / Math.max(1, Date.now() - t0); y0 = null; sh.classList.remove('drag'); sh.style.transform = ''; $('#scrim').style.opacity = '';
    if(dy > 120 || (dy > 40 && v > .6)){ haptic('light'); closeSheet(); } };
  sh.addEventListener('touchstart', start, {passive:true}); sh.addEventListener('touchmove', move, {passive:false}); sh.addEventListener('touchend', end); sh.addEventListener('touchcancel', end);
})();
(function(){
  if(IN_TG) return;  // Telegram tự có cử chỉ riêng
  const p = $('#ptr'); p.innerHTML = ico('refresh', 20); let y0 = null, d = 0, busy = false;
  addEventListener('touchstart', e => { if(window.scrollY > 0 || busy || lockOn() || $('#sheet').classList.contains('on') || S.tab==='chat') return; y0 = e.touches[0].clientY; d = 0; }, {passive:true});
  addEventListener('touchmove', e => { if(y0 === null) return; d = Math.max(0, e.touches[0].clientY - y0); const k = Math.min(1, d / 90);
    p.style.transition = 'none'; p.style.opacity = k; p.style.transform = `translateY(${Math.min(70, d * .6) - 50}px) rotate(${d * 3}deg)`; }, {passive:true});
  addEventListener('touchend', async () => { if(y0 === null) return; y0 = null; p.style.transition = 'transform .35s var(--spring), opacity .3s';
    if(d < 90){ p.style.opacity = 0; p.style.transform = 'translateY(-70px)'; return; }
    busy = true; p.classList.add('spin'); p.style.transform = 'translateY(14px)';
    try{ await refresh(); S.cl = S.rp = S.lr = null; toast('Đã cập nhật'); }catch(e){ toast(e.message); }
    p.classList.remove('spin'); p.style.opacity = 0; p.style.transform = 'translateY(-70px)'; busy = false; });
})();

/* ---------- khởi động */
(async function boot(){
  try{
    tg?.ready(); tg?.expand();
    document.documentElement.dataset.scheme = tg?.colorScheme || (matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');
    tg?.onEvent?.('themeChanged', ()=>{ document.documentElement.dataset.scheme = tg.colorScheme; });
    try{ const dk = document.documentElement.dataset.scheme==='dark'; tg?.setHeaderColor(dk?'#131019':'#F4F1F8'); tg?.setBackgroundColor(dk?'#131019':'#F4F1F8'); tg?.setBottomBarColor?.(dk?'#131019':'#F4F1F8'); }catch(e){}
    if(STANDALONE) document.body.classList.add('standalone');
    if(!IN_TG && 'serviceWorker' in navigator){ navigator.serviceWorker.register('/sw.js').catch(()=>{}); }
    if(!IN_TG && !HQ){ try{ history.replaceState(null, '', '/app'); }catch(e){} }
    if(HQ){ S.tab = 'hq'; S.mk.view = 'qt'; }
    await unlockFlow();
    S.enter = true;
    S.data = await api('/api/bootstrap');
    applyPrefs(S.data.me?.prefs);
    const sp = tg?.initDataUnsafe?.start_param; if(TABS.some(t=>t[0]===sp)) S.tab = sp;
    if(!IN_TG && !HQ && S.data.me?.prefs?.home && TABS.concat([['mkt'],['chat']]).some(t=>t[0]===S.data.me.prefs.home)) S.tab = S.data.me.prefs.home;
    render();
  }catch(e){
    $('#app').innerHTML = `<div class="center"><div><p style="font-weight:600;color:var(--text)">Chưa mở được app</p><p>${esc(e.message)}</p></div></div>`;
  }
})();
