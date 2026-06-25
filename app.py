import threading
import json
import os
from datetime import date, datetime
from flask import Flask, jsonify, render_template_string
import time

app = Flask(__name__)
agent_log = []
agent_running = False

HTML = """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bars CRM</title>
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, sans-serif; background: #0f0f0f; color: #e8e8e8; }
.header { padding: 20px 24px; border-bottom: 1px solid #1e1e1e; display: flex; align-items: center; justify-content: space-between; }
.logo { font-size: 16px; font-weight: 600; color: #fff; }
.logo span { color: #4f8ef7; }
.tag { font-size: 11px; color: #666; margin-top: 2px; }
.btn-group { display: flex; gap: 8px; }
.run-btn { background: #4f8ef7; color: #fff; border: none; padding: 10px 20px; border-radius: 8px; font-size: 13px; cursor: pointer; }
.run-btn:disabled { background: #2a2a2a; color: #555; cursor: not-allowed; }
.run-btn-green { background: #2e7d32; }
.metrics { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; padding: 20px 24px; }
@media(min-width:600px){ .metrics { grid-template-columns: repeat(4,1fr); } }
.metric { background: #1a1a1a; border-radius: 10px; padding: 14px; border: 1px solid #222; }
.metric-label { font-size: 11px; color: #666; margin-bottom: 6px; }
.metric-value { font-size: 26px; font-weight: 600; color: #fff; }
.section { padding: 0 24px 24px; }
.section-title { font-size: 11px; font-weight: 600; color: #555; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 12px; }
.card { background: #1a1a1a; border: 1px solid #222; border-radius: 10px; overflow: hidden; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { text-align: left; padding: 10px 14px; font-size: 11px; color: #555; border-bottom: 1px solid #222; }
td { padding: 11px 14px; border-bottom: 1px solid #1e1e1e; }
tr:last-child td { border-bottom: none; }
.badge { display: inline-block; font-size: 11px; padding: 3px 8px; border-radius: 20px; }
.badge-sent { background: #1a2e1a; color: #4caf50; }
.badge-queue { background: #2e2a1a; color: #f5a623; }
.badge-nocontact { background: #1e1e1e; color: #666; }
.two-col { display: grid; grid-template-columns: 1fr; gap: 20px; padding: 0 24px 24px; }
@media(min-width:700px){ .two-col { grid-template-columns: 1fr 1fr; } }
.ig-item { padding: 14px; border-bottom: 1px solid #1e1e1e; }
.ig-item:last-child { border-bottom: none; }
.ig-top { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.ig-avatar { width: 36px; height: 36px; border-radius: 50%; background: #1e2a4a; display: flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; color: #4f8ef7; flex-shrink: 0; }
.ig-handle { font-size: 13px; font-weight: 500; color: #e8e8e8; }
.ig-company { font-size: 12px; color: #666; }
.ig-actions { display: flex; gap: 8px; }
.ig-btn { font-size: 12px; padding: 6px 12px; border-radius: 6px; border: 1px solid #333; background: transparent; color: #e8e8e8; cursor: pointer; }
.ig-btn:hover { background: #222; }
.ig-btn-blue { border-color: #4f8ef7; color: #4f8ef7; }
.ig-pitch { background: #0d0d0d; border: 1px solid #222; border-radius: 6px; padding: 10px; font-size: 12px; color: #aaa; line-height: 1.6; margin-top: 10px; white-space: pre-wrap; display: none; }
.progress-wrap { margin-bottom: 14px; }
.progress-label { display: flex; justify-content: space-between; font-size: 12px; color: #666; margin-bottom: 5px; }
.progress-track { height: 4px; background: #222; border-radius: 2px; }
.progress-fill { height: 100%; border-radius: 2px; background: #4f8ef7; }
.log-box { background: #0d0d0d; border: 1px solid #1e1e1e; border-radius: 10px; padding: 14px; font-family: monospace; font-size: 12px; color: #4caf50; max-height: 260px; overflow-y: auto; white-space: pre-wrap; }
.spinner { width: 14px; height: 14px; border: 2px solid rgba(255,255,255,0.3); border-top-color: #fff; border-radius: 50%; animation: spin 0.7s linear infinite; display: inline-block; }
@keyframes spin { to { transform: rotate(360deg); } }
.copied { color: #4caf50 !important; border-color: #4caf50 !important; }
.schedule-info { font-size: 11px; color: #555; margin-top: 6px; }
</style>
</head>
<body>
<div class="header">
  <div>
    <div class="logo">Bars <span>CRM</span></div>
    <div class="tag">@dollskills3dart - Lead Agent</div>
    <div class="schedule-info">Поиск: каждые 2ч | Рассылка: 09:00 / 12:00 / 15:00 / 18:00 (Алматы)</div>
  </div>
  <div class="btn-group">
    <button class="run-btn run-btn-green" onclick="runSearch()">+ Найти лидов</button>
    <button class="run-btn" id="runBtn" onclick="runSend()">Отправить письма</button>
  </div>
</div>
<div class="metrics">
  <div class="metric"><div class="metric-label">Всего лидов</div><div class="metric-value" id="m-total">-</div></div>
  <div class="metric"><div class="metric-label">Email сегодня</div><div class="metric-value" id="m-email">-</div></div>
  <div class="metric"><div class="metric-label">Instagram очередь</div><div class="metric-value" id="m-ig">-</div></div>
  <div class="metric"><div class="metric-label">Без контактов</div><div class="metric-value" id="m-nocontact">-</div></div>
</div>
<div class="two-col">
  <div>
    <div class="section-title">Instagram очередь</div>
    <div class="card"><div id="ig-list"><div style="padding:20px;color:#555;font-size:13px;">Загрузка...</div></div></div>
  </div>
  <div>
    <div class="section-title">Лимиты сегодня</div>
    <div class="card" style="padding:16px;">
      <div class="progress-wrap">
        <div class="progress-label"><span>Email</span><span id="email-lim">0 / 20</span></div>
        <div class="progress-track"><div class="progress-fill" id="email-bar" style="width:0%"></div></div>
      </div>
      <div class="progress-wrap" style="margin-bottom:0">
        <div class="progress-label"><span>Instagram DM</span><span id="ig-lim">0 / 3</span></div>
        <div class="progress-track"><div class="progress-fill" id="ig-bar" style="width:0%;background:#7c5ef7;"></div></div>
      </div>
    </div>
    <div style="margin-top:20px;">
      <div class="section-title">Лог агента</div>
      <div class="log-box" id="log-box">Ожидание...</div>
    </div>
  </div>
</div>
<div class="section">
  <div class="section-title">Последние лиды</div>
  <div class="card">
    <table>
      <thead><tr><th>Компания</th><th>Ниша</th><th>Email</th><th>Instagram</th><th>Статус</th><th>Дата</th></tr></thead>
      <tbody id="leads-body"><tr><td colspan="6" style="text-align:center;color:#555;padding:24px;">Загрузка...</td></tr></tbody>
    </table>
  </div>
</div>
<script>
function badge(s){
  if(!s) return '<span class="badge badge-nocontact">-</span>';
  if(s==="Отправлено") return '<span class="badge badge-sent">Отправлено</span>';
  if(s.includes("Instagram")) return '<span class="badge badge-queue">Instagram</span>';
  return '<span class="badge badge-nocontact">'+s+'</span>';
}
function initials(n){ return (n||"?").split(" ").map(w=>w[0]).join("").slice(0,2).toUpperCase(); }
function copyText(btn, text) {
  navigator.clipboard.writeText(text).then(() => {
    btn.textContent = "Скопировано";
    btn.classList.add("copied");
    setTimeout(() => { btn.textContent = "Скопировать DM"; btn.classList.remove("copied"); }, 2000);
  });
}
function togglePitch(id) {
  const el = document.getElementById("pitch-" + id);
  el.style.display = el.style.display === "none" ? "block" : "none";
}
async function loadData(){
  try{
    const d = await (await fetch("/api/data")).json();
    document.getElementById("m-total").textContent=d.total;
    document.getElementById("m-email").textContent=d.email_sent;
    document.getElementById("m-ig").textContent=d.ig_queue_count;
    document.getElementById("m-nocontact").textContent=d.no_contact;
    document.getElementById("email-lim").textContent=d.email_sent+" / 20";
    document.getElementById("ig-lim").textContent=d.ig_sent+" / 3";
    document.getElementById("email-bar").style.width=Math.round(d.email_sent/20*100)+"%";
    document.getElementById("ig-bar").style.width=Math.round(d.ig_sent/3*100)+"%";
    const igHtml = d.ig_queue.length ? d.ig_queue.map((i,idx) => {
      const handle = i.instagram || "";
      const igUrl = "https://instagram.com/" + handle.replace("@","");
      const pitch = (i.pitch || "").replace(/'/g, "\'");
      return `<div class="ig-item">
        <div class="ig-top">
          <div class="ig-avatar">${initials(i.company)}</div>
          <div style="flex:1">
            <div class="ig-handle">${handle}</div>
            <div class="ig-company">${i.company}</div>
          </div>
        </div>
        <div class="ig-actions">
          <a href="${igUrl}" target="_blank" class="ig-btn ig-btn-blue">Открыть Instagram</a>
          ${pitch ? `<button class="ig-btn" onclick="togglePitch('${idx}')">Показать текст</button>
          <button class="ig-btn" onclick="copyText(this, '${pitch}')">Скопировать DM</button>` : ""}
        </div>
        ${pitch ? `<div class="ig-pitch" id="pitch-${idx}">${i.pitch || ""}</div>` : ""}
      </div>`;
    }).join("") : '<div style="padding:20px;color:#555;font-size:13px;">Очередь пуста</div>';
    document.getElementById("ig-list").innerHTML = igHtml;
    document.getElementById("leads-body").innerHTML=d.leads.length?d.leads.slice().reverse().slice(0,20).map(l=>`<tr><td style="font-weight:500;">${l["Компания"]||"-"}</td><td style="color:#666;">${l["Ниша"]||"-"}</td><td style="color:#666;font-size:12px;">${l["Email"]||"-"}</td><td style="color:#4f8ef7;font-size:12px;">${l["Instagram"]||"-"}</td><td>${badge(l["Статус"])}</td><td style="color:#444;font-size:12px;">${l["Дата добавления"]||"-"}</td></tr>`).join(""):'<tr><td colspan="6" style="text-align:center;color:#555;padding:24px;">Нет лидов</td></tr>';
  }catch(e){}
}
async function loadLog(){
  try{
    const d=await (await fetch("/api/log")).json();
    const b=document.getElementById("log-box");
    b.textContent=d.log||"Лог пуст";
    b.scrollTop=b.scrollHeight;
  }catch(e){}
}
async function runSearch(){
  await fetch("/api/run-search", {method:"POST"});
  setTimeout(loadLog, 2000);
  setInterval(loadLog, 4000);
}
async function runSend(){
  const btn=document.getElementById("runBtn");
  btn.disabled=true;
  btn.innerHTML='<span class="spinner"></span> Отправляю...';
  await fetch("/api/run-send", {method:"POST"});
  setTimeout(() => {
    btn.disabled=false;
    btn.innerHTML='Отправить письма';
    loadData();
  }, 5000);
}
loadData(); loadLog(); setInterval(loadData, 30000); setInterval(loadLog, 10000);
</script>
</body>
</html>"""


