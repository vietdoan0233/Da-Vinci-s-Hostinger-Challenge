/* Extension glue: take the URL of the tab the reader is on and hand it to the shared page logic (app.js),
   which calls the server. Nothing is sent until the reader opens the panel or presses a button. */
(function () {
  "use strict";
  var hint = document.getElementById("tab-hint"), tabGo = document.getElementById("tab-go");
  var POST = /^https:\/\/bsky\.app\/profile\/[^/?#]+\/post\/[A-Za-z0-9]+\/?$/;
  var VIDEO = /^https?:\/\/((www|m|music)\.)?(youtube\.com\/(watch|shorts|embed|live)|youtu\.be\/)/i;
  var current = null;   // {id, url} of the active tab
  var analysed = null;  // the URL last sent, so the button can say "again"

  function supported(url) { return !!url && (POST.test(url) || VIDEO.test(url)); }

  function describe(url) {
    if (!url) return "Open a Bluesky post or a YouTube video.";
    if (POST.test(url)) return "This tab: a Bluesky post.";
    if (VIDEO.test(url)) return "This tab: a YouTube video.";
    try { return "This tab (" + new URL(url).hostname + ") is not a post or video. Select text and right-click to decode it."; }
    catch (e) { return "This tab cannot be analysed."; }
  }

  function show() {
    var url = current && current.url;
    hint.textContent = describe(url);
    tabGo.disabled = !supported(url);
    tabGo.textContent = url && url === analysed ? "Analyse again" : "Analyse this tab";
  }

  function analyseTab() {
    if (!current || !supported(current.url)) return;
    analysed = current.url;
    show();
    DecodeApp.analyze(current.url);
  }

  function readTab(then) {
    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
      var t = tabs && tabs[0];
      current = t ? { id: t.id, url: t.url || "" } : null;
      show();
      if (then) then();
    });
  }

  tabGo.addEventListener("click", analyseTab);
  chrome.tabs.onActivated.addListener(function () { readTab(); });
  chrome.tabs.onUpdated.addListener(function (id, change) { if (change.url && current && id === current.id) readTab(); });

  // A time in a video result moves the video in the tab when that video is open there; otherwise it opens a tab.
  DecodeApp.hooks.onSeek = function (seconds, link) {
    var here = current && VIDEO.test(current.url) && analysed === current.url;
    if (!here) { if (link) chrome.tabs.create({ url: link }); return; }
    chrome.scripting.executeScript({
      target: { tabId: current.id },
      func: function (s) { var v = document.querySelector("video"); if (v) { v.currentTime = s; v.play(); } },
      args: [seconds]
    }).catch(function () { if (link) chrome.tabs.create({ url: link }); });
  };

  // Text sent from the right-click menu.
  function takePending() {
    chrome.storage.session.get("pending", function (got) {
      var p = got && got.pending;
      if (!p || Date.now() - p.at > 60000) return;
      chrome.storage.session.remove("pending");
      DecodeApp.analyze(p.text);
    });
  }
  chrome.storage.onChanged.addListener(function (changes, area) { if (area === "session" && changes.pending && changes.pending.newValue) takePending(); });

  // Opening the panel is the reader asking for this tab: analyse it once, then wait for the button.
  readTab(function () {
    chrome.storage.session.get("pending", function (got) {
      if (got && got.pending) takePending(); else analyseTab();
    });
  });
})();
