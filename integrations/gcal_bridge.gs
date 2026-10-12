/**
 * SuperHuy Calendar Bridge — chạy trong tài khoản Google của bạn.
 * Bot gọi script này để đọc lịch (kèm màu) và tạo sự kiện. Không hết hạn như OAuth chế độ Testing.
 * Bảo mật: lần gọi đầu tiên ("pair") script tự sinh một khóa bí mật, lưu trong Script Properties
 * và chỉ trả khóa đó MỘT lần cho bot. Mọi lệnh sau phải kèm đúng khóa.
 */
var COLOR = { red: '11', orange: '6', blue: '9' };          // Tomato, Tangerine, Blueberry
var PRIORITY = { '11': 'red', '6': 'orange', '9': 'blue' };

function doPost(e) {
  var out;
  try { out = handle(JSON.parse(e.postData.contents)); }
  catch (err) { out = { ok: false, error: String(err) }; }
  return ContentService.createTextOutput(JSON.stringify(out)).setMimeType(ContentService.MimeType.JSON);
}

function doGet() {
  return ContentService.createTextOutput(JSON.stringify({ ok: true, name: 'SuperHuy Calendar Bridge' }))
    .setMimeType(ContentService.MimeType.JSON);
}

function handle(b) {
  var props = PropertiesService.getScriptProperties();
  var key = props.getProperty('KEY');
  if (b.action === 'pair') {
    if (key) return { ok: false, error: 'already_paired' };
    key = Utilities.getUuid() + Utilities.getUuid();
    props.setProperty('KEY', key);
    return { ok: true, key: key, calendar: CalendarApp.getDefaultCalendar().getName() };
  }
  if (!key || b.key !== key) return { ok: false, error: 'unauthorized' };

  var cal = CalendarApp.getDefaultCalendar();
  if (b.action === 'ping') return { ok: true, calendar: cal.getName() };

  if (b.action === 'list') {
    var s = new Date(b.start), en = new Date(b.end), evs = [];
    CalendarApp.getAllCalendars().forEach(function (c) {
      if (c.isHidden()) return;
      c.getEvents(s, en).forEach(function (ev) {
        var col = ev.getColor() || '';
        var st = ''; try { st = String(ev.getMyStatus()); } catch (x) {}
        evs.push({ status: st,
          id: ev.getId(), title: ev.getTitle(), start: ev.getStartTime().toISOString(),
          end: ev.getEndTime().toISOString(), allDay: ev.isAllDayEvent(), priority: PRIORITY[col] || 'normal',
          location: ev.getLocation() || '', calendar: c.getName(), mine: c.isOwnedByMe() && c.getId() === cal.getId()
        });
      });
    });
    return { ok: true, events: evs };
  }

  if (b.action === 'create') {
    var opt = { description: b.description || '', location: b.location || '' };
    var ev = b.allDay ? cal.createAllDayEvent(b.title, new Date(b.start), opt)
                      : cal.createEvent(b.title, new Date(b.start), new Date(b.end), opt);
    if (COLOR[b.priority]) ev.setColor(COLOR[b.priority]);
    return { ok: true, id: ev.getId() };
  }

  if (b.action === 'set_priority') {
    var e2 = cal.getEventById(b.id);
    if (!e2) return { ok: false, error: 'not_found' };
    if (COLOR[b.priority]) e2.setColor(COLOR[b.priority]);
    else { try { e2.setColor(''); } catch (x) { e2.setColor('8'); } }  // bỏ màu, nếu không được thì xám
    return { ok: true };
  }

  if (b.action === 'invites') {  // lời mời chưa trả lời trong N ngày tới
    var now = new Date(), until = new Date(now.getTime() + (b.days || 21) * 86400000), inv = [];
    CalendarApp.getAllCalendars().forEach(function (c) {
      if (c.isHidden() || !c.isOwnedByMe()) return;
      c.getEvents(now, until).forEach(function (ev) {
        var st = ''; try { st = String(ev.getMyStatus()); } catch (x) {}
        if (st !== 'INVITED' && st !== 'MAYBE') return;
        var org = ''; try { org = (ev.getCreators() || [])[0] || ''; } catch (x) {}
        inv.push({ id: ev.getId(), title: ev.getTitle(), start: ev.getStartTime().toISOString(),
          end: ev.getEndTime().toISOString(), allDay: ev.isAllDayEvent(), location: ev.getLocation() || '',
          organizer: org, status: st, guests: ev.getGuestList().length, description: (ev.getDescription() || '').slice(0, 500) });
      });
    });
    return { ok: true, invites: inv };
  }

  if (b.action === 'rsvp') {  // yes | no | maybe
    var e4 = cal.getEventById(b.id);
    if (!e4) return { ok: false, error: 'not_found' };
    var G = CalendarApp.GuestStatus;
    e4.setMyStatus({ yes: G.YES, no: G.NO, maybe: G.MAYBE }[b.status] || G.YES);
    return { ok: true };
  }

  if (b.action === 'delete') {
    var e3 = cal.getEventById(b.id);
    if (!e3) return { ok: false, error: 'not_found' };
    e3.deleteEvent();
    return { ok: true };
  }
  // ---------------- Google Tasks (cần bật dịch vụ nâng cao "Tasks API" trong Services)
  if (b.action === 'tasks_list') {
    var since = new Date(Date.now() - (b.done_days || 30) * 86400000).toISOString();
    var lists = Tasks.Tasklists.list({ maxResults: 100 }).items || [], out = [];
    lists.forEach(function (l) {
      var token = null;
      do {
        var r = Tasks.Tasks.list(l.id, { showCompleted: true, showHidden: true, maxResults: 100, pageToken: token });
        (r.items || []).forEach(function (t) {
          if (!t.title || (t.status === 'completed' && (t.completed || '') < since)) return;  // bỏ việc đã xong quá lâu
          out.push({ id: t.id, list_id: l.id, list: l.title, title: t.title,
          notes: t.notes || '', due: t.due || '', status: t.status, completed: t.completed || '', updated: t.updated,
          link: t.webViewLink || '' }); });
        token = r.nextPageToken;
      } while (token);
    });
    return { ok: true, lists: lists.map(function (l) { return { id: l.id, title: l.title }; }), tasks: out };
  }
  if (b.action === 'tasks_create') {
    var t = { title: b.title, notes: b.notes || '' };
    if (b.due) t.due = b.due.slice(0, 10) + 'T00:00:00.000Z';
    var made = Tasks.Tasks.insert(t, b.list_id || '@default');
    return { ok: true, id: made.id, list_id: b.list_id || '@default' };
  }
  if (b.action === 'tasks_update') {  // status: completed | needsAction ; due: YYYY-MM-DD
    var patch = {};
    if (b.status) { patch.status = b.status; if (b.status === 'needsAction') patch.completed = null; }
    if (b.due) patch.due = b.due.slice(0, 10) + 'T00:00:00.000Z';
    if (b.title) patch.title = b.title;
    Tasks.Tasks.patch(patch, b.list_id, b.id);
    return { ok: true };
  }
  return { ok: false, error: 'unknown_action' };
}