def search_only():
    """Только поиск и добавление новых лидов - без отправки."""
    global agent_log, agent_running
    agent_running = True
    try:
        import finder, pitcher, sheets
        import io
        from contextlib import redirect_stdout

        f = io.StringIO()
        with redirect_stdout(f):
            from datetime import date as d
            print(f"[search] Поиск новых лидов - {d.today()}")
            existing = sheets.get_existing_names()
            new_leads = finder.find_and_enrich(existing, count=20)
            added = 0
            for lead in new_leads:
                if lead.get("company") in existing:
                    continue
                if lead.get("email"):
                    try:
                        lead["pitch_email"] = pitcher.generate_pitch(lead, channel="email")
                        lead["email_subject"] = pitcher.generate_subject(lead)
                    except Exception as e:
                        print(f"[search] Ошибка питча: {e}")
                        lead["pitch_email"] = ""
                if lead.get("instagram"):
                    try:
                        lead["pitch_instagram"] = pitcher.generate_pitch(lead, channel="instagram")
                    except:
                        lead["pitch_instagram"] = ""
                sheets.add_lead(lead)
                existing.append(lead.get("company"))
                added += 1
                time.sleep(1)
            print(f"[search] Добавлено: {added} лидов")

        agent_log = f.getvalue().splitlines()
    except Exception as e:
        agent_log = [f"Ошибка поиска: {e}"]
    finally:
        agent_running = False


