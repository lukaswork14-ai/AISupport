/* QC: gửi lỗi giao diện về bot để báo ngay cho chủ nhân (chỉ nội dung lỗi, không gửi dữ liệu) */
(function(){ let n=0; const send = (msg, src, line) => { if(n++ > 5) return;
  try{ fetch('/api/clienterror', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({msg:String(msg).slice(0,300), src:String(src||'').slice(-80), line:String(line||'')})}).catch(()=>{}); }catch(e){} };
  window.addEventListener('error', e => { if(e && e.message) send(e.message, e.filename, e.lineno); });
  window.addEventListener('unhandledrejection', e => { const m = (e.reason && (e.reason.message||e.reason)) || 'unhandled'; if(!/Mất kết nối|Đã khóa|Phiên hết hạn|mã PIN/.test(String(m))) send(m, 'promise', ''); });
})();
const tg = window.Telegram?.WebApp;
const IN_TG = !!tg?.initData;
if(/superHuyMac/.test(navigator.userAgent)) document.documentElement.classList.add('macapp');  // mở trong Telegram; ngược lại là app iPhone/trình duyệt (đăng nhập bằng PIN)
const STANDALONE = !!(navigator.standalone || matchMedia('(display-mode: standalone)').matches);
const HQ = /^\/hq(\/|$)/.test(location.pathname); if(HQ) document.documentElement.classList.add('hq');
/* bản superYou của khách (máy chủ chèn window.SUPERYOU_TENANT): chỉ Chat · Hôm nay · Biên bản (quyết định #4, thẻ 15) */
const TENANT = !HQ && !!window.SUPERYOU_TENANT;
const TENANT_TABS = ['home','meet','chat','me','more'];
const S = { tok:null, tab:'home', data:{}, jobs:{}, busy:{}, kind:'', calDay:'today', cal:{}, chatWait:false, first:'' };
const $ = s => document.querySelector(s);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const haptic = (t='light') => { if(S.haptics===false) return; try{ tg?.HapticFeedback?.impactOccurred(t) }catch(e){} };
const notifyH = t => { try{ tg?.HapticFeedback?.notificationOccurred(t) }catch(e){} };

