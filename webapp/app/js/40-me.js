/* =================================================================== Hồ sơ, cài đặt, passkey, workflow riêng (Không gian của tôi) */
const ACC = {violet:'#6A3DF0', jade:'#0B9877', blue:'#2457C5', rose:'#C21F78', amber:'#C98205', ink:'#15171A'};
function applyPrefs(p){
  if(!p) return;
  const r = document.documentElement;
  if(!IN_TG){ if(p.theme && p.theme!=='system') r.dataset.scheme = p.theme; else r.dataset.scheme = matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';
    if(ACC[p.accent]) r.style.setProperty('--jade', ACC[p.accent]); r.classList.toggle('compact', p.density==='compact'); }
  S.haptics = p.haptics !== false;
}
S.me = null;
function planCard(){
  const pl = S.data?.me?.plan; if(!pl || !pl.plan || HQ) return '';
  const L = pl.limits||{}, U = pl.used||{}, bar = (k, label)=> L[k] ? `<div class="fun"><span>${label}</span><i><em style="width:${Math.min(100,Math.round((U[k]||0)/L[k]*100))}%"></em></i><b>${U[k]||0}/${L[k]}</b></div>` : `<div class="fun"><span>${label}</span><i><em style="width:100%"></em></i><b>Không giới hạn</b></div>`;
  const trial = pl.plan==='trial' && pl.trial_until ? `<p class="meta" style="margin:6px 0 0">Dùng thử đến ${esc(pl.trial_until)} · hết hạn tự về Miễn phí, không mất dữ liệu.</p>` : '';
  return `<div class="sec"><h2>Gói của anh</h2>${pl.next?`<button class="link" onclick="openLink('${pl.upgrade_url}')">Nâng lên ${esc(pl.next_name)}</button>`:''}</div>
    <div class="card pad chart" style="border-left:4px solid ${esc(pl.color||'#6A3DF0')}"><div class="row" style="justify-content:space-between;margin-bottom:8px"><b>${esc(pl.name)}</b><span class="meta">${(pl.features||[]).slice(0,1).map(esc).join('')}</span></div>${bar('workflows','Workflow riêng')}${bar('meetings_month','Họp mỗi tháng')}${bar('seats','Người dùng')}${trial}</div>`;
}
async function meLoad(){ try{ S.me = await run('toi','ho_so',{},'',true); }catch(e){ toast(e.message); S.me={profile:{},prefs:{},themes:{},accents:{},density:{},homes:{},passkeys:[],flags:{flags:{},tier:'free'},tier_names:{}}; } if(S.tab==='me' && !$('#sheet').classList.contains('on')) render(); }
function vMe(){
  const m = S.me, head = `<div class="date">Hồ sơ, bảo mật và cài đặt của ${esc(S.first||'anh')}</div><h1>Không gian của tôi</h1>`;
  if(!m){ meLoad(); return head + `<div class="card empty">Đang tải…</div>`; }
  const p = m.profile||{}, pr = m.prefs||{}, pk = m.passkeys||[], tier = m.flags?.tier||'free';
  const pkOk = !IN_TG && !!window.PublicKeyCredential;
  return head + `<div class="mecard"><span class="orb" style="width:64px;height:64px"><img class="brandimg" src="/icons/huy-192.png?v=3" alt=""></span><div class="grow"><b style="font-size:19px">${esc(p.name||'')}</b><div class="meta">${esc([p.title,p.company].filter(Boolean).join(' · '))}</div><span class="tag role" style="margin-top:4px;display:inline-block">${esc(m.tier_names?.[tier]||tier)}</span></div><button class="btn sm" onclick="meEditProfile()">Sửa</button></div>
    ${planCard()}
    <div class="sec"><h2>Bảo mật</h2></div>
    <div class="card list">
      <div><span class="thumb">${ico('lock',20)}</span><div class="grow"><div style="font-weight:600">Đăng nhập bằng Face ID / Touch ID / vân tay</div><div class="meta">${pkOk?(pk.length?`${pk.length} thiết bị đã đăng ký. Mở app không cần PIN.`:'Dùng khoá sinh trắc của thiết bị thay mã PIN. Mỗi thiết bị đăng ký một lần.'):(IN_TG?'Mở app ngoài Telegram (iPhone, Mac, web) để bật.':'Trình duyệt này chưa hỗ trợ passkey.')}</div></div>${pkOk?`<button class="btn sm pri" onclick="pkRegister()">Thêm thiết bị này</button>`:''}</div>
      ${pk.map(c=>`<div><span class="thumb">${ico('check',18)}</span><div class="grow"><div style="font-weight:600">${esc(c.name)}</div><div class="meta">Đăng ký ${esc(c.created)}${c.last?` · dùng lần cuối ${esc(c.last)}`:''}</div></div><button class="btn sm" onclick="run('toi','passkey_xoa',{cid:'${esc(c.id)}'},'',true).then(r=>{toast(r.text);S.me=null;meLoad()})">Gỡ</button></div>`).join('')}
      <button onclick="openAction('caidat','doipin')"><span class="thumb">${ico('gear',20)}</span><div class="grow"><div style="font-weight:600">Đổi mã PIN</div><div class="meta">PIN vẫn là cách dự phòng khi passkey không dùng được.</div></div><span class="chev">${ico('chev',18)}</span></button>
      <button onclick="lockNow(true)"><span class="thumb">${ico('lock',20)}</span><div class="grow"><div style="font-weight:600">Khoá ngay trên mọi thiết bị</div><div class="meta">Đăng xuất mọi phiên và khoá bot.</div></div></button>
    </div>
    <div class="sec"><h2>Giao diện</h2></div>
    <div class="card pad">
      <div class="row" style="justify-content:space-between;margin-bottom:10px"><span style="font-weight:600">Chế độ</span><div class="seg">${Object.entries(m.themes||{}).map(([k,l])=>`<button class="${pr.theme===k?'on':''}" onclick="mePref({theme:'${k}'})">${esc(l)}</button>`).join('')}</div></div>
      <div class="row" style="justify-content:space-between;margin-bottom:10px"><span style="font-weight:600">Màu nhấn</span><div class="row">${Object.entries(m.accents||{}).map(([k,c])=>`<button class="swatch ${pr.accent===k?'on':''}" style="--c:${c}" aria-label="${k}" onclick="mePref({accent:'${k}'})"></button>`).join('')}</div></div>
      <div class="row" style="justify-content:space-between;margin-bottom:10px"><span style="font-weight:600">Mật độ</span><div class="seg">${Object.entries(m.density||{}).map(([k,l])=>`<button class="${pr.density===k?'on':''}" onclick="mePref({density:'${k}'})">${esc(l)}</button>`).join('')}</div></div>
      <div class="row" style="justify-content:space-between"><span style="font-weight:600">Trang mở đầu</span><select onchange="mePref({home:this.value})">${Object.entries(m.homes||{}).map(([k,l])=>`<option value="${k}" ${pr.home===k?'selected':''}>${esc(l)}</option>`).join('')}</select></div>
      <p class="meta" style="margin:10px 0 0">Trong Telegram, app theo màu của Telegram. Trên iPhone, Mac và web dùng cài đặt này.</p>
    </div>
    <div class="sec"><h2>Thông báo</h2></div>
    <div class="card list">${[['notify_brief','Bản tin sáng từ CFO và phòng ban'],['notify_board','Báo khi có đề xuất chờ duyệt'],['haptics','Rung phản hồi khi thao tác']].map(([k,l])=>`<label class="lbopt" style="padding:12px 16px"><input type="checkbox" ${pr[k]!==false?'checked':''} onchange="mePref({${k}:this.checked})"><span>${l}</span></label>`).join('')}</div>
    <div class="sec"><h2>Tính năng của gói ${esc(m.tier_names?.[tier]||tier)}</h2></div>
    <div class="card list">${Object.entries(m.flags?.flags||{}).map(([k,on])=>`<div><span class="st ${on?'ok':'no'}"></span><div class="grow"><div style="font-weight:600">${esc(FLAG_NAMES[k]||k)}</div></div></div>`).join('')}</div>`;
}
const FLAG_NAMES = {workflow_builder:'Trình dựng workflow kéo thả', passkey_login:'Đăng nhập Face ID / vân tay', assistant_coach:'Trợ lý đồng hành', cfo_brief:'CFO brief mỗi sáng', clone_factory:'Xưởng clone', private_llm:'AI tại chỗ (Ollama)'};
async function mePref(o){ try{ const r = await run('toi','cai_dat_luu',o,'',true); if(S.me) S.me.prefs = r.prefs; if(S.data.me) S.data.me.prefs = r.prefs; applyPrefs(r.prefs); render(); }catch(e){ toast(e.message); } }
function meEditProfile(){ const p = S.me?.profile||{}; sheet(`<h2>Hồ sơ</h2><p class="meta">superYou dùng hồ sơ để trả lời đúng vai trò và mục tiêu của anh.</p>
  ${[['name','Tên'],['title','Chức danh'],['company','Công ty'],['industry','Ngành']].map(([k,l])=>`<label class="field"><span>${l}</span><input type="text" id="pf_${k}" value="${esc(p[k]||'')}"></label>`).join('')}
  <label class="field"><span>Mục tiêu 90 ngày</span><textarea id="pf_goals" style="min-height:80px">${esc(p.goals||'')}</textarea></label>
  <button class="btn pri full" onclick="closeSheet();run('toi','ho_so_luu',{name:$('#pf_name').value,title:$('#pf_title').value,company:$('#pf_company').value,industry:$('#pf_industry').value,goals:$('#pf_goals').value},'',true).then(r=>{toast(r.text);S.first=r.profile.name;S.me=null;meLoad()}).catch(e=>toast(e.message))">Lưu</button>`); }