def send_only(limit=5):
    """Только отправка писем - без поиска."""
    global agent_log
    try:
        import sender, sheets, pitcher
        import io
        from contextlib import redirect_stdout
        from datetime import date as d

        f = io.StringIO()
        with redirect_stdout(f):
            print(f"[send] Отправка {limit} писем - {d.today()}")
            to_contact = sheets.get_leads_to_contact()
            print(f"[send] В очереди: {len(to_contact)}")
            sent = 0
            for lead in to_contact:
                if sent >= limit:
                    break
                company = lead.get("Компания", "")
                if lead.get("Email") and sender.can_send_email():
                    pitch = lead.get("Питч (email)", "")
                    subject = f"AI-видео и 3D реклама для {company}"
                    if not pitch:
                        try:
                            pitch = pitcher.generate_pitch({
                                "company": company,
                                "region": lead.get("Регион", "RU"),
                                "city": lead.get("Город", ""),
                                "niche": lead.get("Ниша", ""),
                                "notes": lead.get("Заметки", ""),
                            }, channel="email")
                            subject = pitcher.generate_subject({
                                "company": company,
                                "region": lead.get("Регион", "RU"),
                                "niche": lead.get("Ниша", ""),
                            })
                            sheets.update_pitch(company, pitch_email=pitch)
                        except Exception as e:
                            print(f"[send] Ошибка питча {company}: {e}")
                            continue
                    ok = sender.send_email(lead["Email"], subject, pitch)
                    if ok:
                        sheets.update_status(company, sheets.STATUS_SENT, str(d.today()))
                        sent += 1
                        time.sleep(2)
            print(f"[send] Отправлено: {sent}")

        agent_log += f.getvalue().splitlines()
    except Exception as e:
        agent_log += [f"Ошибка отправки: {e}"]


