/* =================================================================== Khách đăng ký (phễu cho phòng GTM) */
S.ld = { data:null, f:'all' };
async function ldLoad(){ try{ S.ld.data = await run('khach','ds',{},'',true); }catch(e){ toast(e.message); S.ld.data={items:[],by_status:{},by_src:{},per_day:[],statuses:{},total:0}; } if(S.tab==='leads' && !$('#sheet').classList.contains('on')) render(); }
function vLeads(){
  const d = S.ld.data, head = `<div class="date">Email để lại trên landing page và Marketplace</div><h1>Khách đăng ký</h1>`;
  if(!d){ ldLoad(); return head + `<div class="card empty">Đang tải…</div>`; }
  const st = d.statuses, rows = d.items.filter(x=>S.ld.f==='all'||x.status===S.ld.f);
  const kp = [['Tổng đăng ký', d.total],['Chưa liên hệ', d.by_status.moi||0, (d.by_status.moi||0)?'warn':''],['Đang trao đổi', (d.by_status.da_lien_he||0)+(d.by_status.dang_trao_doi||0)],['Dùng thử', d.by_status.dung_thu||0],['Thành khách', d.by_status.khach||0]];
  return head + `<div class="kpis mkkpis">${kp.map(([l,v,c])=>`<div class="card kpi ${c||''}"><b>${v}</b><span>${l}</span></div>`).join('')}</div>
    <div class="card pad chart" style="margin-top:12px"><div class="row" style="justify-content:space-between"><b>Đăng ký 14 ngày qua</b><span class="meta">${Object.entries(d.by_src).map(([k,v])=>`${esc(k)} ${v}`).join(' · ')||'Chưa có nguồn'}</span></div>
      ${vbars(d.per_day.map(x=>({l:x.d.slice(8,10)+'/'+x.d.slice(5,7), v:x.n, tip:`${x.d.slice(8,10)}/${x.d.slice(5,7)}: ${x.n} đăng ký`})), {aria:'Số đăng ký mỗi ngày', labels:5})}<div class="tipline meta"></div></div>
    <div class="chips">${['all',...Object.keys(st)].map(k=>`<button class="chip ${S.ld.f===k?'on':''}" onclick="S.ld.f='${k}';render()">${k==='all'?'Tất cả':esc(st[k])} ${k==='all'?d.total:(d.by_status[k]||0)}</button>`).join('')}</div>
    <div class="card mklist">${rows.map(x=>`<div class="mkrow"><div class="grow"><div class="ttl2" style="word-break:break-all">${esc(x.email)}</div><div class="meta">${esc(x.src_label)} · ${esc(ago(x.at))}${(x.interests||[]).length?` · quan tâm: ${esc(x.interests.join(', '))}`:''}</div>${x.note?`<div class="meta">Ghi chú: ${esc(x.note)}</div>`:''}</div>
      <div class="row"><button class="btn sm" onclick="copyText('${esc(x.email)}')">${ico('copy',15)}</button><select aria-label="Trạng thái" onchange="ldSet('${esc(x.email)}',this.value)">${Object.entries(st).map(([k,l])=>`<option value="${k}" ${x.status===k?'selected':''}>${esc(l)}</option>`).join('')}</select><button class="btn sm" onclick="ldNote('${esc(x.email)}')">Ghi chú</button></div></div>`).join('') || `<div class="empty">${d.total?'Không có khách ở trạng thái này.':'Chưa có ai đăng ký. Chia sẻ landing page để bắt đầu thu khách.'}</div>`}</div>
    <div class="row" style="margin-top:12px"><button class="btn sm" onclick="openLink(location.origin+'/landing')">${ico('link',15)} Mở landing page</button><button class="btn sm" onclick="openLink(location.origin+'/market')">${ico('link',15)} Mở Marketplace công khai</button></div>`;
}
async function ldSet(email, status){ try{ const r = await run('khach','trangthai',{email, status},'',true); toast(r.text); S.ld.data=null; ldLoad(); }catch(e){ toast(e.message); } }
function ldNote(email){ sheet(`<h2>Ghi chú khách</h2><p class="meta">${esc(email)}</p><label class="field" style="margin-top:10px"><span>Ghi chú</span><textarea id="ldN" placeholder="Đã gọi, hẹn demo thứ Ba…"></textarea></label><button class="btn pri full" onclick="ldSaveNote('${esc(email)}')">Lưu</button>`); }
async function ldSaveNote(email){ const it = S.ld.data.items.find(x=>x.email===email); try{ await run('khach','trangthai',{email, status:it?.status||'moi', note:$('#ldN').value},'',true); toast('Đã lưu ghi chú'); closeSheet(); S.ld.data=null; ldLoad(); }catch(e){ toast(e.message); } }