/* ---------- Workflow riêng: kéo thả từ thư viện, trợ lý đồng hành */
S.wf = { lib:null, list:null, cur:null };
async function wfLoad(){ try{ const [lib, list] = await Promise.all([run('toi','thu_vien',{},'',true), run('toi','wf_ds',{},'',true)]); S.wf.lib = lib; S.wf.list = list; }catch(e){ toast(e.message); S.wf.lib={steps:[],market:[],sched:{}}; S.wf.list={items:[],runs:[],sched:{}}; } if(S.tab==='wf' && !$('#sheet').classList.contains('on')) render(); }
function vWf(){
  const head = `<div class="date">Ghép các bước có sẵn thành quy trình của riêng anh. Chỉ đọc và tổng hợp, không tự gửi hay đăng.</div><h1>Workflow của tôi</h1>`;
  if(!S.wf.lib){ wfLoad(); return head + `<div class="card empty">Đang tải thư viện…</div>`; }
  if(S.wf.cur) return head + wfBuilder();
  const L = S.wf.list;
  return head + `<div class="row" style="margin-bottom:12px"><button class="btn pri" onclick="wfNew()">${ico('plus',16)} Dựng workflow mới</button><button class="btn" onclick="wfCoachSheet()">${ico('spark',16)} Nhờ trợ lý gợi ý</button></div>
    <div class="card mklist">${(L.items||[]).map(w=>`<div class="mkrow"><span class="mkicon" style="--c:#2457C5;width:44px;height:44px">${ico('layers',20)}</span><div class="grow" role="button" tabindex="0" onclick="wfEdit('${w.id}')"><div class="ttl2">${esc(w.name)}</div><div class="meta">${w.steps.length} bước${w.schedule?` · ${esc(L.sched[w.schedule]||'')}`:''}${w.runs?` · chạy ${w.runs} lần`:''}${w.last_run?` · ${esc(ago(w.last_run))}`:''}</div></div><div class="row"><button class="btn sm pri" onclick="wfRun('${w.id}')">${ico('play',15)} Chạy</button><button class="btn sm" onclick="wfEdit('${w.id}')">Sửa</button></div></div>`).join('')||'<div class="empty">Chưa có workflow nào. Dựng mới hoặc nhờ trợ lý gợi ý từ một câu mục tiêu.</div>'}</div>
    ${(L.runs||[]).length?`<div class="sec"><h2>Lần chạy gần đây</h2></div><div class="card mklist">${L.runs.slice(0,5).map(r=>`<div class="mkrow" role="button" tabindex="0" onclick="wfShow(${JSON.stringify(r.text).replace(/"/g,'&quot;')})"><div class="grow"><div class="ttl2">${esc(r.name)}</div><div class="meta">${esc(ago(r.at))} · ${r.ok}/${r.total} bước</div></div><span class="chev">${ico('chev',18)}</span></div>`).join('')}</div>`:''}`;
}
function wfShow(text){ sheet(`<h2>Kết quả</h2><div style="white-space:pre-line;margin-top:10px">${esc(text)}</div><div class="row" style="margin-top:12px"><button class="btn" onclick="copyText(${JSON.stringify(text).replace(/"/g,'&quot;')})">${ico('copy',15)} Sao chép</button></div>`); }
function wfNew(){ S.wf.cur = {id:'', name:'Workflow mới', desc:'', steps:[], schedule:''}; render(); }
function wfEdit(id){ const w = (S.wf.list.items||[]).find(x=>x.id===id); if(w){ S.wf.cur = JSON.parse(JSON.stringify(w)); render(); } }
function wfBuilder(){
  const w = S.wf.cur, lib = S.wf.lib, q = (S.wf.q||'').toLowerCase();
  const groups = {}; lib.steps.filter(s=>!q||(s.label+s.group+s.desc).toLowerCase().includes(q)).forEach(s=>{ (groups[s.group]=groups[s.group]||[]).push(s); });
  return `<div class="row" style="justify-content:space-between;margin-bottom:10px"><button class="btn sm" onclick="S.wf.cur=null;render()">${ico('back',15)} Danh sách</button><div class="row"><button class="btn sm" onclick="wfCoachSheet()">${ico('spark',15)} Trợ lý</button>${w.id?`<button class="btn sm" onclick="wfRun('${w.id}')">${ico('play',15)} Chạy thử</button>`:''}<button class="btn sm pri" onclick="wfSave()">Lưu</button></div></div>
    <div class="wfwrap"><section class="card pad wfcanvas" ondragover="event.preventDefault();this.classList.add('over')" ondragleave="this.classList.remove('over')" ondrop="wfDrop(event)">
      <label class="field" style="margin-bottom:8px"><span>Tên</span><input type="text" id="wfName" value="${esc(w.name)}" oninput="S.wf.cur.name=this.value"></label>
      <div class="row" style="justify-content:space-between;margin-bottom:8px"><b>Các bước (${w.steps.length})</b><select onchange="S.wf.cur.schedule=this.value" aria-label="Lịch chạy">${Object.entries(lib.sched||{}).map(([k,l])=>`<option value="${k}" ${w.schedule===k?'selected':''}>${k?'Lịch: ':''}${esc(l)}</option>`).join('')}</select></div>
      <ol class="wfsteps" id="wfSteps">${w.steps.map((st,i)=>`<li class="wfstep" draggable="true" data-i="${i}" ondragstart="wfDragStep(event,${i})" ondragover="event.preventDefault()" ondrop="wfDropOn(event,${i})"><span class="wfn">${i+1}</span><div class="grow"><input class="wflabel" value="${esc(st.label||'')}" oninput="S.wf.cur.steps[${i}].label=this.value" aria-label="Tên bước"><div class="meta">${esc(st.agent)}.${esc(st.action)}${Object.keys(st.params||{}).length?` · ${esc(Object.entries(st.params).map(([k,v])=>k+'='+v).join(', '))}`:''}</div></div><div class="row" style="flex-wrap:nowrap"><button class="iconbtn" aria-label="Lên" onclick="wfMove(${i},-1)">${ico('chev',16)}</button><button class="iconbtn" aria-label="Xuống" onclick="wfMove(${i},1)" style="transform:rotate(90deg)">${ico('chev',16)}</button><button class="iconbtn" aria-label="Thông số" onclick="wfParams(${i})">${ico('gear',16)}</button><button class="iconbtn" aria-label="Bỏ" onclick="S.wf.cur.steps.splice(${i},1);render()">${ico('trash',16)}</button></div></li>`).join('')||'<li class="wfempty">Kéo bước từ thư viện vào đây, hoặc bấm vào bước để thêm.</li>'}</ol>
      ${w.steps.length>=2?`<p class="meta">Kéo để sắp xếp lại. Workflow chạy lần lượt từ trên xuống, kết quả gom thành một bản.</p>`:''}
    </section>
    <aside class="card pad wflib"><input type="search" placeholder="Tìm bước…" value="${esc(S.wf.q||'')}" oninput="S.wf.q=this.value;render()" aria-label="Tìm bước" style="width:100%;margin-bottom:8px">
      ${Object.entries(groups).map(([g,items])=>`<div class="wfgroup"><b>${esc(items[0].icon||'')} ${esc(g)}</b>${items.map(s=>`<button class="wfitem" draggable="true" ondragstart="wfDragLib(event,'${s.id}')" onclick="wfAdd('${s.id}')" title="${esc(s.desc)}"><span>${esc(s.label)}</span>${ico('plus',14)}</button>`).join('')}</div>`).join('')||'<div class="empty">Không có bước khớp.</div>'}
      ${(lib.market||[]).length?`<div class="wfgroup"><b>🛍 Marketplace</b>${lib.market.map(m=>`<button class="wfitem" onclick="go('mkt');setTimeout(()=>mkOpen('${m.lid}'),200)"><span>${esc(m.label)}</span><span class="meta">${m.installed?'đã cài':m.price?vnd(m.price):'miễn phí'}</span></button>`).join('')}</div>`:''}
    </aside></div>`;
}
function wfDragLib(e, id){ e.dataTransfer.setData('text/lib', id); e.dataTransfer.effectAllowed = 'copy'; }
function wfDragStep(e, i){ e.dataTransfer.setData('text/step', String(i)); e.dataTransfer.effectAllowed = 'move'; }
function wfDrop(e){ e.preventDefault(); e.currentTarget.classList.remove('over'); const id = e.dataTransfer.getData('text/lib'); if(id) wfAdd(id); }
function wfDropOn(e, to){ e.preventDefault(); e.stopPropagation(); const from = e.dataTransfer.getData('text/step'); const id = e.dataTransfer.getData('text/lib'); const st = S.wf.cur.steps;
  if(from!==''){ const [x] = st.splice(+from,1); st.splice(to,0,x); } else if(id){ const s = S.wf.lib.steps.find(x=>x.id===id); if(s) st.splice(to,0,{agent:s.agent, action:s.action, params:{}, label:s.label}); }
  render(); }
