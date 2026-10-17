/* =================================================================== Xưởng Tài sản số (chỉ chủ sàn): nguồn có điểm, đội clone, thẻ duyệt */
S.lb = { view:'xuong', src:'github', industry:'', role:'', q:'', scan:null, mine:null, proj:null, opts:[] };
const LB_SRC = {github:'Kho skill & prompt mở', template:'Template Obsidian / Notion', framework:'Khung làm việc theo vai trò', market:'Bán chạy trên chợ'};
const LB_PART = {nang_suat:['Năng suất ngay',30], brain:['Second Brain',25], cai_mot_cham:['Cài một chạm',20], giay_phep:['Giấy phép',25]};
async function lbScan(force){
  if(S.lb.scan && !force) return;
  S.lb.scan = {loading:true};
  if(S.tab==='lab') render();
  try{ S.lb.scan = await run('xuong','quet',{src:S.lb.src, q:S.lb.q, industry:S.lb.industry, role:S.lb.role},'',true); }catch(e){ S.lb.scan = {error:e.message, items:[]}; }
  if((S.tab==='lab'||(S.tab==='mkt'&&S.mk.view==='xuong')) && !$('#sheet').classList.contains('on')) render();
}
async function lbMine(){ try{ const [m, p] = await Promise.all([run('market','cuatoi',{},'',true), run('xuong','duan_ds',{},'',true)]); S.lb.mine = m; S.lb.proj = p; }catch(e){ toast(e.message); S.lb.mine={mine:[],queue:[],stats:{}}; S.lb.proj={items:[],statuses:{},kinds:{}}; } if((S.tab==='lab'||(S.tab==='mkt'&&S.mk.view==='xuong')) && !$('#sheet').classList.contains('on')) render(); }
function vLab(){
  const head = `<div class="date">Xưởng Tài sản số · chỉ anh thấy</div><h1>Xưởng</h1>
    <div class="row" style="margin-bottom:14px;justify-content:flex-end"><button class="btn sm pri" onclick="lbNew()">${ico('plus',16)} Tạo tài sản</button><button class="btn sm" onclick="go('mkt')">Marketplace</button></div>`;
  return head + vLabInner();
}
function lbScoreBadge(x, big){ const c = x.score>=80?'var(--jade)':x.score>=60?'#2457C5':'var(--danger)'; return `<span class="lbscore ${big?'big':''}" style="--c:${c}" title="Điểm nguồn">${x.score}</span>`; }
function vLabInner(){
  const v = S.lb.view;
  const head = `<div class="seg" style="margin-bottom:12px"><button class="${v==='xuong'?'on':''}" onclick="S.lb.view='xuong';render()">Nguồn</button><button class="${v==='duan'?'on':''}" onclick="S.lb.view='duan';render()">Dự án${S.lb.proj?.items?.length?` ${S.lb.proj.items.length}`:''}</button><button class="${v==='taisan'?'on':''}" onclick="S.lb.view='taisan';render()">Tài sản của anh</button></div>`;
  if(!S.lb.mine) lbMine();
  if(v==='taisan') return head + lbAssets();
  if(v==='duan') return head + lbProjects();
  const sc = S.lb.scan; if(!sc) lbScan();
  const f = sc?.filters || {sources:LB_SRC, industries:{}, roles:{}};
  const sel = (id, obj, cur, on, all) => `<select id="${id}" aria-label="${id}" onchange="${on}"><option value="">${all}</option>${Object.entries(obj).map(([k,l])=>`<option value="${k}" ${k===cur?'selected':''}>${esc(l)}</option>`).join('')}</select>`;
  const bar = `<div class="lbbar"><div class="seg">${Object.entries(f.sources).map(([k,l])=>`<button class="${S.lb.src===k?'on':''}" onclick="S.lb.src='${k}';S.lb.q='';lbScan(true)">${esc(l)}</button>`).join('')}</div>
    <div class="row">${sel('lbI', f.industries, S.lb.industry, "S.lb.industry=this.value;lbScan(true)", 'Mọi ngành')}${sel('lbR', f.roles, S.lb.role, "S.lb.role=this.value;lbScan(true)", 'Mọi vai trò')}</div>
    <form class="hask" style="margin:0" onsubmit="event.preventDefault();S.lb.q=$('#lbq').value.trim();lbScan(true)"><input id="lbq" value="${esc(S.lb.q)}" placeholder="Tìm nguồn theo chủ đề…" autocomplete="off" enterkeyhint="search"><button class="go" aria-label="Tìm">${ico('arrow',20)}</button></form></div>`;
  const sug = S.lb.proj?.suggest?.items?.length ? `<div class="card pad lbsug"><b>${ico('spark',15)} Gợi ý tuần này (${esc((S.lb.proj.suggest.at||'').slice(0,10))})</b><div class="row" style="margin-top:6px">${S.lb.proj.suggest.items.map(t=>`<button class="chip" onclick="lbOpen('${esc(t.key)}')">${esc(t.name)} · ${t.score}</button>`).join('')}</div></div>` : '';
  if(!sc || sc.loading) return head + bar + sug + `<div class="card empty"><span class="spin" style="width:16px;height:16px;display:inline-block;vertical-align:-3px"></span> Đang quét ${esc(f.sources[S.lb.src]||'')}…</div>`;
  if(sc.error) return head + bar + sug + `<div class="card empty">${esc(sc.error)} <button class="link" onclick="lbScan(true)">Thử lại</button></div>`;
  return head + bar + sug + `<p class="meta" style="margin:10px 2px">${esc(sc.label||'')} · ${sc.items.length} nguồn, ${sc.items.filter(i=>i.clone_ok).length} đủ ${sc.min_score||60} điểm. Bấm để xem điểm từng tiêu chí và giao cho đội clone.</p>
    <div class="lbgrid">${sc.items.map(x=>`<button class="card lbcard ${x.cloned?'cloned':''} ${x.clone_ok?'':'low'}" onclick="lbOpen('${esc(x.key)}')">${x.cloned?'<span class="lbtag">Đã clone</span>':''}
      <div class="row" style="width:100%;justify-content:space-between;align-items:flex-start">${x.icon?`<img src="${esc(x.icon)}" alt="" loading="lazy" referrerpolicy="no-referrer">`:`<span class="mkicon" style="--c:${x.color||'#2457C5'};width:48px;height:48px">${ico(x.src==='framework'?'layers':x.src==='market'?'bag':x.src==='template'?'brain':'code',22)}</span>`}${lbScoreBadge(x)}</div>
      <b class="clamp2">${esc(x.name)}</b><span class="meta clamp2">${esc(x.summary||x.dev||'')}</span>
      <span class="row" style="gap:4px;flex-wrap:wrap"><span class="tag lo">${esc(f.industries?.[x.industry]||x.industry||'')}</span><span class="tag lo">${esc(f.roles?.[x.role]||x.role||'')}</span><span class="tag ${x.license?'role':'lo'}">${esc(x.license_label||'Không rõ')}</span></span>
      <span class="meta">${esc(f.kinds?.[x.kind]||x.kind||'')}${x.ratings?` · ${nf(x.ratings)}${x.src==='market'?' cài':' sao'}`:''}</span></button>`).join('')}</div>`;
}
async function lbOpen(key, tab){
  S.lb.cur = S.lb.cur && S.lb.cur.key===key ? S.lb.cur : null; S.lb.tab = tab || S.lb.tab || 'info';
  if(!S.lb.cur){ sheet(`<div class="empty"><span class="spin" style="width:16px;height:16px;display:inline-block;vertical-align:-3px"></span> Đang đọc nguồn và chấm điểm…</div>`);
    try{ S.lb.cur = await run('xuong','xem',{key},'',true); }catch(e){ return sheet(`<div class="empty">${esc(e.message)}</div>`); } }
  const x = S.lb.cur, t = S.lb.tab, f = S.lb.scan?.filters || {industries:x.industries||{}, roles:x.roles||{}, kinds:x.kinds||{}};
  const tabs = [['info','Thông tin'],['score','Điểm nguồn'],['clone','Clone']];
  let b = '';
  if(t==='info') b = `<div class="mkfacts"><div><b>${esc(x.license_label||'Không rõ')}</b><span>Giấy phép</span></div><div><b>${esc(f.industries[x.industry]||x.industry||'')}</b><span>Ngành</span></div><div><b>${esc(f.roles[x.role]||x.role||'')}</b><span>Vai trò</span></div><div><b>${esc(x.kinds?.[x.kind]||x.kind||'')}</b><span>Sẽ thành</span></div></div>
    ${x.url?`<button class="btn sm" onclick="openLink('${esc(x.url)}')">${ico('link',15)} Mở nguồn gốc</button>`:''}
    ${x.questions?.length?`<h3 class="mkh">Người dùng sẽ hỏi</h3><ul class="mkcontents">${x.questions.map(q=>`<li>${esc(q)}</li>`).join('')}</ul>`:''}
    <h3 class="mkh">Mô tả</h3><p style="white-space:pre-line">${esc((x.description||x.summary||'').slice(0,3000))}</p>`;
  if(t==='score') b = `<div class="row" style="align-items:center;gap:14px">${lbScoreBadge(x,true)}<div><b>${x.clone_ok?'Đủ điểm vào xưởng':'Chưa đủ '+(x.min_score||60)+' điểm'}</b><p class="meta" style="margin:2px 0 0">Theo 4 tiêu chí của đặc tả Xưởng.</p></div></div>
    <div class="lbparts">${Object.entries(LB_PART).map(([k,[l,m]])=>`<div class="lbpart"><div class="row" style="justify-content:space-between"><span>${l}</span><b>${x.parts?.[k]??0}/${m}</b></div><div class="bar"><i style="width:${Math.round(100*(x.parts?.[k]||0)/m)}%"></i></div></div>`).join('')}</div>
    ${x.reasons?.length?`<h3 class="mkh">Vì sao chưa cao hơn</h3><ul class="mkcontents">${x.reasons.map(r=>`<li>${esc(r)}</li>`).join('')}</ul>`:''}
    <p class="muted small">Giấy phép cho phép làm lại: ${esc((x.license_ok||[]).join(', '))}. Không rõ giấy phép thì loại ngay.</p>`;
  if(t==='clone') b = x.clone_ok ? `${x.cloned?`<div class="card pad" style="margin-bottom:10px">Đã clone nguồn này. <button class="link" onclick="lbProject('${x.project}')">Mở dự án</button></div>`:''}
    <div class="card pad"><b>Đội clone sẽ làm 6 bước</b><p class="meta" style="margin:4px 0 0">BA → PO → Dev → Designer → Tester → Kiểm duyệt. Mỗi bước lưu vào dự án; anh bấm Sửa ở bước nào thì đội làm lại từ bước đó. Xong có thẻ duyệt, anh bấm Publish mới lên chợ.</p></div>
    <h3 class="mkh">Ghi chú cho đội</h3>
    ${x.notes?.length?`<select id="lbSaved" onchange="if(this.value){$('#lbN').value=($('#lbN').value?$('#lbN').value+'\\n':'')+this.value;this.value=''}"><option value="">Ghi chú đã lưu (${x.notes.length})…</option>${x.notes.map(n=>`<option value="${esc(n)}">${esc(n.slice(0,60))}</option>`).join('')}</select>`:''}
    <label class="field" style="margin-top:8px"><span class="sr">Ghi chú</span><textarea id="lbN" style="min-height:90px" placeholder="Ngành muốn nhắm, điểm cần nhấn mạnh, giá mong muốn…"></textarea></label>
    <div class="row" style="margin-top:8px"><button class="btn sm" onclick="run('xuong','ghichu',{text:$('#lbN').value},'',true).then(r=>toast(r.text)).catch(e=>toast(e.message))">${ico('save',15)} Lưu ghi chú</button></div>
    <button class="btn pri full" style="margin-top:14px" onclick="lbDoClone('${esc(x.key)}')">${ico('spark',17)} Giao cho đội clone</button>
    <p class="muted small">Dev viết lại hoàn toàn bằng lời mình, Kiểm duyệt chặn trùng câu, thương hiệu và dữ liệu riêng. Chưa Publish thì chưa ai thấy.</p>`
    : `<div class="empty">Nguồn này chưa đủ ${x.min_score||60} điểm${x.license?'':' (giấy phép không rõ)'} nên không vào xưởng. Xem tab Điểm nguồn.</div>`;
  sheet(`<div class="mkdet">${x.icon?`<img class="lbicon" src="${esc(x.icon)}" alt="" referrerpolicy="no-referrer">`:mkIcon({type:x.kind==='brain'?'brain':x.kind==='pack'?'pack':'skill',color:x.color||'#2457C5'},72)}<div class="grow"><h2 style="font-size:20px">${esc(x.name)}</h2><div class="meta">${esc(x.dev||'')} · ${esc(LB_SRC[x.src]||x.src)}</div>
      <div class="row" style="margin-top:8px">${lbScoreBadge(x)}<button class="btn sm" onclick="run('xuong','theodoi',{key:'${esc(x.key)}'},'',true).then(r=>{toast(r.text);S.lb.cur.starred=r.starred})">${ico('star',15)} ${x.starred?'Đang theo dõi':'Theo dõi'}</button></div></div></div>
    <div class="seg lbtabs" role="tablist">${tabs.map(([k,l])=>`<button role="tab" aria-selected="${t===k}" class="${t===k?'on':''}" onclick="lbOpen('${esc(x.key)}','${k}')">${l}</button>`).join('')}</div><div style="margin-top:12px">${b}</div>`);
}
async function lbDoClone(key){
  const notes = $('#lbN')?.value||'';
  closeSheet(); toast('Đội clone bắt đầu làm, anh theo dõi tiến độ trong Dự án', 4000);
  try{ const r = await run('xuong','clone',{key, notes},'Đội clone đang làm');
    notifyH('success'); S.lb.cur=null; S.lb.proj=null; lbMine(); if(S.lb.scan?.items){ const it=S.lb.scan.items.find(i=>i.key===key); if(it) it.cloned=true; } lbProject(r.project.id); }catch(e){ toast(e.message, 4000); }
}
function lbProjects(){
  const p = S.lb.proj; if(!p) return `<div class="card empty">Đang tải dự án…</div>`;
  if(!p.items.length) return `<div class="done"><b>Chưa có dự án nào</b>Vào tab Nguồn, chọn một nguồn đủ điểm rồi bấm Giao cho đội clone. Đội BA → PO → Dev → Designer → Tester → Kiểm duyệt sẽ làm và đưa thẻ duyệt cho anh.<div class="row" style="justify-content:center;margin-top:16px"><button class="btn pri" onclick="S.lb.view='xuong';render()">Mở Nguồn</button></div></div>`;
  const tagc = s => s==='da_len_cho'||s==='da_ra_mat'?'role':s==='bo'?'lo':s==='cho_duyet'?'hot':'mid';
  return `<div class="card mklist">${p.items.map(x=>`<div class="mkrow" role="button" tabindex="0" onclick="lbProject('${x.id}')">${x.source?.icon?`<img class="lbmini" src="${esc(x.source.icon)}" alt="" referrerpolicy="no-referrer">`:`<span class="thumb">${ico('layers',20)}</span>`}<div class="grow"><div class="ttl2">${esc(x.name)}</div><div class="meta">Từ ${esc(x.source?.name||'')} · ${esc(p.kinds?.[x.kind]||x.kind||'')}${x.industry?` · ${esc(p.industries?.[x.industry]||x.industry)}`:''}${x.test_score!=null?` · test ${x.test_score}`:''}</div></div><span class="tag ${tagc(x.status)}">${esc(p.statuses[x.status]||x.status)}</span></div>`).join('')}</div>`;
}
async function lbProject(pid){
  let p; try{ p = await run('xuong','duan',{pid},'',true); }catch(e){ return toast(e.message); }
  sheet(`<div class="date">Dự án từ ${esc(p.source?.name||'')} · ${esc(p.kinds?.[p.kind]||p.kind||'')}</div><h2 style="font-size:22px;margin-top:4px">${esc(p.name)}</h2><p style="margin:6px 0 0">${esc(p.pitch||'')}</p>
    <div class="row" style="margin-top:10px">${['nhap','cho_duyet','bo'].map(k=>`<button class="chip ${p.status===k?'on':''}" onclick="run('xuong','duan_sua',{pid:'${p.id}',status:'${k}'},'',true).then(r=>{toast(r.text);S.lb.proj=null;lbMine();lbProject('${p.id}')})">${esc(p.statuses[k]||k)}</button>`).join('')}</div>
    ${p.notes?`<h3 class="mkh">Ghi chú của anh</h3><p style="white-space:pre-line">${esc(p.notes)}</p>`:''}
    <div class="row" style="margin-top:10px"><button class="btn" onclick="if(confirmTap(this))run('xuong','duan_xoa',{pid:'${p.id}'},'',true).then(r=>{toast(r.text);closeSheet();S.lb.proj=null;lbMine()})">Xoá dự án</button></div>`);
}
function confirmTap(b){ if(b.dataset.ok) return true; b.dataset.ok='1'; b.textContent='Bấm lần nữa để xoá'; setTimeout(()=>{ delete b.dataset.ok; b.textContent='Xoá dự án'; }, 3000); return false; }
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
    <button class="card pad" onclick="closeSheet();S.lb.view='xuong';render()"><b>${ico('layers',18)} Giao đội clone từ một nguồn</b><span class="meta">Kho skill mở, template Obsidian/Notion, khung làm việc, bán chạy trên chợ.</span></button></div>`);
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
