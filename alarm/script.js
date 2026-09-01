(function () {
  'use strict';

  var DAYS = ['日', '月', '火', '水', '木', '金', '土'];
  var STORAGE_KEY = 'alarm-app.alarms.v1';

  var alarms = load();
  var ringingAlarm = null;
  var audio = null;

  var el = {
    now: document.getElementById('now'),
    today: document.getElementById('today'),
    time: document.getElementById('time'),
    label: document.getElementById('labelInput'),
    dayList: document.getElementById('dayList'),
    addBtn: document.getElementById('addBtn'),
    list: document.getElementById('alarmList'),
    empty: document.getElementById('empty'),
    overlay: document.getElementById('ringing'),
    ringTime: document.getElementById('ringTime'),
    ringLabel: document.getElementById('ringLabel'),
    snoozeBtn: document.getElementById('snoozeBtn'),
    stopBtn: document.getElementById('stopBtn')
  };

  // ---- 保存・読み込み ----
  function load() {
    try {
      var raw = localStorage.getItem(STORAGE_KEY);
      var parsed = raw ? JSON.parse(raw) : [];
      return Array.isArray(parsed) ? parsed : [];
    } catch (e) {
      return [];
    }
  }

  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(alarms));
    } catch (e) {
      /* プライベートモードなどでは保存されない */
    }
  }

  // ---- 曜日チェックボックス ----
  DAYS.forEach(function (name, i) {
    var id = 'day-' + i;
    var input = document.createElement('input');
    input.type = 'checkbox';
    input.id = id;
    input.value = String(i);
    var label = document.createElement('label');
    label.setAttribute('for', id);
    label.textContent = name;
    el.dayList.appendChild(input);
    el.dayList.appendChild(label);
  });

  function selectedDays() {
    return Array.prototype.slice
      .call(el.dayList.querySelectorAll('input:checked'))
      .map(function (i) { return Number(i.value); });
  }

  function clearDays() {
    Array.prototype.forEach.call(el.dayList.querySelectorAll('input'), function (i) {
      i.checked = false;
    });
  }

  // ---- 時計 ----
  function pad(n) { return n < 10 ? '0' + n : String(n); }

  function tick() {
    var d = new Date();
    el.now.textContent = pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
    el.today.textContent = d.getFullYear() + '年' + (d.getMonth() + 1) + '月' + d.getDate() + '日（' + DAYS[d.getDay()] + '）';
    checkAlarms(d);
  }

  // ---- アラーム判定 ----
  function minuteKey(d) {
    return d.toDateString() + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes());
  }

  function checkAlarms(d) {
    if (ringingAlarm) return;
    var hhmm = pad(d.getHours()) + ':' + pad(d.getMinutes());
    var key = minuteKey(d);

    for (var i = 0; i < alarms.length; i++) {
      var a = alarms[i];
      if (!a.enabled || a.time !== hhmm || a.lastFired === key) continue;
      if (a.days.length > 0 && a.days.indexOf(d.getDay()) === -1) continue;

      a.lastFired = key;
      if (a.days.length === 0) a.enabled = false; // 1回のみのアラームは鳴ったらオフ
      save();
      render();
      ring(a);
      return;
    }
  }

  // ---- 鳴動 ----
  function startSound() {
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      var ctx = new Ctx();
      var gain = ctx.createGain();
      gain.gain.value = 0;
      gain.connect(ctx.destination);
      var osc = ctx.createOscillator();
      osc.type = 'sine';
      osc.frequency.value = 880;
      osc.connect(gain);
      osc.start();

      // 0.4秒鳴らして0.4秒休む、を繰り返す
      var on = false;
      var beat = setInterval(function () {
        on = !on;
        gain.gain.setTargetAtTime(on ? 0.25 : 0, ctx.currentTime, 0.01);
      }, 400);

      audio = { ctx: ctx, osc: osc, beat: beat };
    } catch (e) {
      audio = null;
    }
  }

  function stopSound() {
    if (!audio) return;
    clearInterval(audio.beat);
    try { audio.osc.stop(); } catch (e) {}
    try { audio.ctx.close(); } catch (e) {}
    audio = null;
  }

  function ring(a) {
    ringingAlarm = a;
    el.ringTime.textContent = a.time;
    el.ringLabel.textContent = a.label || '';
    el.overlay.classList.remove('hidden');
    el.stopBtn.focus();
    startSound();
  }

  function dismiss() {
    stopSound();
    el.overlay.classList.add('hidden');
    ringingAlarm = null;
  }

  el.stopBtn.addEventListener('click', dismiss);

  el.snoozeBtn.addEventListener('click', function () {
    var base = ringingAlarm;
    var t = new Date(Date.now() + 5 * 60 * 1000);
    alarms.push({
      id: String(Date.now()) + Math.random().toString(16).slice(2),
      time: pad(t.getHours()) + ':' + pad(t.getMinutes()),
      label: (base && base.label ? base.label + ' ' : '') + '(スヌーズ)',
      days: [],
      enabled: true,
      lastFired: ''
    });
    save();
    render();
    dismiss();
  });

  // ---- 追加・一覧 ----
  el.addBtn.addEventListener('click', function () {
    if (!el.time.value) {
      alert('アラーム時刻を入力してください。');
      el.time.focus();
      return;
    }
    alarms.push({
      id: String(Date.now()) + Math.random().toString(16).slice(2),
      time: el.time.value,
      label: el.label.value.trim(),
      days: selectedDays(),
      enabled: true,
      lastFired: ''
    });
    alarms.sort(function (a, b) { return a.time < b.time ? -1 : a.time > b.time ? 1 : 0; });
    save();
    render();
    el.label.value = '';
    clearDays();
  });

  function daysText(a) {
    if (a.days.length === 0) return '1回のみ';
    if (a.days.length === 7) return '毎日';
    return a.days.slice().sort().map(function (d) { return DAYS[d]; }).join('・');
  }

  function render() {
    el.list.textContent = '';
    el.empty.hidden = alarms.length > 0;

    alarms.forEach(function (a) {
      var li = document.createElement('li');
      li.className = 'alarm-item' + (a.enabled ? '' : ' off');

      var main = document.createElement('div');
      main.className = 'alarm-main';
      var time = document.createElement('div');
      time.className = 'alarm-time';
      time.textContent = a.time;
      var meta = document.createElement('div');
      meta.className = 'alarm-meta';
      meta.textContent = daysText(a) + (a.label ? ' ・ ' + a.label : '');
      main.appendChild(time);
      main.appendChild(meta);

      var sw = document.createElement('label');
      sw.className = 'switch';
      var cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = a.enabled;
      cb.setAttribute('aria-label', a.time + ' のアラームのオン・オフ');
      cb.addEventListener('change', function () {
        a.enabled = cb.checked;
        a.lastFired = '';
        save();
        render();
      });
      var slider = document.createElement('span');
      slider.className = 'slider';
      sw.appendChild(cb);
      sw.appendChild(slider);

      var del = document.createElement('button');
      del.type = 'button';
      del.className = 'delete';
      del.textContent = '✕';
      del.setAttribute('aria-label', a.time + ' のアラームを削除');
      del.addEventListener('click', function () {
        alarms = alarms.filter(function (x) { return x.id !== a.id; });
        save();
        render();
      });

      li.appendChild(main);
      li.appendChild(sw);
      li.appendChild(del);
      el.list.appendChild(li);
    });
  }

  render();
  tick();
  setInterval(tick, 1000);
})();