def _scheduler():
    """
    Расписание по Алматы (UTC+5):
    - Поиск лидов: каждые 2 часа
    - Отправка: 09:00, 12:00, 15:00, 18:00
    """
    last_search_hour = -1
    last_send_key = ""
    print("[scheduler] Запущен")
    while True:
        now_utc = datetime.utcnow()
        almaty_hour = (now_utc.hour + 5) % 24
        almaty_minute = now_utc.minute
        today = str(date.today())

        # Поиск каждые 2 часа
        if almaty_hour % 2 == 0 and almaty_minute == 0 and almaty_hour != last_search_hour:
            last_search_hour = almaty_hour
            if not agent_running:
                print(f"[scheduler] Автопоиск {almaty_hour}:00")
                threading.Thread(target=search_only, daemon=True).start()

        # Отправка 4 раза в день по 5 писем
        send_hours = [9, 12, 15, 18]
        send_key = f"{today}-{almaty_hour}"
        if almaty_hour in send_hours and almaty_minute == 0 and send_key != last_send_key:
            last_send_key = send_key
            print(f"[scheduler] Автоотправка {almaty_hour}:00")
            threading.Thread(target=lambda: send_only(5), daemon=True).start()

        time.sleep(30)


threading.Thread(target=_scheduler, daemon=True).start()


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/api/data")
def api_data():
    try:
        import sheets, sender
        leads = sheets.get_all_leads()
        counts = sender.get_today_counts()
        ig_queue = []
        if os.path.exists("instagram_queue.json"):
            with open("instagram_queue.json", encoding="utf-8") as f:
                raw = json.load(f)
                ig_queue = [i for i in raw if not i.get("sent")]
        leads_dict = {l.get("Instagram", "").strip(): l for l in leads if l.get("Instagram")}
        for item in ig_queue:
            ig = item.get("instagram", "").strip()
            if ig in leads_dict:
                item["pitch"] = leads_dict[ig].get("Питч (Instagram)", "")
        no_contact = sum(1 for l in leads if l.get("Статус") == "Нет контактов")
        return jsonify({
            "total": len(leads),
            "email_sent": counts.get("email", 0),
            "ig_sent": counts.get("instagram", 0),
            "ig_queue_count": len(ig_queue),
            "ig_queue": ig_queue,
            "no_contact": no_contact,
            "leads": leads,
        })
    except Exception as e:
        return jsonify({"error": str(e), "total": 0, "email_sent": 0, "ig_sent": 0,
                        "ig_queue_count": 0, "ig_queue": [], "no_contact": 0, "leads": []})


@app.route("/api/log")
def api_log():
    return jsonify({"log": "\n".join(agent_log[-100:]) if agent_log else "Агент ещё не запускался"})


@app.route("/api/status")
def api_status():
    return jsonify({"running": agent_running})


@app.route("/api/run-search", methods=["POST"])
def api_run_search():
    if agent_running:
        return jsonify({"status": "already_running"})
    threading.Thread(target=search_only, daemon=True).start()
    return jsonify({"status": "search_started"})


@app.route("/api/run-send", methods=["POST"])
def api_run_send():
    threading.Thread(target=lambda: send_only(5), daemon=True).start()
    return jsonify({"status": "send_started"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