function wfAdd(id){ const s = S.wf.lib.steps.find(x=>x.id===id); if(!s) return; if(S.wf.cur.steps.length>=12) return toast('Tối đa 12 bước'); S.wf.cur.steps.push({agent:s.agent, action:s.action, params:{}, label:s.label}); haptic('light'); render(); }
function wfMove(i, d){ const st = S.wf.cur.steps, j = i+d; if(j<0||j>=st.length) return; [st[i],st[j]] = [st[j],st[i]]; render(); }
function wfParams(i){ const st = S.wf.cur.steps[i], def = S.wf.lib.steps.find(x=>x.agent===st.agent&&x.action===st.action); const ps = def?.params||[];
  sheet(`<h2>${esc(st.label||'Bước')}</h2><p class="meta">${esc(def?.desc||'')}</p>${ps.length?ps.map(p=>`<label class="field"><span>${esc(p.label)}</span><input type="text" id="wp_${p.name}" value="${esc(st.params?.[p.name]??(p.default??''))}"></label>`).join(''):'<p class="meta">Bước này không có thông số.</p>'}<button class="btn pri full" onclick="closeSheet();${ps.map(p=>`S.wf.cur.steps[${i}].params['${p.name}']=$('#wp_${p.name}').value;`).join('')}render()">Xong</button>`); }
