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
