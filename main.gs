function runDailyReport() {
  try {
    var site = getLatestRow();

    Logger.log('取得行: ' + site.rowNumber);
    Logger.log('集計日: ' + site.date);

    // 2日以上古ければ止める（必要なら3日にしてもOK）
    assertFreshness(site.date, 2);

    var daily   = getTopDailyArticles();
    var weekly  = getTopWeeklyArticles();
    var monthly = getTopMonthlyArticles();

    var message = buildMessage(site, daily, weekly, monthly);
    Logger.log(message);

    if (!CONFIG.DEBUG_MODE) sendDiscord(message);
    Logger.log('送信完了');
  } catch (e) {
    Logger.log('エラー: ' + e.message);
    throw e;
  }
}

function assertFreshness(dateStr, maxDaysOld) {
  var dataDate = new Date(dateStr);
  var today = new Date();
  var diffMs = today - dataDate;
  var diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays > maxDaysOld) {
    throw new Error('データが古すぎます: ' + diffDays + '日前のデータです（最大' + maxDaysOld + '日以内）');
  }
}

function sendDiscord(message) {
  var maxRetry = 3;

  for (var attempt = 1; attempt <= maxRetry; attempt++) {
    var res = UrlFetchApp.fetch(CONFIG.WEBHOOK_URL, {
      method: 'post',
      contentType: 'application/json',
      payload: JSON.stringify({ content: message }),
      muteHttpExceptions: true,
    });

    var code = res.getResponseCode();
    var body = res.getContentText();

    Logger.log('attempt=' + attempt + ' HTTP=' + code);
    Logger.log('レスポンス: ' + body);
    Logger.log('URL末尾10文字: ' + CONFIG.WEBHOOK_URL.slice(-10));

    if (code === 204) {
      return;
    }

    // 429 や一時的なサーバーエラーだけ再試行
    if ([429, 500, 502, 503, 504].indexOf(code) !== -1 && attempt < maxRetry) {
      var waitMs = 5000 * attempt; // 5秒 → 10秒 → 15秒
      Logger.log(waitMs + 'ms 待機して再試行します');
      Utilities.sleep(waitMs);
      continue;
    }

    throw new Error('Discord送信失敗 HTTP: ' + code + ' / body: ' + body);
  }
}

function testReadCsv() {
  Logger.log(JSON.stringify(getLatestRow(), null, 2));
  Logger.log('日次TOP: ' + JSON.stringify(getTopDailyArticles()));
  Logger.log('週次TOP: ' + JSON.stringify(getTopWeeklyArticles()));
  Logger.log('月次TOP: ' + JSON.stringify(getTopMonthlyArticles()));
}

function testBuildMessage() {
  var site    = getLatestRow();
  var daily   = getTopDailyArticles();
  var weekly  = getTopWeeklyArticles();
  var monthly = getTopMonthlyArticles();
  Logger.log(buildMessage(site, daily, weekly, monthly));
}

function testWebhookSimple() {
  var res = UrlFetchApp.fetch(CONFIG.WEBHOOK_URL, {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify({ content: 'test' }),
    muteHttpExceptions: true,
  });
  Logger.log('HTTP: ' + res.getResponseCode());
}

function testSend() {
  runDailyReport();
}