async function wfSave(){ const w = S.wf.cur; if(!w.steps.length) return toast('Thêm ít nhất một bước'); try{ const r = await run('toi','wf_luu',{wid:w.id, name:$('#wfName')?.value||w.name, steps:JSON.stringify(w.steps), schedule:w.schedule||'', desc:w.desc||''},'',true); toast(r.text, 3500); notifyH('success'); S.wf.cur=null; S.wf.list=null; S.wf.lib=null; wfLoad(); }catch(e){ toast(e.message, 4500); } }
async function wfRun(id){ toast('Đang chạy…', 2500); try{ const r = await run('toi','wf_chay',{wid:id},'Chạy workflow'); wfShow(r.text||''); S.wf.list=null; wfLoad(); }catch(e){ toast(e.message); } }
function wfCoachSheet(){ sheet(`<h2>Trợ lý đồng hành</h2><p class="meta">Nói mục tiêu, trợ lý ghép sẵn các bước. Anh kéo thả chỉnh tiếp rồi lưu.</p><label class="field" style="margin-top:10px"><span>Anh muốn workflow làm gì?</span><textarea id="wfGoal" placeholder="Ví dụ: mỗi sáng gom lịch, tin nhắn Lark và tin ngành thành một bản ngắn"></textarea></label><div class="chips" style="padding-top:0">${['Bàn giao buổi sáng','Chuẩn bị trước cuộc họp','Tổng hợp tuần cho đội','Theo dõi đối thủ'].map(x=>`<button class="chip" onclick="$('#wfGoal').value='${x}'">${x}</button>`).join('')}</div><button class="btn pri full" onclick="wfCoach()">${ico('spark',16)} Gợi ý</button>`); }
async function wfCoach(){ const goal = $('#wfGoal').value.trim(); if(!goal) return toast('Nhập mục tiêu'); closeSheet(); toast('Trợ lý đang ghép bước…', 3000); try{ const r = await run('toi','tro_ly',{goal},'Gợi ý workflow'); if(!S.wf.lib) await wfLoad(); S.wf.cur = {id:'', name:r.name, desc:r.why, steps:r.steps, schedule:''}; go('wf'); toast(r.tip||r.why, 5000); }catch(e){ toast(e.message, 4500); } }