/* ---------- biểu tượng (nét mảnh, đồng bộ) */
const P = {
  download:'<path d="M12 4v11"/><path d="m7 10 5 5 5-5"/><path d="M4 20h16"/>', bag:'<path d="M5 8h14l-1 12H6z"/><path d="M9 8a3 3 0 0 1 6 0"/>', factory:'<path d="M3 20V10l6 4v-4l6 4V5h4v15z"/><path d="M3 20h18"/>', users:'<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7M18 14.5a6 6 0 0 1 3.5 5.5"/>',
  home:'<path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  news:'<path d="M4 5h13v14H6a2 2 0 0 1-2-2zM17 9h3v8a2 2 0 0 1-2 2"/><path d="M7.5 9h6M7.5 12.5h6M7.5 16h4"/>',
  chat:'<path d="M4 5h16v11H9l-5 4z"/><path d="M8.5 10.5h.01M12 10.5h.01M15.5 10.5h.01"/>',
  studio:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m10 9.5 5 2.5-5 2.5z"/>',
  more:'<circle cx="5" cy="12" r="1.4"/><circle cx="12" cy="12" r="1.4"/><circle cx="19" cy="12" r="1.4"/>',
  calendar:'<rect x="3.5" y="5" width="17" height="15" rx="2"/><path d="M3.5 9.5h17M8 3v4M16 3v4"/>',
  mail:'<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3.5 6.5 8.5 6.5 8.5-6.5"/>',
  lark:'<path d="M4 6h16v10H10l-4 3v-3H4z"/><path d="M8 10h8M8 13h5"/>',
  brain:'<path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 3 5 3 3 0 0 0 5 1V5a3 3 0 0 0-3-1z"/><path d="M15 4a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-3 5 3 3 0 0 1-5 1"/>',
  send:'<path d="M4 12 20 4l-4 16-4-7z"/><path d="m12 13 8-9"/>',
  gear:'<circle cx="12" cy="12" r="3"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"/>',
  spark:'<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>',
  arrow:'<path d="M5 12h14M13 6l6 6-6 6"/>',
  chev:'<path d="m9 6 6 6-6 6"/>',
  pen:'<path d="M4 20h4L19 9l-4-4L4 16z"/>', save:'<path d="M6 4h12v16l-6-4-6 4z"/>',
  link:'<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3A4 4 0 0 0 11 18.7l1-1"/>',
  refresh:'<path d="M20 11a8 8 0 1 0-2.3 5.7"/><path d="M20 4v7h-7"/>',
  image:'<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="9.5" r="1.8"/><path d="m21 16-5-5-9 9"/>',
  film:'<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4"/>',
  play:'<path d="M8 5v14l11-7z"/>', copy:'<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a1 1 0 0 0-1-1H5a1 1 0 0 0-1 1v10a1 1 0 0 0 1 1h3"/>',
  plus:'<path d="M12 5v14M5 12h14"/>', mic:'<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21"/>', upload:'<path d="M12 15V4M7.5 8.5 12 4l4.5 4.5"/><path d="M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3"/>', video:'<rect x="3" y="6" width="13" height="12" rx="2"/><path d="m16 10.5 5-3v9l-5-3z"/>', pause:'<path d="M8 5v14M16 5v14"/>', check:'<path d="m5 12.5 4.5 4.5L19 7"/>', code:'<path d="m8 8-4 4 4 4M16 8l4 4-4 4M13.5 5l-3 14"/>', star:'<path d="m12 3.8 2.5 5.1 5.6.8-4 4 1 5.6-5.1-2.7-5 2.7 1-5.6-4.1-4 5.6-.8z"/>',
  x:'<path d="M6 6l12 12M18 6 6 18"/>', lock:'<rect x="5" y="11" width="14" height="10" rx="2.5"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
  del:'<path d="M21 5H9l-6 7 6 7h12a1 1 0 0 0 1-1V6a1 1 0 0 0-1-1z"/><path d="m12 9 6 6M18 9l-6 6"/>', reply:'<path d="M10 8 4 13l6 5"/><path d="M4 13h10a6 6 0 0 1 6 6"/>', inbox:'<path d="M3 13h5l1.5 3h5L16 13h5"/><path d="M5 5h14l2 8v6a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1v-6z"/>', layers:'<path d="m12 3 9 5-9 5-9-5z"/><path d="m3 13 9 5 9-5"/>', sprout:'<path d="M12 21v-9"/><path d="M12 12c0-4 3-7 8-7 0 4-3 7-8 7z"/><path d="M12 14c0-3-2.5-5.5-7-5.5 0 3 2.5 5.5 7 5.5z"/>', tasks:'<rect x="4" y="4" width="16" height="16" rx="4"/><path d="m8.5 12 2.5 2.5 4.5-5"/>', wallet:'<path d="M4 7a2 2 0 0 1 2-2h11v4"/><rect x="4" y="9" width="17" height="11" rx="2"/><path d="M16 14.5h2"/>', chart:'<path d="M4 20V10M10 20V4M16 20v-7M21 20H3"/>', back:'<path d="m15 6-6 6 6 6"/>', trash:'<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>'
};
const ico = (n, w=22) => `<svg width="${w}" height="${w}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${P[n]||P.spark}</svg>`;
const AGENT_ICON = { phattrien:'sprout', viec:'tasks', taichinh:'wallet', lich:'calendar', email:'mail', lark:'lark', tin:'news', studio:'studio', noidung:'studio', hop:'mic', dang:'send', brain:'brain', caidat:'gear' };
const KIND = { post:['Bài viết','pen'], bantin:['Ảnh bản tin','image'], video:['Video','film'], note:['Ghi chú','save'] };

