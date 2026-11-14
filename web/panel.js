/* Renders an /api/analyze response into DOM nodes. Shared by the web page and
   (later) the extension. Post text, handles and reasons are untrusted: every
   string goes in through textContent, links are checked, and no markup is ever built from strings. */
(function () {
  "use strict";

  var NEAR = 0.7;      // same threshold bot_score uses for "near-identical"
  var WINDOW = 600;    // seconds, same as similar.summary()

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }

  function icon(d, cls) {
    var ns = "http://www.w3.org/2000/svg";
    var s = document.createElementNS(ns, "svg");
    s.setAttribute("viewBox", "0 0 24 24");
    s.setAttribute("aria-hidden", "true");
    s.setAttribute("class", "ic" + (cls ? " " + cls : ""));
    var p = document.createElementNS(ns, "path");
    p.setAttribute("d", d);
    s.appendChild(p);
    return s;
  }

  var ICONS = {
    bot: "M12 2a1 1 0 0 1 1 1v2h4a3 3 0 0 1 3 3v8a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V8a3 3 0 0 1 3-3h4V3a1 1 0 0 1 1-1zM8.5 10a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm7 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zM9 15v1.5h6V15H9zM1 10h2v5H1v-5zm20 0h2v5h-2v-5z",
    quote: "M4 5h7v7c0 3.3-2.2 6-5.5 7l-.8-1.8C6.600 16.500 7.800 15 8 13H4V5zm9 0h7v7c0 3.300-2.200 6-5.500 7l-.800-1.800c1.900-.700 3.100-2.200 3.300-4.200h-4V5z",
    link: "M14 3h7v7h-2V6.400l-8.300 8.300-1.400-1.400L17.600 5H14V3zM5 5h6v2H5v12h12v-6h2v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V7a2 2 0 0 1 2-2z"
  };

  function safeUrl(u) {
    try {
      var p = new URL(String(u));
      return p.protocol === "https:" || p.protocol === "http:" ? p.href : null;
    } catch (e) { return null; }
  }

  function avatar(name, cls) {
    var a = el("div", "avatar" + (cls ? " " + cls : ""));
    var ch = String(name || "?").replace(/^@/, "").charAt(0).toUpperCase() || "?";
    a.textContent = ch;
    // stable colour per name, so the same account looks the same everywhere
    var h = 0, s = String(name || "");
    for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 360;
    a.style.background = "hsl(" + h + " 45% 32%)";
    return a;
  }

  // "name.bsky.social" is the default handle form; the suffix adds nothing for a reader
  function shortName(handle) { return String(handle).replace(/\.bsky\.social$/, ""); }

  function fmtTime(ts) {
    if (!ts) return "";
    var d = new Date(ts * 1000);
    return d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" }) + " · " +
      d.toLocaleDateString([], { month: "short", day: "numeric", year: "numeric" });
  }

  function gap(ts, base) {
    if (!ts || !base) return ts ? fmtTime(ts) : "";
    var s = Math.round(ts - base), a = Math.abs(s), txt;
    if (a < 60) txt = a + " s";
    else if (a < 3600) txt = Math.round(a / 60) + " min";
    else if (a < 86400) txt = Math.round(a / 3600) + " h";
    else txt = Math.round(a / 86400) + " d";
    return a < 5 ? "same moment" : txt + (s < 0 ? " earlier" : " later");
  }

  /* ---- quote highlighting ------------------------------------------------ */

  function quoteRange(text, quote) {
    var parts = String(quote).trim().split(/\s+/).map(function (w) {
      return w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/['\u2018\u2019]/g, "['\u2018\u2019]")
              .replace(/["\u201c\u201d]/g, "[\"\u201c\u201d]");
    });
    if (!parts[0]) return null;
    var m;
    try { m = new RegExp(parts.join("\\s+"), "i").exec(text); } catch (e) { return null; }
    return m ? [m.index, m.index + m[0].length] : null;
  }

  function highlighted(text, techniques) {
    var ranges = [];
    (techniques || []).forEach(function (t, i) {
      var r = quoteRange(text, t.quote);
      if (r) ranges.push({ a: r[0], b: r[1], ids: [i], names: [t.name] });
    });
    ranges.sort(function (x, y) { return x.a - y.a; });
    var merged = [];
    ranges.forEach(function (r) {
      var last = merged[merged.length - 1];
      if (last && r.a < last.b) {
        last.b = Math.max(last.b, r.b);
        last.ids = last.ids.concat(r.ids);
        r.names.forEach(function (n) { if (last.names.indexOf(n) < 0) last.names.push(n); });
      } else merged.push(r);
    });
    var box = el("div", "post-text"), at = 0;
    merged.forEach(function (r) {
      if (r.a > at) box.appendChild(document.createTextNode(text.slice(at, r.a)));
      var m = el("mark", "hl", text.slice(r.a, r.b));
      m.title = r.names.join(", ");
      m.dataset.t = r.ids.join(",");
      box.appendChild(m);
      at = r.b;
    });
    if (at < text.length) box.appendChild(document.createTextNode(text.slice(at)));
    return box;
  }

  /* ---- sections ----------------------------------------------------------- */

  function verdictLevel(bot) {
    if (!bot) return "";
    return bot.score >= 0.6 ? "high" : bot.score >= 0.3 ? "mid" : "low";
  }

  function stat(value, label) {
    var s = el("span", "stat");
    s.appendChild(el("b", null, value));
    s.appendChild(document.createTextNode(" " + label));
    return s;
  }

  // A post's images and video cover frames. Alt text is untrusted: set as a property, never as HTML.
  function mediaRow(post) {
    var row = el("div", "post-media");
    ((post && post.media) || []).forEach(function (m) {
      var src = safeUrl(m.url);
      if (!src) return;
      var img = document.createElement("img");
      img.alt = m.alt || (m.type === "video" ? "Video cover frame, no description" : "Image, no description");
      img.loading = "lazy"; img.referrerPolicy = "no-referrer"; img.src = src;
      row.appendChild(img);
    });
    return row;
  }

  // The post this one quotes, as its own bordered card: someone else wrote it, so it carries their handle.
  // Only techniques found in the quoted post are highlighted here; blanks keep the hover indexes in step.
  function quoteCard(post, techniques) {
    var q = post && post.quoted;
    if (!q) return document.createDocumentFragment();
    var card = el("div", "quoted");
    var src = safeUrl(q.url), who = el(src ? "a" : "div", "quoted-by", "Quoted post by @" + q.author);
    if (src) { who.href = src; who.target = "_blank"; who.rel = "noopener noreferrer"; }
    card.appendChild(who);
    card.appendChild(highlighted(q.text, (techniques || []).map(function (t) {
      return t.source === "quoted" ? t : { name: "", quote: "" };
    })));
    card.appendChild(mediaRow(q));
    return card;
  }

  // The post itself, laid out like a focused post, with quotes highlighted.
  function renderPost(node, a, inputText) {
    node.textContent = "";
    var post = a.post, text = post ? post.text : (inputText || "");
    var art = el("article", "post");
    var head = el("div", "post-head");
    head.appendChild(avatar(post ? post.author : "T", "lg"));
    var who = el("div", "who");
    who.appendChild(el("div", "name", post ? shortName(post.author) : "Pasted text"));
    who.appendChild(el("div", "handle", post ? "@" + post.author : "No author to check"));
    var lvl = verdictLevel(a.bot);
    if (a.bot && lvl !== "low") {
      var tag = el("div", "auto-tag " + lvl);
      tag.appendChild(icon(ICONS.bot));
      tag.appendChild(el("span", null, lvl === "high" ? "Bot-like signals" : "Some bot-like signals"));
      tag.title = "Bot-likeness score " + a.bot.score.toFixed(2) + ". A suspicion score, not a probability.";
      who.appendChild(tag);
    }
    head.appendChild(who);
    var src = post && safeUrl(post.url);
    if (src) {
      var open = el("a", "open");
      open.href = src; open.target = "_blank"; open.rel = "noopener noreferrer";
      open.setAttribute("aria-label", "Open the original post");
      open.appendChild(icon(ICONS.link));
      head.appendChild(open);
    }
    art.appendChild(head);
    art.appendChild(highlighted(text, a.techniques));
    art.appendChild(mediaRow(post));
    art.appendChild(quoteCard(post, a.techniques));
    var meta = el("div", "post-meta", (post && post.ts ? fmtTime(post.ts) + " · " : "") + (post ? "Bluesky" : "Pasted text"));
    art.appendChild(meta);

    var stats = el("div", "stats");
    stats.appendChild(stat(a.techniques ? String(a.techniques.length) : "–", a.techniques && a.techniques.length === 1 ? "Technique" : "Techniques"));
    var near = (a.similar || []).filter(function (i) { return i.overlap >= NEAR; }).length;
    stats.appendChild(stat(a.similar ? String(near) : "–", near === 1 ? "Copy" : "Copies"));
    stats.appendChild(stat(a.bot ? a.bot.score.toFixed(2) : "–", "Bot-likeness"));
    art.appendChild(stats);
    node.appendChild(art);
  }

  function note(cls, text) { return el("p", "note " + (cls || ""), text); }

  function renderTechniques(node, a) {
    node.textContent = "";
    node.appendChild(el("h2", "sec-title", "Techniques found in this post"));
    if ((a.errors || {}).media) node.appendChild(note("warn", a.errors.media.replace(/^not enough data: /, "Not enough data: ")));
    if (!a.techniques) {
      node.appendChild(note("warn", "Not checked: " + ((a.errors || {}).techniques || (a.errors || {}).post || "no result")));
      return;
    }
    if (!a.techniques.length) {
      node.appendChild(note("", "No manipulation techniques found."));
      return;
    }
    a.techniques.forEach(function (t, i) {
      var row = el("div", "tech");
      row.dataset.t = String(i);
      var badge = el("div", "tech-ic");
      badge.appendChild(icon(ICONS.quote));
      row.appendChild(badge);
      var body = el("div", "tech-body");
      body.appendChild(el("div", "tech-name", t.name));
      body.appendChild(el("blockquote", "tech-quote", t.quote));
      if (t.source === "image") body.appendChild(el("p", "tech-why", "Quote read from the post's image."));
      if (t.source === "quoted") body.appendChild(el("p", "tech-why", "Found in the quoted post" + (a.post && a.post.quoted ? " by @" + a.post.quoted.author : "") + ", not in this author's own words."));
      if (t.why) body.appendChild(el("p", "tech-why", t.why));
      row.appendChild(body);
      node.appendChild(row);
    });
  }

  function renderBot(node, a) {
    node.textContent = "";
    var h = el("h2", "card-title", "Bot-likeness score");
    h.title = "A suspicion score from posting rhythm, profile and text reuse. It is not a probability.";
    node.appendChild(h);
    if (!a.bot) {
      node.appendChild(note(a.post ? "warn" : "",
        a.post ? "Not enough data: " + ((a.errors || {}).bot || "author could not be checked")
               : "Paste a post link to check the author."));
      return;
    }
    var lvl = verdictLevel(a.bot);
    var top = el("div", "bot-top");
    top.appendChild(el("span", "bot-num " + lvl, a.bot.score.toFixed(2)));
    top.appendChild(el("span", "bot-verdict", a.bot.verdict));
    node.appendChild(top);
    var bar = el("div", "bar");
    bar.setAttribute("role", "meter");
    bar.setAttribute("aria-valuemin", "0"); bar.setAttribute("aria-valuemax", "1");
    bar.setAttribute("aria-valuenow", String(a.bot.score));
    bar.setAttribute("aria-label", "Bot-likeness score");
    var fill = el("div", "bar-fill " + lvl);
    fill.style.width = Math.max(2, Math.round(a.bot.score * 100)) + "%";
    bar.appendChild(fill);
    node.appendChild(bar);
    if (a.bot.reasons && a.bot.reasons.length) {
      var ul = el("ul", "reasons");
      a.bot.reasons.forEach(function (r) { ul.appendChild(el("li", null, r)); });
      node.appendChild(ul);
    }
    var names = { cadence: "posting rhythm", text_reuse: "copies of this text", profile: "profile" };
    var checked = (a.bot.checked || []).map(function (c) { return names[c] || c; });
    node.appendChild(note("dim", checked.length ? "Checked: " + checked.join(", ") + "." : "Nothing could be checked."));
    node.appendChild(note("dim", "A suspicion score, not a probability."));
  }

  function similarSummary(items, postTs) {
    if (!items.length) return "No other accounts found posting this text.";
    var near = items.filter(function (i) { return i.overlap >= NEAR; });
    if (!near.length) return items.length + (items.length === 1 ? " post shares" : " posts share") + " parts of this text, none near-identical.";
    var line = near.length + (near.length === 1 ? " account" : " accounts") + " posted near-identical text";
    if (postTs) {
      var quick = near.filter(function (i) { return i.ts && Math.abs(i.ts - postTs) <= WINDOW; }).length;
      if (quick) line += ", " + quick + " within 10 minutes";
    }
    return line + ".";
  }

  function renderSimilar(node, a) {
    node.textContent = "";
    node.appendChild(el("h2", "card-title", "Who else posted this"));
    if (!a.similar) {
      node.appendChild(note("warn", ((a.errors || {}).similar || (a.errors || {}).post || "Not checked").replace(/^not enough data: /, "Not enough data: ")));
      return;
    }
    node.appendChild(el("p", "sim-summary", similarSummary(a.similar, a.post && a.post.ts)));
    a.similar.forEach(function (i) {
      var row = el("div", "sim");
      row.appendChild(avatar(i.author));
      var body = el("div", "sim-body");
      var top = el("div", "sim-top");
      var who = el("span", "sim-author", "@" + shortName(i.author));
      who.title = "@" + i.author;
      top.appendChild(who);
      var when = gap(i.ts, a.post && a.post.ts);
      if (when) top.appendChild(el("span", "sim-when", "· " + when));
      body.appendChild(top);
      body.appendChild(el("div", "sim-text", i.text));
      row.appendChild(body);
      var url = safeUrl(i.url);
      var pill = el(url ? "a" : "span", "pill" + (i.overlap >= NEAR ? " strong" : ""), Math.round(i.overlap * 100) + "%");
      pill.title = Math.round(i.overlap * 100) + "% of the wording overlaps";
      if (url) { pill.href = url; pill.target = "_blank"; pill.rel = "noopener noreferrer"; }
      row.appendChild(pill);
      node.appendChild(row);
    });
    if (a.similar.length) node.appendChild(note("dim", "Matching text shows coordination, not automation. People share copypasta too."));
  }

  var STANCE = { supports: "Supports", challenges: "Challenges", "adds context": "Adds context" };

  // What live web pages say about the post's main claim. Reports sources, never a true/false verdict.
  function renderCoverage(node, a) {
    node.textContent = "";
    node.appendChild(el("h2", "card-title", "What live sources say"));
    var c = a.coverage;
    if (!c) {
      node.appendChild(note("warn", ((a.errors || {}).coverage || (a.errors || {}).post || "Not checked").replace(/^not enough data: /, "Not enough data: ")));
      return;
    }
    node.appendChild(el("p", "cov-claim", "Claim checked: " + c.claim.statement));
    var byId = {};
    c.sources.forEach(function (s) { byId[s.id] = s; });
    if (!c.points.length) node.appendChild(note("warn", "Not enough data: the pages that were read say nothing quotable about this claim."));
    c.points.forEach(function (p) {
      var row = el("div", "cov"), s = byId[p.source] || {};
      row.appendChild(el("span", "cov-stance " + p.stance.replace(" ", "-"), STANCE[p.stance] || p.stance));
      row.appendChild(el("p", "cov-text", p.text));
      row.appendChild(el("blockquote", "cov-quote", p.quote));
      row.appendChild(sourceLink(s, "cov-src"));
      node.appendChild(row);
    });
    var list = el("ul", "cov-sources");
    c.sources.forEach(function (s) {
      var li = el("li");
      li.appendChild(sourceLink(s));
      li.appendChild(document.createTextNode(s.read ? " · read in full" : " · found, could not be read"));
      list.appendChild(li);
    });
    node.appendChild(list);
    if (c.by_country) renderCountries(node, c.by_country);
    node.appendChild(note("dim", "Searched and read live at " + fmtTime(c.checked_at) + " through the Oxylabs Web API. A sample of the web, not a verdict on the post."));
  }

  // The same search run from each country. A site only one country sees is marked.
  function renderCountries(node, countries) {
    var seenIn = {};
    countries.forEach(function (c) { (c.sources || []).forEach(function (s) { seenIn[s.domain] = (seenIn[s.domain] || 0) + 1; }); });
    node.appendChild(el("h3", "cov-sub", "Same search, three countries"));
    countries.forEach(function (c) {
      var row = el("div", "cov-country");
      row.appendChild(el("b", null, c.name));
      if (!c.sources) row.appendChild(el("span", "warn", "Not enough data: this search failed."));
      else if (!c.sources.length) row.appendChild(el("span", null, "No results."));
      else c.sources.forEach(function (s) {
        var only = seenIn[s.domain] === 1;
        var a = sourceLink(s, only ? "only" : "");
        if (only) a.title = "Only in the results from " + c.name + (s.title ? ": " + s.title : "");
        row.appendChild(a);
      });
      node.appendChild(row);
    });
    node.appendChild(note("dim", "Underlined sites appear in one country's results only. The points above use the pages from the first country with results."));
  }

  function sourceLink(s, cls) {
    var url = safeUrl(s.url), n = el(url ? "a" : "span", cls, s.domain || s.id);
    if (url) { n.href = url; n.target = "_blank"; n.rel = "noopener noreferrer"; n.title = s.title || ""; }
    return n;
  }

  // Hovering a technique lights up its quote in the post, and the other way round.
  function linkHighlights(postNode, techNode) {
    function set(ids, on) {
      ids.forEach(function (id) {
        var row = techNode.querySelector('.tech[data-t="' + id + '"]');
        if (row) row.classList.toggle("on", on);
      });
      postNode.querySelectorAll("mark.hl").forEach(function (m) {
        var mine = m.dataset.t.split(",");
        if (ids.some(function (id) { return mine.indexOf(id) >= 0; })) m.classList.toggle("on", on);
      });
    }
    techNode.querySelectorAll(".tech").forEach(function (row) {
      row.addEventListener("mouseenter", function () { set([row.dataset.t], true); });
      row.addEventListener("mouseleave", function () { set([row.dataset.t], false); });
    });
    postNode.querySelectorAll("mark.hl").forEach(function (m) {
      m.addEventListener("mouseenter", function () { set(m.dataset.t.split(","), true); });
      m.addEventListener("mouseleave", function () { set(m.dataset.t.split(","), false); });
    });
  }

  function compact(n) {
    return n >= 1000 ? (n / 1000).toFixed(n >= 10000 ? 0 : 1).replace(/\.0$/, "") + "K" : String(n || 0);
  }

  function replyAvatar(post) {
    var src = post.avatar && safeUrl(post.avatar);
    if (!src) return avatar(post.author);
    var img = document.createElement("img");
    img.className = "avatar"; img.alt = ""; img.loading = "lazy"; img.referrerPolicy = "no-referrer";
    img.src = src;
    img.addEventListener("error", function () { img.replaceWith(avatar(post.author)); });
    return img;
  }

  // One reply in the thread: its own bot-likeness score, and techniques when it was scanned.
  // Clicking it calls onOpen(url) so the page can make it the main post.
  function renderReply(item, onOpen) {
    var post = item.post, bot = item.bot;
    var row = el("article", "reply");
    row.appendChild(replyAvatar(post));
    var body = el("div", "reply-body");

    var head = el("div", "reply-head");
    head.appendChild(el("span", "reply-name", post.name || shortName(post.author)));
    head.appendChild(el("span", "reply-handle", "@" + post.author));
    if (post.ts) head.appendChild(el("span", "reply-time", "· " + new Date(post.ts * 1000).toLocaleDateString([], { month: "short", day: "numeric" })));
    var badge = el("span", "score " + (bot ? verdictLevel(bot) : "none"), bot ? "Bot-likeness " + bot.score.toFixed(2) : "Bot-likeness n/a");
    badge.title = bot ? bot.verdict + (bot.reasons.length ? ": " + bot.reasons.join("; ") : "") + ". A suspicion score, not a probability."
                      : "Not enough data: " + ((item.errors || {}).bot || "author could not be checked");
    head.appendChild(badge);
    body.appendChild(head);

    body.appendChild(highlighted(post.text, item.techniques));
    body.appendChild(mediaRow(post));
    body.appendChild(quoteCard(post, item.techniques));

    if (item.techniques && item.techniques.length) {
      var list = el("div", "reply-techs");
      item.techniques.forEach(function (t) {
        var line = el("div", "reply-tech");
        line.appendChild(el("b", null, t.name));
        if (t.why) line.appendChild(document.createTextNode(" " + t.why));
        if (t.source === "quoted") line.appendChild(document.createTextNode(" (Found in the quoted post.)"));
        list.appendChild(line);
      });
      body.appendChild(list);
    } else if (item.techniques) {
      body.appendChild(el("div", "reply-note", "Scanned for techniques: none found."));
    }
    if ((item.errors || {}).media) body.appendChild(el("div", "reply-note warn", item.errors.media));
    if (!item.techniques && (item.errors || {}).techniques) {
      body.appendChild(el("div", "reply-note warn", "Techniques not checked: " + item.errors.techniques));
    }

    var foot = el("div", "reply-foot");
    foot.appendChild(el("span", null, compact(post.replies) + (post.replies === 1 ? " reply" : " replies")));
    foot.appendChild(el("span", null, compact(post.likes) + (post.likes === 1 ? " like" : " likes")));
    body.appendChild(foot);
    row.appendChild(body);

    var url = safeUrl(post.url);
    if (url && onOpen) {
      row.tabIndex = 0;
      row.setAttribute("role", "link");
      row.setAttribute("aria-label", "Analyse this reply by " + post.author);
      row.addEventListener("click", function () { if (!String(window.getSelection())) onOpen(url); });
      row.addEventListener("keydown", function (e) { if (e.key === "Enter") onOpen(url); });
    }
    return row;
  }

  // Everything in one column, for the extension panel.
  function renderPanel(node, analysis, inputText) {
    node.textContent = "";
    var parts = ["post", "tech", "bot", "sim", "cov"].map(function (c) {
      var s = el("section", "panel-sec " + (c === "post" || c === "tech" ? c : "card"));
      node.appendChild(s);
      return s;
    });
    renderPost(parts[0], analysis, inputText);
    renderTechniques(parts[1], analysis);
    renderBot(parts[2], analysis);
    renderSimilar(parts[3], analysis);
    renderCoverage(parts[4], analysis);
    linkHighlights(parts[0], parts[1]);
  }

  window.DecodePanel = {
    renderPanel: renderPanel, renderPost: renderPost, renderTechniques: renderTechniques,
    renderBot: renderBot, renderSimilar: renderSimilar, renderCoverage: renderCoverage, renderReply: renderReply, linkHighlights: linkHighlights
  };
})();
