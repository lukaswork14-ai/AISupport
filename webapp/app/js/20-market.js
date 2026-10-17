/* =================================================================== superYou Marketplace (trong app của chủ nhân) */
S.mk = { view:'kham', q:'', cat:'', type:'', data:null, adm:null, admTab:'cho', admFilter:'all' };
const MKT_ICON = { skill:'spark', brain:'brain', workflow:'layers' };
const vnd = v => v>0 ? Number(v).toLocaleString('vi-VN')+'đ' : 'Miễn phí';
function mkIcon(x, size=56){ return `<span class="mkicon" style="--c:${esc(x.color||'#5B3FD9')};width:${size}px;height:${size}px">${ico(MKT_ICON[x.type]||'spark', Math.round(size*.46))}</span>`; }
function mkStars(r, n){ return r ? `<span class="mkstars" aria-label="${r} sao">★ ${String(r).replace('.',',')}${n!=null?` <i>(${n})</i>`:''}</span>` : `<span class="mkstars none">Chưa có đánh giá</span>`; }
function mkBy(x){ return `${esc(x.creator?.name||'')}${x.creator?.official?' <b class="mkoff">Chính chủ</b>':''}`; }
async function mkLoad(force){
  if(S.mk.data && !force) return;
  try{ S.mk.data = await run('market','ds',{q:S.mk.q, cat:S.mk.cat, type:S.mk.type},'',true); }catch(e){ toast(e.message); S.mk.data = {items:[],top:[],new:[],featured:[],installed:[],cats:{},types:{},pending:0}; }
  if(S.tab==='mkt' && !$('#sheet').classList.contains('on')) render();
}
function mkGet(x){
  if(x.installed) return `<button class="mkget on" onclick="event.stopPropagation();mkOpen('${x.id}')">Đã cài</button>`;
  return `<button class="mkget" onclick="event.stopPropagation();mkInstall('${x.id}')">${x.price>0?'Nhận':'Nhận'}</button>`;
}
function mkRow(x, i){ return `<div class="mkrow" role="button" tabindex="0" onclick="mkOpen('${x.id}')" onkeydown="if(event.key==='Enter')mkOpen('${x.id}')">
  ${i!=null?`<span class="mkrank">${i+1}</span>`:''}${mkIcon(x,52)}<div class="grow"><div class="ttl2">${esc(x.name)}</div><div class="meta clamp1">${esc(x.tagline||'')}</div>
  <div class="meta">${esc(x.type_label)} · ${mkStars(x.rating, x.rating_n)}${x.price>0?` · ${vnd(x.price)}`:''}</div></div>${mkGet(x)}</div>`; }