/* ---------- tiện ích */
function toast(m, ms=2600){ const t=$('#toast'); t.textContent=m; t.style.display='block'; t.classList.remove('in'); void t.offsetWidth; t.classList.add('in'); clearTimeout(t._h); t._h=setTimeout(()=>t.style.display='none', ms); }
async function api(path, body){
  const opt = body ? {method:'POST', headers:{'Content-Type':'application/json','X-Session':S.tok||''}, body:JSON.stringify(body)} : {headers:{'X-Session':S.tok||''}};
  let r; try{ r = await fetch(path, opt); }catch(e){ throw new Error('Mất kết nối tới bot. Đóng app và bấm “Mở app” trong chat để mở lại.'); }
  const j = await r.json().catch(()=>({error:'Phản hồi không hợp lệ'}));
  if(r.status===401){ if(S.tok && path!=='/api/pin'){ relock(); throw new Error('Đã khóa, nhập mã PIN để tiếp tục'); } throw new Error(j.error||'Phiên hết hạn'); }
  if(j.error) throw new Error(j.error);
  return j;
}
async function run(agent, action, params={}, label='', quiet=false){
  if(!quiet) haptic();
  const j = await api('/api/run', {agent, action, params});
  const r = j.job ? await waitJob(j.job, label||action, agent, quiet) : j.result;
  if(r && r.game) xpPop(r.game);
  return r;
}
function waitJob(id, label, agent, quiet=false){
  if(!quiet){ S.jobs[id] = label; if(agent){ S.busy[agent]=(S.busy[agent]||0)+1; } paintBusy(); }
  return new Promise((ok, fail)=>{
    const done = () => { if(quiet) return; delete S.jobs[id]; if(agent){ S.busy[agent]--; } paintBusy(); };
    const tick = async ()=>{
      try{
        const j = await api('/api/job?id='+id);
        if(j.status==='running') return setTimeout(tick, 1600);
        done();
        if(j.status==='done'){ if(!quiet) notifyH('success'); ok(j.result); } else { if(!quiet) notifyH('error'); fail(new Error(j.error||'Có lỗi')); }
      }catch(e){ done(); fail(e); }
    };
    setTimeout(tick, 900);
  });
}
function paintBusy(){
  const names = Object.values(S.jobs), el = $('#jobs');
  el.style.display = names.length ? 'flex' : 'none';
  el.innerHTML = names.length ? `<div class="spin"></div><span>${esc(names[names.length-1])}${names.length>1?` và ${names.length-1} việc khác`:''}</span>` : '';
  document.querySelectorAll('.mate').forEach(m => m.classList.toggle('busy', (S.busy[m.dataset.id]||0) > 0));
}
async function refresh(){ const keep = S.data; S.data = await api('/api/bootstrap'); S.data.chat = S.data.chat || keep.chat || []; render(); }
const fmtTime = iso => iso ? iso.slice(11,16) : '';
const viDate = d => d.toLocaleDateString('vi-VN', {weekday:'long', day:'numeric', month:'long'});
function openLink(u){ if(!u) return; tg?.openLink ? tg.openLink(u) : window.open(u, '_blank'); }
function copyText(t){
  const ok = () => { toast('Đã sao chép'); haptic('medium'); };
  const fb = () => { const a=document.createElement('textarea'); a.value=t; document.body.appendChild(a); a.select(); try{ document.execCommand('copy'); ok(); }catch(e){ toast('Không sao chép được'); } a.remove(); };
  navigator.clipboard?.writeText ? navigator.clipboard.writeText(t).then(ok).catch(fb) : fb();
}

/* ---------- điều hướng */
const TABS = TENANT ? [['home','Hôm nay','home'],['ai','superYou','spark'],['meet','Biên bản','mic']]
  : HQ ? [['hq','Tổng quan','home'],['board','Phòng ban','users'],['ai','superHuy','spark'],['mkt','Marketplace','bag'],['users','Người dùng','users']]
  : [['home','Hôm nay','home'],['tasks','Việc','tasks'],['ai','superHuy','spark'],['meet','Họp','mic'],['growth','Phát triển','sprout']];
