/* ---------- chuyển vai (như Facebook đổi giữa trang cá nhân và Page) */
async function roleMenu(){
  const cur = HQ ? 'owner' : 'member';
  const items = [['member','superHuy','Trợ lý riêng, công việc hằng ngày','#6A3DF0',location.origin+'/app'],['owner','superYou HQ','Điều hành toàn bộ business','#B42346',location.origin+'/hq'],['seller','Console người bán','Sản phẩm và doanh thu của anh trên Marketplace','#0E7C6B',location.origin+'/market/console'],['account','Trung tâm tài khoản','Gói, sản phẩm đã mua, bảo mật','#7A5A00',location.origin+'/account']];
  sheet(`<h2>Chuyển vai</h2><p class="meta">Một tài khoản, nhiều vai. Chọn vai để mở đúng bảng điều khiển.</p><div class="card list" style="margin-top:10px">${items.map(([k,l,d,c,u])=>`<button onclick="roleGo('${k}','${u}')"><span class="thumb" style="background:${c};color:#fff;font-weight:800">${l[0]}</span><div class="grow"><div style="font-weight:600">${l}${k===cur?' <span class="tag role">Đang dùng</span>':''}</div><div class="meta">${d}</div></div><span class="chev">${ico('chev',18)}</span></button>`).join('')}</div>`);
}
async function roleGo(k, url){
  closeSheet();
  if((k==='member' && !HQ) || (k==='owner' && HQ)) return;
  try{ const r = await api('/api/account/owner', {}); lsSet('sy-acc', r.session); if(k==='owner' || k==='member'){ /* giữ phiên PIN qua sessionStorage để không phải nhập lại */ try{ sessionStorage.setItem('sh_tok', S.tok||''); }catch(e){} } }catch(e){}
  if(IN_TG && tg?.openLink) tg.openLink(url); else location.href = url;
}