function vMkt(){
  const v = S.mk.view, d = S.mk.data;
  const head = `<div class="date">Chợ tài sản số của superYou: skill, workflow, gói tri thức</div><h1>Marketplace</h1>
    <div class="row" style="margin-bottom:14px;justify-content:space-between"><div class="seg" style="flex-wrap:wrap"><button class="${v==='kham'?'on':''}" onclick="S.mk.view='kham';render()">Khám phá</button><button class="${v==='cai'?'on':''}" onclick="S.mk.view='cai';render()">Đã cài${d?.installed?.length?` ${d.installed.length}`:''}</button>${HQ?`<button class="${v==='xuong'?'on':''}" onclick="S.mk.view='xuong';render()" style="white-space:nowrap;display:inline-flex;align-items:center;gap:5px">${ico('factory',14)}Xưởng clone</button><button class="${v==='qt'?'on':''}" onclick="S.mk.view='qt';render()">Quản trị${d?.pending?` <em class="mkbadge">${d.pending}</em>`:''}</button>`:''}</div>
    <div class="row">${HQ?`<button class="btn sm pri" onclick="lbNew()">${ico('plus',16)} Tạo tài sản</button>`:`<button class="btn sm" onclick="openLink(location.origin+'/hq')">${ico('factory',16)} Quản trị ở HQ</button>`}<button class="btn sm" onclick="openLink(location.origin+'/market')">${ico('link',16)} Trang công khai</button></div></div>`;
  if(v==='xuong') return head + vLabInner();
  if(v==='qt') return head + vQt();
  if(!d) return head + `<div class="card empty">Đang mở Marketplace…</div>`;
  if(v==='cai') return head + mkInstalled(d);
  const chips = `<div class="chips" role="group" aria-label="Danh mục"><button class="chip ${!S.mk.cat?'on':''}" onclick="mkFilter('cat','')">Tất cả</button>${Object.entries(d.cats||{}).map(([k,l])=>`<button class="chip ${S.mk.cat===k?'on':''}" onclick="mkFilter('cat','${k}')">${esc(l)}</button>`).join('')}</div>
    <div class="chips" role="group" aria-label="Loại">${Object.entries(d.types||{}).map(([k,l])=>`<button class="chip ${S.mk.type===k?'on':''}" onclick="mkFilter('type',S.mk.type==='${k}'?'':'${k}')">${ico(MKT_ICON[k],14)} ${esc(l)}</button>`).join('')}</div>`;
  const search = `<form class="hask" style="margin:0 0 4px" onsubmit="event.preventDefault();S.mk.q=$('#mkq').value.trim();mkLoad(true)"><input id="mkq" value="${esc(S.mk.q)}" placeholder="Tìm skill, workflow, gói tri thức…" autocomplete="off" enterkeyhint="search"><button class="go" aria-label="Tìm">${ico('arrow',20)}</button></form>`;
  if(!d.items.length) return head + search + chips + `<div class="card empty">${S.mk.q||S.mk.cat||S.mk.type?'Không có sản phẩm khớp bộ lọc.':'Chưa có sản phẩm nào lên kệ.'}</div>`;
  const feat = d.featured.length ? `<div class="mkfeat">${d.featured.map(x=>`<article class="mkhero" style="--c:${esc(x.color)}" onclick="mkOpen('${x.id}')" role="button" tabindex="0">
      <span class="mkkick">${esc(x.type_label)}${x.featured?' · Đang nổi bật':''}</span><h3>${esc(x.name)}</h3><p>${esc(x.tagline||'')}</p>
      <div class="row" style="margin-top:auto;justify-content:space-between"><span class="mkby">${mkBy(x)}</span>${mkGet(x)}</div></article>`).join('')}</div>` : '';
  return head + search + chips + feat +
    `<div class="mkcols"><section><div class="sec"><h2>Được dùng nhiều</h2></div><div class="card mklist">${d.top.map((x,i)=>mkRow(x,i)).join('')}</div></section>
     <section><div class="sec"><h2>Mới lên kệ</h2></div><div class="card mklist">${d.new.map(x=>mkRow(x)).join('')}</div></section></div>`;
}
function mkFilter(k, v){ S.mk[k] = v; mkLoad(true); }
function mkInstalled(d){
  if(!d.installed.length) return `<div class="done"><b>Anh chưa cài sản phẩm nào</b>Skill giúp superHuy làm đúng kiểu anh muốn, workflow chạy nhiều việc bằng một chạm, gói tri thức bổ sung Second Brain.<div class="row" style="justify-content:center;margin-top:16px"><button class="btn pri" onclick="S.mk.view='kham';render()">Khám phá Marketplace</button></div></div>`;
  return `<div class="card mklist">${d.installed.map(x=>`<div class="mkrow">${mkIcon(x,48)}<div class="grow" role="button" tabindex="0" onclick="mkOpen('${x.id}')"><div class="ttl2">${esc(x.name)}</div><div class="meta">${esc(x.type_label)} · phiên bản ${esc(x.version)} · ${x.enabled?'đang bật':'đang tắt'}</div></div>
    <div class="row">${x.type==='workflow'||x.type==='pack'?`<button class="btn sm pri" onclick="mkRun('${x.id}')">${ico('play',15)} Chạy</button>`:''}${x.type==='skill'||x.type==='pack'?`<button class="btn sm" onclick="mkToggle('${x.id}')">${x.enabled?'Tắt':'Bật'}</button>`:''}<button class="btn sm" onclick="mkUninstall('${x.id}')">Gỡ</button></div></div>`).join('')}</div>
    <p class="muted small" style="margin:12px 4px">Skill đang bật được superHuy áp dụng ngay trong câu trả lời. Workflow chỉ đọc và tổng hợp, không tự gửi hay đăng gì.</p>`;
}
function mkSpecBody(x){
  const sp = x.spec||{}, k = sp.kind;
  const perm = `<h3 class="mkh">Quyền và tương thích</h3><ul class="mkcontents">${(sp.permissions||[]).map(p=>`<li>${esc(p)}</li>`).join('')}${(sp.compat||[]).map(p=>`<li>${esc(p)}</li>`).join('')}</ul>`;
  if(k==='skill') return `<div class="mkspec"><div class="mkbox"><b>Kích hoạt khi</b><p>${esc(sp.trigger||'')}</p></div><div class="mkbox"><b>Thử ngay bằng câu</b>${(sp.examples||[]).map(e=>`<button class="mkex" onclick="closeSheet();S.dockOpen=true;dock();$('#dIn')&&($('#dIn').value=${JSON.stringify(e)})">“${esc(e)}”</button>`).join('')}</div></div>
    <h3 class="mkh">Skill này dạy trợ lý ${sp.rule_count?`${sp.rule_count} quy tắc`:'cách làm'}</h3><ol class="mkcontents">${(sp.rules?.length?sp.rules:sp.preview||[]).map(c=>`<li>${esc(c)}</li>`).join('')}</ol>${perm}`;
  if(k==='workflow') return `<div class="mkspec"><div class="mkbox"><b>${sp.step_count} bước · ${esc(sp.runtime||'')}</b><p>${esc(sp.output||'')}</p></div><div class="mkbox"><b>Cần kết nối</b><p>${(sp.connects||[]).length?sp.connects.map(c=>`<span class="tag role" style="margin:2px 4px 2px 0">${esc(c)}</span>`).join(''):'Không cần kết nối thêm'}</p></div></div>
    <h3 class="mkh">Các bước chạy liền nhau</h3><ol class="mkflow">${(sp.steps||[]).map(st=>`<li><b>${esc(st.label)}</b><span>${esc(st.tool)}${st.connect&&st.tool!==st.connect?` · ${esc(st.connect)}`:''}</span></li>`).join('')}</ol>
    <p class="meta">Cách chạy: ${esc(sp.how||'')}</p>${perm}`;
  if(k==='pack') return `<div class="mkspec"><div class="mkbox"><b>Phòng ban AI · ${(sp.roles||[]).length} vai</b>${(sp.roles||[]).map(r=>`<p>${esc(r)}</p>`).join('')}</div><div class="mkbox"><b>Trong gói</b><p>Skill ${sp.rule_count} quy tắc · workflow ${sp.step_count} bước · ${sp.note_count} ghi chú</p></div></div>
    <h3 class="mkh">Cách phòng ban làm việc</h3><ol class="mkcontents">${(sp.rules||[]).map(c=>`<li>${esc(c)}</li>`).join('')}</ol>
    ${sp.step_count?`<h3 class="mkh">Workflow</h3><ol class="mkflow">${(sp.steps||[]).map(st=>`<li><b>${esc(st.label)}</b><span>${esc(st.tool)}</span></li>`).join('')}</ol>`:''}
    <p class="meta">${esc(sp.how||'')}</p>${perm}`;
  if(k==='brain') return `<div class="mkspec"><div class="mkbox"><b>${sp.note_count} ghi chú · đọc ${sp.read_min} phút</b><p>Lưu vào ${esc(sp.where||'')}</p></div><div class="mkbox"><b>Xem thử: ${esc(sp.sample_title||'')}</b><p class="mksample">${esc((sp.sample||'').replace(/^# .*\n/,'').trim().slice(0,400))}${(sp.sample||'').length>400?'…':''}</p></div></div>
    <h3 class="mkh">Mục lục</h3><ol class="mkcontents mktoc">${(sp.toc||[]).map(c=>`<li>${esc(c)}</li>`).join('')}</ol>${perm}`;
  return '';
}
async function mkOpen(id){
  sheet(`<div class="empty">Đang mở…</div>`);
  let x; try{ x = await run('market','xem',{lid:id},'',true); }catch(e){ return sheet(`<div class="empty">${esc(e.message)}</div>`); }
  const tot = Object.values(x.dist||{}).reduce((a,b)=>a+b,0)||1, sp = x.spec||{};
  const cta = x.installed ? `<button class="btn" onclick="mkUninstall('${x.id}')">Gỡ</button>${x.type==='workflow'||x.type==='pack'?`<button class="btn pri" onclick="mkRun('${x.id}')">${ico('play',15)} Chạy</button>`:x.type==='skill'?`<button class="btn pri" onclick="mkToggle('${x.id}')">${x.enabled?'Đang bật · Tắt':'Đang tắt · Bật'}</button>`:''}`
    : `<button class="btn pri" onclick="mkInstall('${x.id}')">${ico('download',15)} ${esc(sp.buy_label||'Nhận')}</button>`;
  sheet(`<div class="mkdet">${mkIcon(x,84)}<div class="grow"><span class="tag lo">${esc(x.type_label)}${x.featured?' · Nổi bật':''}</span><h2 style="font-size:21px;margin-top:6px">${esc(x.name)}</h2><div class="meta">${mkBy(x)} · ${esc(x.cat_label)}</div><div style="margin-top:4px">${esc(x.tagline||'')}</div>
      <div class="row" style="margin-top:10px">${cta}<button class="btn" onclick="lbClone('${x.id}')">${ico('layers',15)} Nhân bản</button></div></div></div>
    <div class="mkfacts"><div><b>${x.rating?String(x.rating).replace('.',','):'–'}</b><span>${x.rating_n} đánh giá</span></div><div><b>${x.installs}</b><span>Lượt cài</span></div><div><b>${x.type==='brain'?sp.note_count+' ghi chú':x.type==='workflow'?sp.step_count+' bước':x.type==='pack'?'3 phần':(sp.rule_count||'')+' quy tắc'}</b><span>${x.type==='brain'?'Nội dung':x.type==='workflow'?'Chạy '+esc(sp.runtime||''):'Hướng dẫn'}</span></div><div><b>${esc(x.version)}</b><span>Phiên bản</span></div><div><b>${x.price>0?vnd(x.price):'0đ'}</b><span>${sp.billing==='monthly'?'Mỗi tháng':'Một lần'}</span></div></div>
    ${mkSpecBody(x)}
    ${x.whats_new?`<h3 class="mkh">Có gì mới</h3><p>${esc(x.whats_new)}</p>`:''}
    <h3 class="mkh">Mô tả</h3><p style="white-space:pre-line">${esc(x.description||'')}</p>
    ${x.cloned_from?`<p class="meta">Nhân bản từ “${esc(x.cloned_from.name)}” của ${esc(x.cloned_from.creator||'')}.</p>`:''}${x.source_url?`<p class="meta">Nguồn tham khảo: ${esc(x.source_url)}</p>`:''}
    <h3 class="mkh">Thông tin</h3><dl class="mkinfo">${(sp.info||[]).map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v||'–')}</dd>`).join('')}</dl>
    <h3 class="mkh">Đánh giá</h3>
    <div class="mkrate"><div><b>${x.rating?String(x.rating).replace('.',','):'–'}</b><span>trên 5</span></div><div class="grow">${Object.entries(x.dist||{}).map(([k,n])=>`<div class="mkbar"><span>${k}★</span><i><em style="width:${Math.round(n/tot*100)}%"></em></i></div>`).join('')}</div></div>
    ${(x.reviews||[]).map(r=>`<div class="card pad" style="margin-top:8px"><div class="row" style="justify-content:space-between"><b>${'★'.repeat(r.stars)}${'☆'.repeat(5-r.stars)}</b><span class="meta">${esc(r.name)} · ${esc(ago(r.at))}</span></div>${r.text?`<p style="margin:6px 0 0">${esc(r.text)}</p>`:''}</div>`).join('')}
    <div class="card pad" style="margin-top:10px"><div class="row" role="radiogroup" aria-label="Số sao">${[1,2,3,4,5].map(n=>`<button class="mkstar" data-n="${n}" onclick="document.querySelectorAll('.mkstar').forEach(b=>b.classList.toggle('on',+b.dataset.n<=${n}));S.mk.st=${n}" aria-label="${n} sao">★</button>`).join('')}</div>
      <label class="field" style="margin:8px 0"><span>Nhận xét của anh</span><textarea id="mkRv" style="min-height:70px" placeholder="Điều anh thích, điều cần cải thiện"></textarea></label><button class="btn sm pri" onclick="mkReview('${x.id}')">Gửi đánh giá</button></div>`);
}
async function mkInstall(id){ toast('Đang cài…'); try{ const r = await run('market','cai',{lid:id},'Cài sản phẩm'); toast(r.text, 4200); notifyH('success'); closeSheet(); await mkLoad(true); }catch(e){ toast(e.message); } }
async function mkUninstall(id){ try{ const r = await run('market','go',{lid:id},'',true); toast(r.text, 3800); closeSheet(); mkLoad(true); }catch(e){ toast(e.message); } }
async function mkToggle(id){ try{ const r = await run('market','batat',{lid:id},'',true); toast(r.text); mkLoad(true); }catch(e){ toast(e.message); } }
async function mkReview(id){ try{ const r = await run('market','danhgia',{lid:id, stars:S.mk.st||5, text:$('#mkRv').value},'',true); toast(r.text); S.mk.st=0; mkOpen(id); mkLoad(true); }catch(e){ toast(e.message); } }
async function mkRun(id){
  toast('superHuy đang chạy workflow…', 3000);
  try{ const r = await run('market','chay',{lid:id},'Chạy workflow'); S.mk.out = r.text||''; sheet(`<h2>Kết quả workflow</h2><div class="md" style="white-space:pre-line;margin-top:10px">${esc(r.text||'')}</div>
    <div class="row" style="margin-top:14px"><button class="btn" onclick="copyText(S.mk.out||'')">${ico('copy',15)} Sao chép</button></div>`); }catch(e){ toast(e.message); }
}

/* ---------- Quản trị cao nhất (chủ App Store) */
async function qtLoad(){ try{ S.mk.adm = await run('market','quantri',{},'',true); }catch(e){ toast(e.message); } if(S.tab==='mkt' && S.mk.view==='qt' && !$('#sheet').classList.contains('on')) render(); }
function vQt(){
  const a = S.mk.adm; if(!a){ qtLoad(); return `<div class="card empty">Đang tải bảng quản trị…</div>`; }
  const k = a.kpi, t = S.mk.admTab; if(t==='gd' && !S.mk.gd) gdLoad(); if(!S.mk.kn) knLoad();
  const kp = [['Đang bán',k.published],['Chờ duyệt',k.review,k.review?'warn':''],['Người tạo',k.creators],['Lượt cài',k.installs],['Khách quan tâm',k.interest],['Giá trị quan tâm',money(k.pipeline)],['Đánh giá TB',k.rating?String(k.rating).replace('.',','):'–'],['Tổng sản phẩm',k.listings]];
  const queue = a.listings.filter(x=>x.status==='review');
  const ST = {published:'Đang bán', review:'Chờ duyệt', draft:'Nháp', rejected:'Từ chối', archived:'Đã gỡ'};
  let body = '';
  if(t==='cho') body = queue.length ? queue.map(x=>`<article class="card pad mkq">${mkIcon(x,44)}<div class="grow"><div class="ttl2">${esc(x.name)}</div><div class="meta">${esc(x.type_label)} · ${esc(x.creator?.name||'')} · ${esc(x.submitter?.email||'')} · ${vnd(x.price)}</div><p style="margin:6px 0">${esc(x.tagline||'')}</p>
      <div class="row"><button class="btn sm" onclick="mkOpen('${x.id}')">Xem chi tiết</button></div>
      <label class="field" style="margin:10px 0 8px"><span>Ghi chú cho người tạo</span><input type="text" id="qn_${x.id}" placeholder="Lý do từ chối hoặc lời nhắn"></label>
      <div class="row"><button class="btn sm pri" onclick="qtQuick('${x.id}')">${ico('spark',15)} Gợi ý giá và duyệt</button><button class="btn sm" onclick="qtSet('${x.id}','status','published')">Lên kệ giữ giá ${vnd(x.price)}</button><button class="btn sm" onclick="qtSet('${x.id}','status','rejected')">Từ chối</button></div></div></article>`).join('')
      : `<div class="card empty">Không có sản phẩm nào chờ duyệt. Sản phẩm người tạo gửi lên sẽ hiện ở đây, superHuy cũng nhắn anh qua Telegram.</div>`;
  if(t==='sp'){
    const rows = a.listings.filter(x=>S.mk.admFilter==='all'||x.status===S.mk.admFilter);
    body = `<div class="chips">${['all','published','review','draft','rejected','archived'].map(s=>`<button class="chip ${S.mk.admFilter===s?'on':''}" onclick="S.mk.admFilter='${s}';render()">${s==='all'?'Tất cả':ST[s]} ${s==='all'?a.listings.length:(a.by_status[s]||0)}</button>`).join('')}</div>
      <div class="card mklist">${rows.map(x=>`<div class="mkrow">${mkIcon(x,40)}<div class="grow"><div class="ttl2">${esc(x.name)}${x.featured?' <b class="mkoff">Nổi bật</b>':''}</div><div class="meta">${esc(ST[x.status]||x.status)} · ${esc(x.creator?.name||'')} · ${vnd(x.price)} · ${x.installs} cài · ${x.interest} quan tâm</div></div>
        <div class="row"><button class="btn sm" onclick="qtSet('${x.id}','featured','${x.featured?'false':'true'}')">${x.featured?'Bỏ nổi bật':'Nổi bật'}</button>${x.status==='published'?`<button class="btn sm" onclick="qtSet('${x.id}','status','archived')">Gỡ</button>`:`<button class="btn sm" onclick="qtSet('${x.id}','status','published')">Lên kệ</button>`}<button class="btn sm" onclick="qtPrice('${x.id}',${x.price})">Giá</button></div></div>`).join('') || '<div class="empty">Không có sản phẩm.</div>'}</div>`;
  }
  if(t==='nt') body = a.creators.length ? `<div class="card mklist">${a.creators.map(c=>`<div class="mkrow"><span class="thumb">${ico('home',20)}</span><div class="grow"><div class="ttl2">${esc(c.name)} ${c.status==='suspended'?'<span class="tag hi">Đang khoá</span>':''}</div><div class="meta">${esc(c.email)} · ${c.published}/${c.products} đang bán · ${c.installs} cài · ${c.interest} quan tâm · từ ${esc((c.created||'').slice(0,10))}</div></div>
      <div class="row">${c.status==='suspended'?`<button class="btn sm" onclick="qtCreator('${c.id}','mo')">Mở khoá</button>`:`<button class="btn sm" onclick="qtCreator('${c.id}','khoa')">Khoá</button>`}<button class="btn sm" onclick="qtCreator('${c.id}','capkhoa')">Cấp khoá mới</button></div></div>`).join('')}</div>`
      : `<div class="card empty">Chưa có người tạo nào. Người ngoài đăng ký bán ở trang công khai › Bán trên superYou.</div>`;
  if(t==='nk') body = `<div class="card mklist">${a.log.map(l=>`<div class="mkrow"><div class="grow"><div>${esc(l.what)}</div><div class="meta">${esc(l.who)} · ${esc(ago(l.at))}</div></div></div>`).join('') || '<div class="empty">Chưa có hoạt động.</div>'}</div>`;
  return `<div class="kpis mkkpis">${kp.map(([l,v,c])=>`<div class="card kpi ${c||''}"><b>${v}</b><span>${l}</span></div>`).join('')}</div>
    <div class="seg" style="margin:16px 0 12px;flex-wrap:wrap"><button class="${t==='cho'?'on':''}" onclick="S.mk.admTab='cho';render()">Chờ duyệt ${queue.length||''}</button><button class="${t==='gd'?'on':''}" onclick="S.mk.admTab='gd';render()">Giao dịch${S.mk.gd?.kpi?.pending?` <em class="mkbadge">${S.mk.gd.kpi.pending}</em>`:''}</button><button class="${t==='kn'?'on':''}" onclick="S.mk.admTab='kn';render()">Khiếu nại${S.mk.kn?.kpi?.new?` <em class="mkbadge">${S.mk.kn.kpi.new}</em>`:''}</button><button class="${t==='sp'?'on':''}" onclick="S.mk.admTab='sp';render()">Sản phẩm</button><button class="${t==='nt'?'on':''}" onclick="S.mk.admTab='nt';render()">Người tạo</button><button class="${t==='nk'?'on':''}" onclick="S.mk.admTab='nk';render()">Nhật ký</button></div>${t==='gd'?vGd():t==='kn'?vKn():body}
    <p class="muted small" style="margin:14px 4px">Chỉ anh thấy trang này. Sàn giữ 20% mỗi lượt bán của người tạo khác; sản phẩm chính chủ 100% về anh.</p>`;
}
async function gdLoad(){ try{ S.mk.gd = await run('market','gd',{},'',true); }catch(e){ toast(e.message); S.mk.gd={kpi:{},orders:[],owed:[],payouts:[],config:{}}; } if(S.tab==='mkt' && S.mk.view==='qt' && !$('#sheet').classList.contains('on')) render(); }
function vGd(){
  const g = S.mk.gd; if(!g) return `<div class="card empty">Đang tải giao dịch…</div>`;
  const k = g.kpi, c = g.config||{};
  const setup = [['Tài khoản nhận tiền (VietQR)', c.vietqr_ready, 'Điền BANK_ID, BANK_ACCOUNT, BANK_ACCOUNT_NAME vào .env trên VPS'],['Đối soát tự động (Casso/SePay)', c.webhook_ready, 'Điền PAY_WEBHOOK_TOKEN và trỏ webhook về /api/pay/webhook'],['PayOS (giai đoạn 2)', c.payos_ready, 'Điền PAYOS_CLIENT_ID, PAYOS_API_KEY, PAYOS_CHECKSUM_KEY'],['Email hoá đơn', c.mail_ready, 'Kết nối Gmail hoặc Lark Mail trong Cài đặt']];
  const pend = g.orders.filter(o=>o.status==='pending');
  return `<div class="kpis mkkpis"><div class="card kpi"><b>${money(k.gross||0)}</b><span>Tổng bán</span></div><div class="card kpi"><b>${money(k.fee||0)}</b><span>Về sàn (anh)</span></div><div class="card kpi"><b>${money(k.month||0)}</b><span>Tháng này</span></div><div class="card kpi ${k.pending?'warn':''}"><b>${k.pending||0}</b><span>Đơn chờ tiền</span></div><div class="card kpi"><b>${money(k.owed||0)}</b><span>Nợ người bán</span></div><div class="card kpi"><b>${k.refunds||0}</b><span>Hoàn tiền</span></div></div>
    <div class="sec"><h2>Thiết lập thanh toán</h2></div><div class="card list">${setup.map(([l,ok,h])=>`<div><span class="st ${ok?'ok':'no'}"></span><div class="grow"><div style="font-weight:600">${l}</div><div class="meta">${ok?'Sẵn sàng':h}</div></div></div>`).join('')}</div>
    ${pend.length?`<div class="sec"><h2>Đơn chờ thanh toán</h2></div><div class="card mklist">${pend.map(o=>`<div class="mkrow"><div class="grow"><div class="ttl2">${esc(o.code)} · ${esc(o.name)}</div><div class="meta">${esc(o.email)} · ${vnd(o.amount)} · ${esc(ago(o.created))}</div></div><div class="row"><button class="btn sm pri" onclick="gdConfirm('${o.id}')">Đã nhận tiền</button></div></div>`).join('')}</div>`:''}
    ${g.owed.length?`<div class="sec"><h2>Trả người bán</h2></div><div class="card mklist">${g.owed.map(v=>`<div class="mkrow"><div class="grow"><div class="ttl2">${esc(v.name)} ${v.due?'<span class="tag mid">Đến hạn</span>':''}</div><div class="meta">Số dư ${vnd(v.balance)} · đã trả ${vnd(v.paid)} · ${v.bank?.account?`${esc(v.bank.bank)} ${esc(v.bank.account)} (${esc(v.bank.name)})`:'chưa có tài khoản nhận'}</div></div><div class="row">${v.balance>0?`<button class="btn sm" onclick="gdPayout('${v.id}',${v.balance})">Ghi đã trả</button>`:''}</div></div>`).join('')}</div>`:''}
    <div class="sec"><h2>Giao dịch gần đây</h2></div><div class="card mklist">${g.orders.slice(0,40).map(o=>`<div class="mkrow"><div class="grow"><div class="ttl2">${esc(o.code)} · ${esc(o.name)}</div><div class="meta">${esc(o.email)} · ${vnd(o.amount)}${o.fee!=null?` · sàn ${vnd(o.fee)}`:''} · ${esc(o.status_text)} · ${esc(ago(o.paid_at||o.created))}</div></div><div class="row">${['paid','delivered'].includes(o.status)?`<button class="btn sm" onclick="gdRefund('${o.id}')">Hoàn tiền</button>`:''}</div></div>`).join('')||'<div class="empty">Chưa có giao dịch. Đơn từ trang công khai sẽ hiện ở đây.</div>'}</div>`;
}
async function gdConfirm(id){ try{ const r = await run('market','gd_nhan',{oid:id},'',true); toast(r.text,4000); S.mk.gd=null; gdLoad(); }catch(e){ toast(e.message); } }
function gdRefund(id){ sheet(`<h2>Hoàn tiền</h2><label class="field" style="margin-top:12px"><span>Lý do</span><textarea id="gdN"></textarea></label><button class="btn pri full" onclick="closeSheet();run('market','gd_hoan',{oid:'${id}',note:$('#gdN').value},'',true).then(r=>{toast(r.text,4500);S.mk.gd=null;gdLoad()}).catch(e=>toast(e.message))">Ghi hoàn tiền</button><p class="muted small">superYou ghi sổ; anh chuyển khoản trả khách thủ công.</p>`); }
function gdPayout(sid, bal){ sheet(`<h2>Ghi đã trả người bán</h2><label class="field" style="margin-top:12px"><span>Số tiền (số dư ${vnd(bal)})</span><input type="number" id="gdA" value="${bal}" min="1000" step="1000"></label><label class="field"><span>Mã giao dịch ngân hàng</span><input type="text" id="gdR"></label><button class="btn pri full" onclick="closeSheet();run('market','gd_tra',{sid:'${sid}',amount:$('#gdA').value,ref:$('#gdR').value},'',true).then(r=>{toast(r.text,4000);S.mk.gd=null;gdLoad()}).catch(e=>toast(e.message))">Ghi đã trả</button>`); }
async function qtQuick(id){
  let r; try{ r = await run('market','goi_y_gia',{lid:id},'',true); }catch(e){ return toast(e.message); }
  priceSheet(r, (price, billing, featured)=>run('market','qt_duyet_gia',{lid:id, price, billing, featured},'',true).then(x=>{ toast(x.text,4000); closeSheet(); S.mk.adm=null; S.mk.data=null; qtLoad(); mkLoad(true); }).catch(e=>toast(e.message)));
}
function priceSheet(r, onOk){
  const tiers = r.tiers||[0,29000,49000,99000,199000,299000];
  sheet(`<h2>Gợi ý giá: ${esc(r.name||'')}</h2><div class="card pad" style="margin-top:10px"><b>Đề xuất ${vnd(r.tier)} · ${r.billing==='monthly'?'mỗi tháng':'một lần'}</b><p style="margin:6px 0 0">${esc(r.why||'')}</p><p class="meta">Đối tượng: ${esc(r.audience||'')}</p></div>
    <h3 class="mkh">Chọn bậc giá</h3><div class="row" role="radiogroup">${tiers.map(t=>`<label class="lbt" style="flex:1 1 90px"><input type="radio" name="pt" value="${t}" ${t===r.tier?'checked':''}><span>${t?vnd(t):'Miễn phí'}</span></label>`).join('')}</div>
    <label class="field" style="margin-top:10px"><span>Hoặc giá khác (đồng)</span><input type="number" id="ptX" min="0" step="1000" placeholder="Để trống nếu dùng bậc trên"></label>
    <label class="lbopt"><input type="checkbox" id="ptM" ${r.billing==='monthly'?'checked':''}><span>Thu theo tháng (thuê bao)</span></label><label class="lbopt"><input type="checkbox" id="ptF"><span>Đưa lên mục nổi bật</span></label>
    <button class="btn pri full" style="margin-top:12px" onclick="window.__priceOk()">${ico('check',16)} Duyệt lên kệ</button>`);
  window.__priceOk = ()=>{ const x = $('#ptX').value; const price = x!=='' ? +x : +(document.querySelector('input[name=pt]:checked')||{}).value||0; onOk(price, $('#ptM').checked?'monthly':'once', $('#ptF').checked); };
}
async function qtSet(id, field, value){ const note = $('#qn_'+id)?.value||''; try{ const r = await run('market','qt_sua',{lid:id, field, value, note},'',true); toast(r.text, 3500); S.mk.adm=null; S.mk.data=null; qtLoad(); mkLoad(true); }catch(e){ toast(e.message); } }
function qtPrice(id, cur){ sheet(`<h2>Đổi giá</h2><label class="field" style="margin-top:12px"><span>Giá (đồng, 0 = miễn phí)</span><input type="number" id="qtp" inputmode="numeric" value="${cur}" min="0" step="1000"></label><button class="btn pri full" onclick="closeSheet();qtSet('${id}','price',$('#qtp').value)">Lưu giá</button>`); }
async function qtCreator(cid, action){
  try{ const r = await run('market','qt_nguoitao',{cid, action},'',true); S.mk.adm=null; qtLoad();
    if(r.key) sheet(`<h2>Khoá truy cập mới</h2><p class="meta">${esc(r.text)}</p><div class="card pad" style="margin-top:12px;font-family:ui-monospace,monospace;word-break:break-all">${esc(r.key)}</div><button class="btn pri full" style="margin-top:12px" onclick="copyText('${esc(r.key)}')">Sao chép khoá</button><p class="muted small">Khoá chỉ hiện một lần.</p>`);
    else toast(r.text, 3500); }catch(e){ toast(e.message); }
}

/* =================================================================== Phòng Phát triển sản phẩm số (chỉ chủ nhân) */
S.lb = { view:'xuong', src:'ios', country:'vn', chart:'free', genre:'', q:'', scan:null, mine:null, proj:null, opts:['feature_clone','vn_local','fix_pain','ai_native'] };
async function lbScan(force){
  if(S.lb.scan && !force) return;
  S.lb.scan = {loading:true};
  if(S.tab==='lab') render();
  try{ S.lb.scan = await run('xuong','quet',{src:S.lb.src, country:S.lb.country, chart:S.lb.chart, genre:S.lb.genre, q:S.lb.q},'',true); }catch(e){ S.lb.scan = {error:e.message, items:[]}; }
  if((S.tab==='lab'||(S.tab==='mkt'&&S.mk.view==='xuong')) && !$('#sheet').classList.contains('on')) render();
}
async function lbMine(){ try{ const [m, p] = await Promise.all([run('market','cuatoi',{},'',true), run('xuong','duan_ds',{},'',true)]); S.lb.mine = m; S.lb.proj = p; }catch(e){ toast(e.message); S.lb.mine={mine:[],queue:[],stats:{}}; S.lb.proj={items:[],statuses:{},targets:{}}; } if((S.tab==='lab'||(S.tab==='mkt'&&S.mk.view==='xuong')) && !$('#sheet').classList.contains('on')) render(); }
function vLab(){
  const head = `<div class="date">Phòng Phát triển sản phẩm số · chỉ anh thấy</div><h1>Sản phẩm số</h1>
    <div class="row" style="margin-bottom:14px;justify-content:flex-end"><button class="btn sm pri" onclick="lbNew()">${ico('plus',16)} Tạo tài sản</button><button class="btn sm" onclick="go('mkt')">Marketplace</button></div>`;
  return head + vLabInner();
}
function vLabInner(){
  const v = S.lb.view;
  const head = `<div class="seg" style="margin-bottom:12px"><button class="${v==='xuong'?'on':''}" onclick="S.lb.view='xuong';render()">Săn sản phẩm</button><button class="${v==='duan'?'on':''}" onclick="S.lb.view='duan';render()">Dự án${S.lb.proj?.items?.length?` ${S.lb.proj.items.length}`:''}</button><button class="${v==='taisan'?'on':''}" onclick="S.lb.view='taisan';render()">Tài sản của anh</button></div>`;
  if(!S.lb.mine) lbMine();
  if(v==='taisan') return head + lbAssets();
  if(v==='duan') return head + lbProjects();
  const sc = S.lb.scan; if(!sc) lbScan();
  const f = sc?.filters || {sources:{ios:'App Store iPhone',mac:'Mac App Store',github:'GitHub Trending',ph:'Product Hunt'}, countries:{vn:'Việt Nam',us:'Mỹ'}, charts:{free:'Miễn phí hàng đầu',paid:'Trả phí hàng đầu',grossing:'Doanh thu cao nhất'}, genres:{'':'Mọi danh mục'}};
  const apple = ['ios','mac'].includes(S.lb.src);
  const sel = (id, obj, cur, on) => `<select id="${id}" aria-label="${id}" onchange="${on}">${Object.entries(obj).map(([k,l])=>`<option value="${k}" ${k===cur?'selected':''}>${esc(l)}</option>`).join('')}</select>`;
  const bar = `<div class="lbbar"><div class="seg">${Object.entries(f.sources).map(([k,l])=>`<button class="${S.lb.src===k?'on':''}" onclick="S.lb.src='${k}';S.lb.q='';lbScan(true)">${esc(l)}</button>`).join('')}</div>
    <div class="row">${apple?sel('lbC', f.countries, S.lb.country, "S.lb.country=this.value;lbScan(true)") + sel('lbK', f.charts, S.lb.chart, "S.lb.chart=this.value;lbScan(true)") + sel('lbG', f.genres, S.lb.genre, "S.lb.genre=this.value;lbScan(true)"):''}</div>
    ${S.lb.src!=='ph'?`<form class="hask" style="margin:0" onsubmit="event.preventDefault();S.lb.q=$('#lbq').value.trim();lbScan(true)"><input id="lbq" value="${esc(S.lb.q)}" placeholder="${apple?'Tìm app theo từ khoá…':'Tìm repo theo chủ đề…'}" autocomplete="off" enterkeyhint="search"><button class="go" aria-label="Tìm">${ico('arrow',20)}</button></form>`:''}</div>`;
  if(!sc || sc.loading) return head + bar + `<div class="card empty"><span class="spin" style="width:16px;height:16px;display:inline-block;vertical-align:-3px"></span> Đang quét ${esc(f.sources[S.lb.src]||'')}…</div>`;
  if(sc.error) return head + bar + `<div class="card empty">${esc(sc.error)} <button class="link" onclick="lbScan(true)">Thử lại</button></div>`;
  return head + bar + `<p class="meta" style="margin:10px 2px">${esc(sc.label||'')} · ${sc.items.length} sản phẩm. Bấm một sản phẩm để xem và clone.</p>
    <div class="lbgrid">${sc.items.map(x=>`<button class="card lbcard ${x.cloned?'cloned':''}" onclick="lbOpen('${esc(x.key)}')">${x.cloned?'<span class="lbtag">Đã clone</span>':''}
      ${x.icon?`<img src="${esc(x.icon)}" alt="" loading="lazy" referrerpolicy="no-referrer">`:`<span class="mkicon" style="--c:#2457C5;width:56px;height:56px">${ico(x.src==='github'?'code':'spark',24)}</span>`}
      <b class="clamp2">${esc(x.name)}</b><span class="meta clamp1">${esc(x.dev||'')}</span>
      <span class="meta">${x.rank?`#${x.rank} · `:''}${x.rating?`★ ${x.rating} `:''}${x.ratings?`(${nf(x.ratings)}${x.src==='github'?' sao':''}) `:''}${esc(x.price||'')}</span><span class="tag lo">${esc(x.cat||'')}</span></button>`).join('')}</div>`;
}
async function lbOpen(key, tab){
  S.lb.cur = S.lb.cur && S.lb.cur.key===key ? S.lb.cur : null; S.lb.tab = tab || S.lb.tab || 'info';
  if(!S.lb.cur){ sheet(`<div class="empty"><span class="spin" style="width:16px;height:16px;display:inline-block;vertical-align:-3px"></span> Đang đọc chi tiết, ảnh và đánh giá…</div>`);
    try{ S.lb.cur = await run('xuong','xem',{key, country:S.lb.country},'',true); }catch(e){ return sheet(`<div class="empty">${esc(e.message)}</div>`); } }
  const x = S.lb.cur, t = S.lb.tab;
  const tabs = [['info','Thông tin'],['shots',`Ảnh ${x.shots?.length||0}`],['clone','Clone'],['reviews',`Đánh giá ${x.reviews?.length||0}`],['dev',`Nhà phát triển ${x.dev_apps?.length||0}`]];
  let b = '';
  if(t==='info') b = `<div class="mkfacts"><div><b>${x.rating||'–'}</b><span>${nf(x.ratings||0)} ${x.src==='github'?'sao':'đánh giá'}</span></div><div><b>${esc(x.price||'–')}</b><span>${x.src==='github'?'Giấy phép':'Giá'}</span></div><div><b>${esc(x.cat||'')}</b><span>Danh mục</span></div><div><b>${esc(x.updated||'–')}</b><span>Cập nhật</span></div></div>
    ${x.url?`<button class="btn sm" onclick="openLink('${esc(x.url)}')">${ico('link',15)} Mở trang gốc</button>`:''}
    ${x.pain?.length?`<h3 class="mkh">Người dùng đang phàn nàn</h3>${x.pain.map(r=>`<div class="card pad" style="margin-top:6px"><b>${'★'.repeat(r.stars)}</b> ${esc(r.title)}<p class="meta" style="margin:4px 0 0">${esc(r.text)}</p></div>`).join('')}`:''}
    <h3 class="mkh">Mô tả</h3><p style="white-space:pre-line">${esc((x.description||x.summary||'').slice(0,3000))}</p>`;
  if(t==='shots') b = x.shots?.length ? `<div class="lbshots">${x.shots.map(u=>`<img src="${esc(u)}" alt="Ảnh màn hình" loading="lazy" referrerpolicy="no-referrer">`).join('')}</div>` : `<div class="empty">Nguồn này không có ảnh màn hình.</div>`;
  if(t==='reviews') b = x.reviews?.length ? `<p class="meta">Trung bình ${x.review_avg}★ trên ${x.reviews.length} đánh giá gần đây.</p>${x.reviews.map(r=>`<div class="card pad" style="margin-top:6px"><div class="row" style="justify-content:space-between"><b>${'★'.repeat(r.stars)}${'☆'.repeat(5-r.stars)} ${esc(r.title)}</b><span class="meta">${esc(r.author)}</span></div><p style="margin:4px 0 0">${esc(r.text)}</p></div>`).join('')}` : `<div class="empty">Chưa có đánh giá ở cửa hàng này.</div>`;
  if(t==='dev') b = x.dev_apps?.length ? `<p class="meta">Sản phẩm khác của ${esc(x.dev)}</p><div class="lbgrid" style="margin-top:8px">${x.dev_apps.map(a=>`<button class="card lbcard" onclick="S.lb.cur=null;S.lb.tab='info';lbOpen('${esc(a.key)}')"><img src="${esc(a.icon)}" alt="" loading="lazy" referrerpolicy="no-referrer"><b class="clamp2">${esc(a.name)}</b><span class="meta">${a.rating?`★ ${a.rating} `:''}${esc(a.price||'')}</span></button>`).join('')}</div>` : `<div class="empty">Không có thông tin nhà phát triển.</div>`;
  if(t==='clone') b = `${x.cloned?`<div class="card pad" style="margin-bottom:10px">Đã clone sản phẩm này. <button class="link" onclick="lbProject('${x.project}')">Mở dự án</button></div>`:''}
    <h3 class="mkh" style="margin-top:4px">Nền tảng đích</h3><div class="lbtargets">${Object.entries(x.targets).map(([k,l],i)=>`<label class="lbt"><input type="radio" name="lbT" value="${k}" ${(S.lb.target||'web')===k?'checked':''} onchange="S.lb.target=this.value"><span>${esc(l)}</span></label>`).join('')}</div>
    <label class="field" style="margin-top:12px"><span>Tên dự án</span><input type="text" id="lbP" value="${esc((x.name||'').replace(/[^\p{L}\p{N} ]/gu,'').split(' ').slice(0,2).join(''))}Clone"></label>
    <h3 class="mkh">Cấu hình clone</h3>${Object.entries(x.options).map(([k,l])=>`<label class="lbopt"><input type="checkbox" value="${k}" ${S.lb.opts.includes(k)?'checked':''} onchange="S.lb.opts=this.checked?[...new Set([...S.lb.opts,'${k}'])]:S.lb.opts.filter(o=>o!=='${k}')"><span>${esc(l)}</span></label>`).join('')}
    <h3 class="mkh">Ghi chú và yêu cầu riêng</h3>
    ${x.notes?.length?`<select id="lbSaved" onchange="if(this.value){$('#lbN').value=($('#lbN').value?$('#lbN').value+'\\n':'')+this.value;this.value=''}"><option value="">Ghi chú đã lưu (${x.notes.length})…</option>${x.notes.map(n=>`<option value="${esc(n)}">${esc(n.slice(0,60))}</option>`).join('')}</select>`:''}
    <label class="field" style="margin-top:8px"><span class="sr">Ghi chú</span><textarea id="lbN" style="min-height:90px" placeholder="Tính năng muốn nhấn mạnh, phong cách giao diện, kiến trúc…"></textarea></label>
    <div class="chips" style="padding-top:0">${x.chips.map(c=>`<button class="chip" onclick="$('#lbN').value=($('#lbN').value?$('#lbN').value+', ':'')+'${esc(c)}'">+ ${esc(c)}</button>`).join('')}</div>
    <div class="row" style="margin-top:8px"><button class="btn sm" onclick="run('xuong','ghichu',{text:$('#lbN').value},'',true).then(r=>toast(r.text)).catch(e=>toast(e.message))">${ico('save',15)} Lưu ghi chú</button></div>
    <button class="btn pri full" style="margin-top:14px" onclick="lbDoClone('${esc(x.key)}')">${ico('spark',17)} Dựng bản thiết kế bằng AI</button>
    <p class="muted small">superHuy giữ ý tưởng và tính năng đã được kiểm chứng, sửa điểm người dùng phàn nàn, còn tên, giao diện, câu chữ và hình ảnh là của anh.</p>`;
  sheet(`<div class="mkdet">${x.icon?`<img class="lbicon" src="${esc(x.icon)}" alt="" referrerpolicy="no-referrer">`:mkIcon({type:'skill',color:'#2457C5'},72)}<div class="grow"><h2 style="font-size:20px">${esc(x.name)}</h2><div class="meta">${esc(x.dev||'')} · ${esc(x.cat||'')}</div>
      <div class="row" style="margin-top:8px"><button class="btn sm" onclick="run('xuong','theodoi',{key:'${esc(x.key)}'},'',true).then(r=>{toast(r.text);S.lb.cur.starred=r.starred})">${ico('star',15)} ${x.starred?'Đang theo dõi':'Theo dõi'}</button></div></div></div>
    <div class="seg lbtabs" role="tablist">${tabs.map(([k,l])=>`<button role="tab" aria-selected="${t===k}" class="${t===k?'on':''}" onclick="lbOpen('${esc(x.key)}','${k}')">${l}</button>`).join('')}</div><div style="margin-top:12px">${b}</div>`);
}
async function lbDoClone(key){
  const target = (document.querySelector('input[name=lbT]:checked')||{}).value || 'web';
  const notes = $('#lbN')?.value||'', project = $('#lbP')?.value||'';
  closeSheet(); toast('superHuy đang dựng bản thiết kế, khoảng 1–2 phút', 4000);
  try{ const r = await run('xuong','clone',{key, target, options:S.lb.opts.join(','), notes, project, country:S.lb.country},'Dựng bản thiết kế');
    notifyH('success'); S.lb.cur=null; S.lb.proj=null; lbMine(); if(S.lb.scan?.items){ const it=S.lb.scan.items.find(i=>i.key===key); if(it) it.cloned=true; } lbProject(r.project.id); }catch(e){ toast(e.message, 4000); }
}
function lbProjects(){
  const p = S.lb.proj; if(!p) return `<div class="card empty">Đang tải dự án…</div>`;
  if(!p.items.length) return `<div class="done"><b>Chưa có dự án nào</b>Vào Xưởng clone, chọn một sản phẩm đang thắng thị trường rồi bấm Clone. superHuy sẽ dựng bản thiết kế và prompt để dựng sản phẩm của anh.<div class="row" style="justify-content:center;margin-top:16px"><button class="btn pri" onclick="S.lb.view='xuong';render()">Mở Xưởng clone</button></div></div>`;
  return `<div class="card mklist">${p.items.map(x=>`<div class="mkrow" role="button" tabindex="0" onclick="lbProject('${x.id}')">${x.source?.icon?`<img class="lbmini" src="${esc(x.source.icon)}" alt="" referrerpolicy="no-referrer">`:`<span class="thumb">${ico('layers',20)}</span>`}<div class="grow"><div class="ttl2">${esc(x.name)}</div><div class="meta">Từ ${esc(x.source?.name||'')} · ${esc(p.targets[x.target]||x.target)}${x.mvp_days?` · khoảng ${x.mvp_days} ngày`:''}</div></div><span class="tag ${x.status==='da_ra_mat'?'role':x.status==='bo'?'lo':'mid'}">${esc(p.statuses[x.status]||x.status)}</span></div>`).join('')}</div>`;
}
async function lbProject(pid){
  let p; try{ p = await run('xuong','duan',{pid},'',true); }catch(e){ return toast(e.message); }
  const mk = ['skill','workflow','brain'].includes(p.target); S.lb.prompt = p.build_prompt||'';
  sheet(`<div class="date">Dự án từ ${esc(p.source?.name||'')} · ${esc(p.targets[p.target]||'')}</div><h2 style="font-size:22px;margin-top:4px">${esc(p.name)}</h2><p style="margin:6px 0 0">${esc(p.pitch||'')}</p>
    <div class="row" style="margin-top:10px">${Object.entries(p.statuses).map(([k,l])=>`<button class="chip ${p.status===k?'on':''}" onclick="run('xuong','duan_sua',{pid:'${p.id}',status:'${k}'},'',true).then(r=>{toast(r.text);S.lb.proj=null;lbMine();lbProject('${p.id}')})">${esc(l)}</button>`).join('')}</div>
    <h3 class="mkh">Cơ hội</h3><p>${esc(p.opportunity||'')}</p>
    <h3 class="mkh">Tính năng</h3><ol class="mkcontents">${(p.features||[]).map(f=>`<li>${esc(f)}</li>`).join('')}</ol>
    ${p.improvements?.length?`<h3 class="mkh">Làm tốt hơn bản gốc</h3><ul class="mkcontents">${p.improvements.map(f=>`<li>${esc(f)}</li>`).join('')}</ul>`:''}
    <h3 class="mkh">Kiếm tiền</h3><p>${esc(p.monetization||'')}</p>
    <h3 class="mkh">${mk?'Nội dung sản phẩm':'Prompt dựng sản phẩm'}</h3><pre class="lbprompt">${esc(p.build_prompt||'')}</pre>
    <div class="row" style="margin-top:10px"><button class="btn pri" onclick="copyText(S.lb.prompt||'')">${ico('copy',15)} Sao chép prompt</button>
      ${mk?`<button class="btn pri" onclick="lbPriceApprove('${p.id}')">${ico('spark',15)} Gợi ý giá và lên kệ</button><button class="btn" onclick="lbToMarket('${p.id}')">${ico('send',15)} Lưu nháp vào Marketplace</button>`:''}
      <button class="btn" onclick="if(confirmTap(this))run('xuong','duan_xoa',{pid:'${p.id}'},'',true).then(r=>{toast(r.text);closeSheet();S.lb.proj=null;lbMine()})">Xoá dự án</button></div>
    ${!mk?`<p class="muted small">Dán prompt này vào Claude Code (hoặc giao cho em trong phiên Product) để dựng bản đầu tiên.</p>`:''}`);
}
function confirmTap(b){ if(b.dataset.ok) return true; b.dataset.ok='1'; b.textContent='Bấm lần nữa để xoá'; setTimeout(()=>{ delete b.dataset.ok; b.textContent='Xoá dự án'; }, 3000); return false; }
async function lbPriceApprove(pid){
  let r; try{ r = await run('xuong','goi_y_gia',{pid},'',true); }catch(e){ return toast(e.message); }
  priceSheet(r, async (price, billing, featured)=>{ try{ const x = await run('xuong','len_cho',{pid, publish:true, price},'',true); if(billing==='monthly'||featured) await run('market','qt_duyet_gia',{lid:x.id, price, billing, featured},'',true); toast('Đã lên kệ với giá '+(price?vnd(price):'miễn phí'), 4000); closeSheet(); S.lb.mine=null; S.lb.proj=null; S.mk.data=null; lbMine(); mkLoad(true); }catch(e){ toast(e.message); } });
}
async function lbToMarket(pid){ try{ const r = await run('xuong','len_cho',{pid},'',true); toast(r.text+' Xem ở Tài sản của anh.', 4000); closeSheet(); S.lb.view='taisan'; S.lb.mine=null; S.lb.proj=null; lbMine(); render(); }catch(e){ toast(e.message); } }
function lbAssets(){
  const m = S.lb.mine; if(!m) return `<div class="card empty">Đang tải…</div>`;
  const ST = {published:'Đang bán', review:'Chờ duyệt', draft:'Nháp', rejected:'Từ chối', archived:'Đã gỡ'};
  return `<div class="kpis mkkpis"><div class="card kpi"><b>${m.stats.products||0}</b><span>Sản phẩm</span></div><div class="card kpi"><b>${m.stats.installs||0}</b><span>Lượt cài</span></div><div class="card kpi"><b>${m.stats.interest||0}</b><span>Khách quan tâm</span></div></div>
    <div class="sec"><h2>Tài sản của anh</h2><button class="link" onclick="lbNew()">Tạo mới</button></div>
    <div class="card mklist">${m.mine.map(x=>`<div class="mkrow">${mkIcon(x,44)}<div class="grow" role="button" tabindex="0" onclick="lbEdit('${x.id}')"><div class="ttl2">${esc(x.name)}${x.featured?' <b class="mkoff">Nổi bật</b>':''}</div><div class="meta">${esc(x.type_label)} · ${esc(ST[x.status]||x.status)} · ${vnd(x.price)} · ${x.installs} cài</div></div>
      <div class="row"><button class="btn sm" onclick="lbEdit('${x.id}')">Sửa</button><button class="btn sm" onclick="lbClone('${x.id}')">Nhân bản</button></div></div>`).join('') || '<div class="empty">Chưa có tài sản nào.</div>'}</div>`;
}
function lbNew(){
  sheet(`<h2>Tạo tài sản số</h2><p class="meta">Chọn cách bắt đầu. Cách nào cũng mở trình soạn để anh xem lại trước khi lên kệ.</p>
    <div class="lbways"><button class="card pad" onclick="lbPackSheet(false)"><b>${ico('spark',18)} Dán và để AI đóng gói</b><span class="meta">Dán SKILL.md, ghi chú, quy trình hay prompt. AI đặt tên, viết mô tả, chia nội dung.</span></button>
    <button class="card pad" onclick="lbPackSheet(true)"><b>${ico('link',18)} Dựng từ một nguồn</b><span class="meta">Dán link bài viết, repo hay trang sản phẩm. AI dựng bản của anh, ghi nguồn tham khảo.</span></button>
    <button class="card pad" onclick="lbEditor({type:'skill',name:'',tagline:'',description:'',body:'',category:'nang-suat',price:0,tags:''})"><b>${ico('pen',18)} Tự viết</b><span class="meta">Mở trình soạn trống.</span></button>
    <button class="card pad" onclick="closeSheet();S.lb.view='xuong';render()"><b>${ico('layers',18)} Clone sản phẩm đang thắng</b><span class="meta">Vào Xưởng clone: App Store, GitHub, Product Hunt.</span></button></div>`);
}
function lbPackSheet(fromUrl){
  sheet(`<h2>${fromUrl?'Dựng từ một nguồn':'Dán và để AI đóng gói'}</h2>
    <label class="field" style="margin-top:12px"><span>Loại mong muốn</span><select id="pkT"><option value="">Để AI chọn</option><option value="skill">Skill</option><option value="workflow">Workflow</option><option value="brain">Gói Second Brain</option></select></label>
    ${fromUrl?`<label class="field"><span>Link nguồn</span><input type="url" id="pkU" inputmode="url" placeholder="https://…"></label>`:''}
    <label class="field"><span>${fromUrl?'Ghi chú thêm (không bắt buộc)':'Nguyên liệu'}</span><textarea id="pkR" style="min-height:${fromUrl?90:200}px" placeholder="${fromUrl?'Muốn nhấn mạnh điều gì, dành cho ai…':'Dán SKILL.md, quy trình, checklist, ghi chú…'}"></textarea></label>
    <button class="btn pri full" onclick="lbPack(${fromUrl})">${ico('spark',17)} Đóng gói</button>`);
}
async function lbPack(fromUrl){
  const raw = $('#pkR').value, hint_type = $('#pkT').value, source_url = fromUrl ? ($('#pkU').value||'').trim() : '';
  if(fromUrl && !source_url) return toast('Dán link nguồn trước nhé');
  closeSheet(); toast('AI đang đóng gói…', 3000);
  try{ const p = await run('market','donggoi',{raw, hint_type, source_url, clone:fromUrl},'Đóng gói tài sản'); p.tags=(p.tags||[]).join(', '); lbEditor(p); }catch(e){ toast(e.message, 4000); }
}
async function lbEdit(id){ try{ const p = await run('market','studio_xem',{lid:id},'',true); lbEditor(p); }catch(e){ toast(e.message); } }
async function lbClone(id){ try{ const r = await run('market','nhanban',{lid:id},'',true); toast(r.text, 3500); S.lb.mine=null; lbEdit(r.id); lbMine(); }catch(e){ toast(e.message, 4000); } }
const LB_HINT = { skill:'Hướng dẫn đánh số superHuy làm theo khi gặp đúng loại việc.', brain:'Mỗi ghi chú bắt đầu bằng một dòng “# Tiêu đề”.', workflow:'Mỗi dòng một bước: agent.hanh_dong: Tên bước (ví dụ lark.tomtat: Tóm tắt Lark). Không dùng bước gửi, đăng, xoá.' };
function lbEditor(p){
  const cats = S.mk.data?.cats || {'dieu-hanh':'Điều hành','hop':'Họp & quyết định','noi-dung':'Nội dung & marketing','ban-hang':'Bán hàng & e-commerce','hoc':'Học tập','nang-suat':'Năng suất cá nhân'};
  sheet(`<h2>${p.id?'Sửa tài sản':'Tài sản mới'}</h2>${(p.issues||[]).length?`<div class="card pad" style="margin-top:10px;background:var(--amber-soft)"><b>Nên xem lại</b><ul style="margin:6px 0 0;padding-left:18px">${p.issues.map(i=>`<li>${esc(i)}</li>`).join('')}</ul></div>`:''}
    <input type="hidden" id="edId" value="${esc(p.id||'')}"><input type="hidden" id="edSrc" value="${esc(p.source_url||'')}">
    <div class="row" style="margin-top:12px"><label class="field grow"><span>Loại</span><select id="edT" onchange="$('#edHint').textContent=LB_HINT[this.value]" ${p.id?'disabled':''}>${['skill','workflow','brain'].map(t=>`<option value="${t}" ${p.type===t?'selected':''}>${{skill:'Skill',workflow:'Workflow',brain:'Gói Second Brain'}[t]}</option>`).join('')}</select></label>
      <label class="field grow"><span>Danh mục</span><select id="edC">${Object.entries(cats).map(([k,l])=>`<option value="${k}" ${p.category===k?'selected':''}>${esc(l)}</option>`).join('')}</select></label></div>
    <label class="field"><span>Tên</span><input type="text" id="edN" value="${esc(p.name||'')}" maxlength="80"></label>
    <label class="field"><span>Câu giới thiệu</span><input type="text" id="edG" value="${esc(p.tagline||'')}" maxlength="160"></label>
    <label class="field"><span>Mô tả</span><textarea id="edD" style="min-height:110px">${esc(p.description||'')}</textarea></label>
    <label class="field"><span>Nội dung</span><textarea id="edB" style="min-height:200px;font-family:ui-monospace,monospace;font-size:13px">${esc(p.body||'')}</textarea><small class="meta" id="edHint">${esc(LB_HINT[p.type||'skill'])}</small></label>
    <div class="row"><label class="field grow"><span>Giá (đồng, 0 = miễn phí)</span><input type="number" id="edP" min="0" step="1000" value="${p.price||0}"></label><label class="field grow"><span>Thẻ</span><input type="text" id="edK" value="${esc(p.tags||'')}" placeholder="họp, CEO"></label></div>
    <label class="lbopt"><input type="checkbox" id="edF" ${p.featured?'checked':''}><span>Đưa lên mục nổi bật của Marketplace</span></label>
    <div class="row" style="margin-top:14px"><button class="btn" onclick="lbSave(false)">Lưu nháp</button><button class="btn pri" onclick="lbSave(true)">${p.status==='published'?'Cập nhật trên kệ':'Lên kệ'}</button></div>`);
}
async function lbSave(publish){
  const v = id => ($('#'+id)||{}).value||'';
  try{ const r = await run('market','studio_luu',{lid:v('edId'), type:v('edT'), name:v('edN'), tagline:v('edG'), description:v('edD'), body:v('edB'), category:v('edC'), price:v('edP')||0, tags:v('edK'), publish, featured:$('#edF').checked, source_url:v('edSrc')},'',true);
    toast(r.text, 3500); notifyH('success'); closeSheet(); S.lb.mine=null; S.mk.data=null; S.mk.adm=null; S.lb.view='taisan'; lbMine(); if(S.tab==='lab'||S.tab==='mkt') render(); }catch(e){ toast(e.message, 4500); }
}


/* ---------- Khiếu nại và hoàn tiền (chủ sàn) */
async function knLoad(){ S.mk.kn = S.mk.kn || {loading:true}; try{ S.mk.kn = await run('market','kn',{},'',true); }catch(e){ toast(e.message); S.mk.kn={kpi:{},items:[],blocked:[]}; } if(S.tab==='mkt' && S.mk.view==='qt' && !$('#sheet').classList.contains('on')) render(); }
function knReload(){ S.mk.kn=null; S.mk.gd=null; knLoad(); }
function vKn(){
  const n = S.mk.kn; if(!n || n.loading) return `<div class="card empty">Đang tải khiếu nại…</div>`;
  const k = n.kpi||{}, f = S.mk.knFilter||'moi';
  const rows = (n.items||[]).filter(x=>f==='all'||x.c_status===f);
  const card = x=>{
    const sel = x.seller||{}, sOff = sel.official, sLock = sel.status==='suspended';
    return `<article class="card pad mkkn"><div class="row" style="justify-content:space-between;align-items:flex-start;gap:8px"><div class="grow"><div class="ttl2">${esc(x.code)} · ${esc(x.name)}</div>
      <div class="meta">${esc(x.email)}${x.buyer_blocked?' <span class="tag hi">Email đang khoá</span>':''} · ${esc(x.amount_text)} · mua ${esc(ago(x.paid_at))} · ${esc(x.status_text)}</div></div>
      <span class="tag ${x.c_status==='moi'?'hi':x.c_status==='da_hoan'?'mid':''}">${esc(x.c_status_text)}</span></div>
      <p class="mkknr">“${esc(x.reason)}”<span class="meta"> · ${esc(ago(x.at))}${x.in_window?' · trong hạn hoàn '+n.refund_days+' ngày':' · quá hạn hoàn '+n.refund_days+' ngày'}</span></p>
      <div class="meta">Người bán: ${sOff?'superYou (chính chủ)':`${esc(sel.name)} · ${sel.complaints_30d} khiếu nại/30 ngày${sLock?' · <b>đang khoá</b>':''}`}</div>
      ${x.reply?`<div class="meta" style="margin-top:6px">Phản hồi: ${esc(x.reply)}</div>`:''}
      <div class="row" style="margin-top:10px;flex-wrap:wrap">${x.c_status==='moi'?`<button class="btn sm pri" onclick="knDecide('${esc(x.id)}','hoan')">${x.can_refund?'Chấp nhận, hoàn '+esc(x.amount_text):'Chấp nhận'}</button><button class="btn sm" onclick="knDecide('${esc(x.id)}','tu_choi')">Từ chối</button>`:''}
        ${sOff||!sel.id?'':`<button class="btn sm" data-n="${esc(sel.name)}" onclick="knSeller('${esc(sel.id)}','${sLock?'mo':'khoa'}',this.dataset.n)">${sLock?'Mở người bán':'Khoá người bán'}</button>`}
        <button class="btn sm" data-e="${esc(x.email)}" onclick="knBuyer(this.dataset.e,${x.buyer_blocked?0:1})">${x.buyer_blocked?'Mở email mua':'Khoá email mua'}</button></div></article>`;
  };
  return `<div class="kpis mkkpis"><div class="card kpi ${k.new?'warn':''}"><b>${k.new||0}</b><span>Khiếu nại mới</span></div><div class="card kpi"><b>${k.refunded||0}</b><span>Đã hoàn tiền</span></div><div class="card kpi"><b>${k.rejected||0}</b><span>Đã từ chối</span></div><div class="card kpi"><b>${k.blocked||0}</b><span>Email mua đang khoá</span></div></div>
    <div class="chips" style="margin-top:12px">${[['moi','Mới'],['da_hoan','Đã hoàn'],['tu_choi','Từ chối'],['all','Tất cả']].map(([v,l])=>`<button class="chip ${f===v?'on':''}" onclick="S.mk.knFilter='${v}';render()">${l}</button>`).join('')}</div>
    ${rows.length?rows.map(card).join(''):`<div class="card empty">${f==='moi'?'Không có khiếu nại mới. Khách khiếu nại từ Tài khoản › Sản phẩm đã mua; superHuy báo anh qua Telegram.':'Không có khiếu nại.'}</div>`}
    ${(n.blocked||[]).length?`<div class="sec"><h2>Email mua đang khoá</h2></div><div class="card mklist">${n.blocked.map(b=>`<div class="mkrow"><div class="grow"><div class="ttl2">${esc(b.email)}</div><div class="meta">${esc(b.note||'')} · ${esc(ago(b.at))}</div></div><div class="row"><button class="btn sm" data-e="${esc(b.email)}" onclick="knBuyer(this.dataset.e,0)">Mở khoá</button></div></div>`).join('')}</div>`:''}
    <p class="muted small" style="margin:12px 4px">Người bán bị ${n.suspend_after||3} khiếu nại trong 30 ngày tự bị khoá. Hoàn tiền: superYou ghi sổ, anh chuyển khoản trả khách thủ công.${n.mail_ready?'':' Chưa kết nối mail: khách xem phản hồi trong Tài khoản.'}</p>`;
}
function knDecide(id, dec){
  const ok = dec==='hoan';
  sheet(`<h2>${ok?'Chấp nhận khiếu nại':'Từ chối khiếu nại'}</h2><label class="field" style="margin-top:12px"><span>${ok?'Lời nhắn cho khách (không bắt buộc)':'Lý do từ chối (khách sẽ nhận được)'}</span><textarea id="knN" maxlength="500"></textarea></label>
    <button class="btn pri full" onclick="knSend('${id}','${dec}')">${ok?'Chấp nhận và ghi hoàn tiền':'Từ chối'}</button>${ok?'<p class="muted small">superYou ghi sổ hoàn tiền; anh chuyển khoản trả khách thủ công.</p>':''}`);
}
async function knSend(id, dec){ try{ const r = await run('market','kn_xuly',{oid:id, decision:dec, note:$('#knN').value},'',true); closeSheet(); toast(r.text,5000); knReload(); }catch(e){ toast(e.message); } }
async function knSeller(cid, act, name){ if(!confirm(`${act==='khoa'?'Khoá':'Mở khoá'} người bán ${name}?${act==='khoa'?' Sản phẩm đang bán sẽ bị gỡ.':''}`)) return; try{ const r = await run('market','qt_nguoitao',{cid, action:act},'',true); toast(r.text,4000); S.mk.adm=null; knReload(); }catch(e){ toast(e.message); } }
async function knBuyer(email, on){ if(on && !confirm(`Khoá email mua ${email}? Email này không tạo được đơn mới.`)) return; try{ const r = await run('market','kn_khoamua',{email, on: on?'1':'0', note: on?'Khoá từ màn Khiếu nại':''},'',true); toast(r.text,3500); knReload(); }catch(e){ toast(e.message); } }