function nav(){
  const n = $('#nav'); n.hidden = false;
  n.innerHTML = TABS.map(([id,l,i]) => id==='ai' ? `<button data-t="ai" class="ai ${S.dockOpen||S.tab==='chat'?'on':''}" aria-label="Trò chuyện với superHuy"><span class="orb"><img class="brandimg" src="/icons/huy-192.png?v=3" alt=""></span><em>${l}</em></button>`
    : `<button data-t="${id}" class="${S.tab===id?'on':''}" aria-label="${l}">${ico(i)}<span>${l}</span></button>`).join('');
  n.querySelectorAll('button').forEach(b => b.onclick = () => b.dataset.t==='ai' ? aiToggle() : go(b.dataset.t));
  // viên nền trượt theo tab đang mở + biểu tượng nảy khi vừa chuyển tab
  const on = n.querySelector('button.on:not(.ai)'), pill = document.createElement('i'); pill.className = 'pill';
  n.prepend(pill);
  const place = () => { if(!on){ pill.style.opacity = 0; return; } const nb = n.getBoundingClientRect(), b = on.getBoundingClientRect();
    pill.style.opacity = 1; pill.style.width = Math.min(64, b.width - 6) + 'px'; pill.style.left = (b.left - nb.left + (b.width - Math.min(64, b.width - 6)) / 2) + 'px'; };
  if(S.pillX != null){ pill.style.transition = 'none'; pill.style.left = S.pillX + 'px'; pill.style.width = (S.pillW||56) + 'px'; void pill.offsetWidth; pill.style.transition = ''; }
  requestAnimationFrame(()=>{ place(); S.pillX = parseFloat(pill.style.left)||null; S.pillW = parseFloat(pill.style.width)||56; });
  if(on && S.popTab === S.tab){ on.classList.add('pop'); S.popTab = null; }
  sideNav();
}
/* thanh bên cho màn hình rộng (Mac, iPad ngang, máy tính) */
const SIDE = TENANT ? [['home','Hôm nay','home',"go('home')"],['chat','Trò chuyện','chat',"go('chat')"],['meet','Biên bản','mic',"go('meet')"],['me','Hồ sơ','users',"go('me')"],['more','Cài đặt','gear',"go('more')"]]
  : HQ ? [['hq','Tổng quan','home',"go('hq')"],['board','Phòng ban','users',"go('board')"],['mkt','Marketplace','bag',"go('mkt')"],['gd','Giao dịch','wallet',"S.mk.view='qt';S.mk.admTab='gd';go('mkt')"],
  ['leads','Khách hàng','inbox',"go('leads')"],['lab','Xưởng clone','factory',"go('lab')"],['cfo','Tài chính CFO','chart',"go('cfo')"],['sales','Bán hàng CSO','inbox',"go('sales')"],['ops','Vận hành','check',"go('ops')"],['users','Người dùng & gói','users',"go('users')"],['ex','Thử nghiệm','sprout',"go('ex')"],['_qc','Hệ thống','check',"openQC()"],['_app','Mở superHuy','spark',"openLink(location.origin+'/app')"]]
  : [['home','Hôm nay','home',"go('home')"],['tasks','Việc','tasks',"go('tasks')"],['meet','Họp','mic',"go('meet')"],['content','Nội dung','film',"go('content')"],
  ['growth','Phát triển','sprout',"go('growth')"],['mail','Hộp thư','inbox',"go('mail')"],['money','Tài chính','wallet',"go('money')"],['chat','Trò chuyện','chat',"go('chat')"],
  ['mkt','Marketplace','bag',"go('mkt')"],['wf','Workflow của tôi','layers',"go('wf')"],['_brain','Second Brain','brain',"openBrain()"],['_lark','Lark','lark',"openAgent('lark')"],['_hq','superYou HQ','factory',"openLink(location.origin+'/hq')"],['me','Hồ sơ','users',"go('me')"],['more','Cài đặt','gear',"go('more')"]];
