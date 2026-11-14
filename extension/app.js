/* Page logic shared by the website and the extension panel: read the input, call the API,
   hand the result to panel.js. Set window.DECODE_API before loading to call another server. */
(function () {
  "use strict";
  var MAX = 5000;
  var API = window.DECODE_API || "";
  var hooks = { onSeek: null };  // the extension sets onSeek to move the video in its tab
  var $ = function (id) { return document.getElementById(id); };
  var input = $("in"), go = $("go"), status = $("status"), count = $("count");
  var isUrl = function (v) { return /^https?:\/\/\S+$/.test(v); };
  var isVideo = function (v) { return /^https?:\/\/((www|m|music)\.)?(youtube\.com\/(watch|shorts|embed|live)|youtu\.be\/)/i.test(v); };

  function refresh() {
    var v = input.value.trim();
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 240) + "px";
    var over = !isUrl(v) && v.length > MAX;
    go.disabled = !v || over;
    count.textContent = v.length > MAX * 0.8 && !isUrl(v) ? v.length + " / " + MAX : "";
    count.classList.toggle("over", over);
  }

  function say(text, cls, spin) {
    status.textContent = "";
    status.className = "status" + (cls ? " " + cls : "");
    if (spin) { var s = document.createElement("div"); s.className = "spinner"; status.appendChild(s); }
    status.appendChild(document.createTextNode(text));
    status.hidden = false;
  }

  /* ---- thread: ten replies at a time, more as the reader scrolls ---- */
  var thread = { url: null, next: null, busy: false, run: 0 };
  var more = $("more");

  function moreSay(text, spin) {
    more.textContent = "";
    if (spin) { var s = document.createElement("div"); s.className = "spinner"; more.appendChild(s); }
    more.appendChild(document.createTextNode(text));
  }

  async function loadReplies() {
    if (thread.busy || thread.next == null) return;
    thread.busy = true;
    var mine = thread.run, offset = thread.next;
    moreSay(offset ? "Loading more replies…" : "Reading the thread…", true);
    try {
      var r = await fetch(API + "/api/replies?url=" + encodeURIComponent(thread.url) + "&offset=" + offset);
      var data = await r.json().catch(function () { return null; });
      if (mine !== thread.run) return;  // the reader opened another post meanwhile
      if (r.status === 429) { thread.retry = true; return moreSay((data && data.detail) || "Too many requests. Scroll again in a minute."); }
      if (!r.ok || !data || (data.errors && data.errors.replies)) { thread.next = null; return moreSay("Replies could not be loaded: " + ((data && data.errors && data.errors.replies) || "the server did not answer") + "."); }
      $("thread-title").textContent = data.total ? "Replies (" + data.total + ")" : "Replies";
      data.replies.forEach(function (item) { $("replies").appendChild(DecodePanel.renderReply(item, open)); });
      thread.next = data.next;
      moreSay(data.total === 0 ? "No replies to this post." : data.next == null ? "End of the thread." : "");
    } catch (e) {
      if (mine === thread.run) moreSay("Replies could not be loaded. Check your connection and scroll again.");
    } finally {
      if (mine === thread.run) thread.busy = false;
      // the marker may still be on screen (short page): keep going until it is pushed below the fold
      if (mine === thread.run && thread.next != null && !thread.retry && more.getBoundingClientRect().top < innerHeight + 200) loadReplies();
      thread.retry = false;
    }
  }

  function startThread(url) {
    thread = { url: url, next: url ? 0 : null, busy: false, run: thread.run + 1 };
    $("replies").textContent = "";
    $("thread-title").textContent = "Replies";
    $("thread").hidden = !url;
    moreSay("");
    if (url) loadReplies();
  }

  if ("IntersectionObserver" in window) {
    new IntersectionObserver(function (entries) {
      if (entries.some(function (e) { return e.isIntersecting; })) loadReplies();
    }, { rootMargin: "300px" }).observe(more);
  } else {
    addEventListener("scroll", function () { if (more.getBoundingClientRect().top < innerHeight + 300) loadReplies(); });
  }

  // A clicked reply becomes the main post, with its own replies below it.
  function open(url) {
    input.value = url;
    refresh();
    window.scrollTo({ top: 0 });
    run(true);
  }

  /* ---- video: the transcript is checked a few chunks at a time, results appear as they arrive ---- */
  var videoRun = 0;

  async function runVideo(v, push) {
    var mine = ++videoRun, offset = 0, video = null, seen = 0, flagged = 0, counts = {}, list = null;
    say("Reading the transcript…", "", true);
    try {
      while (offset != null) {
        var r = await fetch(API + "/api/video?url=" + encodeURIComponent(v) + "&offset=" + offset);
        var data = await r.json().catch(function () { return null; });
        if (mine !== videoRun) return;
        if (r.status === 429) { if (!video) return say((data && data.detail) || "Too many requests. Try again in a minute.", "error"); DecodePanel.videoNote($("tech"), "Stopped early: too many requests. Try again in a minute.", true); break; }
        if (!r.ok || !data) { if (!video) return say("The video could not be analysed.", "error"); DecodePanel.videoNote($("tech"), "Stopped early: the server did not answer.", true); break; }
        if (data.errors && data.errors.video) return say(data.errors.video + ".", "error");
        if (!video) {
          video = data.video;
          list = DecodePanel.renderVideoStart($("post"), $("tech"), video);
          status.hidden = true;
          $("result").hidden = false;
          var target = "?q=" + encodeURIComponent(v);
          if (push && target !== location.search) history.pushState(null, "", target); else history.replaceState(null, "", target);
        }
        var failed = data.chunks.filter(function (c) { return !c.techniques; });
        if (failed.length === data.chunks.length && data.chunks.length) {
          DecodePanel.videoNote($("tech"), "Not checked: " + (failed[0].errors.techniques || "no result") + ".", true);
          break;
        }
        data.chunks.forEach(function (c) {
          seen++;
          if (!c.techniques || !c.techniques.length) return;
          flagged++;
          c.techniques.forEach(function (t) { counts[t.name] = (counts[t.name] || 0) + 1; });
          list.appendChild(DecodePanel.renderChunk(c, video, hooks.onSeek));
        });
        offset = data.next;
        DecodePanel.videoProgress($("post"), $("tech"), { seen: seen, total: data.total, flagged: flagged, counts: counts, done: offset == null, truncated: video.truncated });
      }
    } catch (e) {
      if (mine !== videoRun) return;
      if (!video) say("The server could not be reached. Check your connection and try again.", "error");
      else DecodePanel.videoNote($("tech"), "Stopped early: the connection was lost.", true);
    } finally {
      if (mine === videoRun) refresh();
    }
  }

  async function run(push) {
    var v = input.value.trim();
    if (!v || go.disabled) return;
    var url = isUrl(v);
    go.disabled = true;
    videoRun++;
    startThread(null);
    if (isVideo(v)) { $("result").hidden = $("bot").hidden = $("sim").hidden = true; return runVideo(v, push); }
    $("result").hidden = $("bot").hidden = $("sim").hidden = true;
    say(url ? "Reading the post and checking it…" : "Checking the text…", "", true);
    try {
      var r = await fetch(API + "/api/analyze", { method: "POST", headers: { "Content-Type": "application/json" },
                                             body: JSON.stringify(url ? { url: v } : { text: v }) });
      var data = await r.json().catch(function () { return null; });
      if (r.status === 429) return say((data && data.detail) || "Too many requests. Try again in a minute.", "error");
      if (!r.ok || !data) return say("That input could not be analysed. Paste a Bluesky post link or up to " + MAX + " characters of text.", "error");
      if (url && !data.post) return say((data.errors && data.errors.post) || "The post could not be read.", "error");
      DecodePanel.renderPost($("post"), data, v);
      DecodePanel.renderTechniques($("tech"), data);
      DecodePanel.renderBot($("bot"), data);
      DecodePanel.renderSimilar($("sim"), data);
      DecodePanel.linkHighlights($("post"), $("tech"));
      status.hidden = true;
      $("result").hidden = $("bot").hidden = $("sim").hidden = false;
      // a link is shareable; pasted text stays out of the address bar
      var target = url ? "?q=" + encodeURIComponent(v) : location.pathname;
      if (push && target !== location.search) history.pushState(null, "", target);
      else history.replaceState(null, "", target);
      if (url) startThread(v);
    } catch (e) {
      say("The server could not be reached. Check your connection and try again.", "error");
    } finally {
      refresh();
    }
  }

  input.addEventListener("input", refresh);
  input.addEventListener("keydown", function (e) { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) run(true); });
  $("form").addEventListener("submit", function (e) { e.preventDefault(); run(true); });
  // Back and forward walk through the posts the reader opened.
  addEventListener("popstate", function () {
    var q = new URLSearchParams(location.search).get("q");
    input.value = q || ""; refresh();
    if (q) run(false); else location.reload();
  });
  if ($("new")) $("new").addEventListener("click", function () { input.value = ""; refresh(); input.focus(); window.scrollTo({ top: 0 }); });
  document.querySelectorAll(".chip").forEach(function (c) {
    c.addEventListener("click", function () { input.value = c.dataset.ex; refresh(); run(true); });
  });

  window.DecodeApp = {
    hooks: hooks,
    analyze: function (value) { input.value = value; refresh(); window.scrollTo({ top: 0 }); run(true); }
  };

  var q = new URLSearchParams(location.search).get("q");
  if (q) { input.value = q; refresh(); run(); } else refresh();
})();