function sideNav(){
  const el = $('#side'); if(!el) return;
  const badge = {tasks:S.tk?.data?.stats?.today, content:S.data?.cq?.new?.length, meet:(S.mt?.items||[]).filter(m=>m.status==='working'||m.status==='queued').length};
  el.innerHTML = `<div class="sbrand" role="button" tabindex="0" onclick="roleMenu()" aria-label="Chuyển vai"><img class="brandimg" src="/icons/huy-128.png?v=3" alt=""><div><b>${HQ?'superYou HQ':'superHuy'} <span class="rolecaret">▾</span></b><span>${HQ?'Vai: Chủ sàn':'Vai: Người dùng'}</span></div></div>
    <button class="sask" onclick="S.dockOpen=true;dock();setTimeout(()=>$('#dIn')?.focus(),150)">${ico('spark',18)}<span>Hỏi superHuy</span><kbd>⌘K</kbd></button>
    <div class="snav">${SIDE.map(([id,l,i,f])=>`<button class="${S.tab===id||(id==='content'&&['news','studio'].includes(S.tab))?'on':''}" onclick="${f}">${ico(i,19)}<span>${l}</span>${badge[id]?`<em>${badge[id]>99?'99+':badge[id]}</em>`:''}</button>`).join('')}</div>
    <div class="sfoot"><button onclick="openQC()">${ico('check',16)} Tình trạng hệ thống</button><button onclick="lockNow(true)">${ico('lock',16)} Khoá</button></div>`;
}
const WIDE = matchMedia('(min-width:1024px)');
WIDE.addEventListener?.('change', ()=>{ try{ if(S.tok) render(); }catch(e){} });
document.addEventListener('keydown', e=>{ if((e.metaKey||e.ctrlKey) && e.key.toLowerCase()==='k' && S.tok && !lockOn()){ e.preventDefault(); S.dockOpen=true; dock(); setTimeout(()=>$('#dIn')?.focus(),150); } });
function go(tab){ if(TENANT && !TENANT_TABS.includes(tab)) tab = 'home'; if(tab==='news'||tab==='studio'){ S.cview = tab==='news'?'duyet':'tao'; tab='content'; } if(S.tab!==tab){ haptic('soft'); S.enter = true; S.popTab = tab; } S.tab = tab; closeSheet(); render(); window.scrollTo(0,0); if(tab==='chat') setTimeout(()=>$('#msgIn')?.focus(), 200); }
function render(){
  nav();
  const app = $('#app');
  if(S.enter){ S.enter = false; app.classList.remove('enter'); void app.offsetWidth; app.classList.add('enter'); clearTimeout(S.enterT); S.enterT = setTimeout(()=>app.classList.remove('enter'), 900); }
  $('#app').innerHTML = ({home:vHome, meet:vMeet, mail:vMail, chat:vChat, content:vContent, news:vContent, studio:vContent, more:vMore, tasks:vTasks, money:vMoney, growth:vGrowth, mkt:vMkt, lab:vLab, leads:vLeads, hq:vHq, board:vBoard, cfo:vCfo, sales:vSales, ops:vOps, me:vMe, wf:vWf, ex:vEx, users:vUsers})[S.tab]();
  paintBusy();
  if(S.tab==='home'){ loadCal(true); loadInv(true); liveDigests(); loadHomeStats(); }
  if(S.tab==='tasks') tasksEnter();
  if(S.tab==='money') moneyEnter();
  if(S.tab==='growth') growthEnter();
  if(S.tab==='mkt') mkLoad();
  if(S.tab==='leads') tipBind();
  if(S.tab==='hq') hqLoad();
  if(S.tab==='me' && !S.me) meLoad();
  if(S.tab==='wf' && !S.wf.lib) wfLoad();
  if(S.tab==='ex' && !S.ex) exLoad();
  if(S.tab==='users' && !S.us) usLoad();
  if(S.tab==='board' && !S.bd) bdLoad();
  if(S.tab==='cfo'){ if(!S.cf) cfLoad(); else tipBind(); }
  if(S.tab==='mail'){ mailEnter(); bindSwipe(); }
  if(S.tab==='content') contentEnter();
  if(S.tab==='meet'){ if(S.mt.rec) recTick(); else meetEnter(); }
  dock();
  
  if(S.tab==='chat'){ const c=$('.chat'); if(c) window.scrollTo(0, document.body.scrollHeight); bindComposer(); }
}

