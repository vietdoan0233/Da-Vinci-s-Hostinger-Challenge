/* Draws eval/results.json. Numbers are shown exactly as the eval scripts wrote them:
   a missing section says "not measured yet" and never shows a placeholder figure. */
(function () {
  "use strict";
  var root = document.getElementById("out"), out = root;  // out is the section being drawn

  function el(tag, cls, text) {
    var n = document.createElement(tag);
    if (cls) n.className = cls;
    if (text != null) n.textContent = text;
    return n;
  }
  function add(parent, tag, cls, text) { var n = el(tag, cls, text); parent.appendChild(n); return n; }
  // Whole percents, except small non-zero rates, which would otherwise read as a misleading "0%".
  function pct(v) {
    var x = v * 100;
    if (x > 0 && x < 1) return x < 0.1 ? "<0.1%" : x.toFixed(1) + "%";
    return Math.round(x) + "%";
  }
  function val(r) { return r.n ? r.k / r.n : r.value; }
  function range(r) { return r.ci95 ? "95% range " + pct(r.ci95[0]) + "–" + pct(r.ci95[1]) : ""; }

  // The count and range behind a figure, shown when the reader hovers it. The sample size itself
  // is stated in each section's text, so the tables carry the main figure only.
  function detail(r) { return r.k + " of " + r.n + (r.ci95 ? " · " + range(r) : ""); }

  // The rate on a 0 to 100% track: a tick at the measured value, a band over its 95% range.
  function meter(r) {
    var m = el("div", "meter");
    m.setAttribute("aria-hidden", "true");  // the same figures are in the text beside it
    if (r.ci95) {
      var band = add(m, "span", "band");
      band.style.left = r.ci95[0] * 100 + "%";
      band.style.width = Math.max(1, (r.ci95[1] - r.ci95[0]) * 100) + "%";
    }
    add(m, "span", "tick").style.left = val(r) * 100 + "%";
    return m;
  }

  function cell(r) {
    var td = el("td", "n");
    if (!r) { td.textContent = "–"; return td; }
    var rate = add(td, "div", "rate");
    rate.appendChild(meter(r));
    add(rate, "span", null, pct(val(r)));
    td.title = detail(r);
    return td;
  }

  function tile(parent, label, r, plain) {
    var t = add(parent, "div", "tile");
    add(t, "div", "label", label);
    add(t, "div", "num", plain != null ? plain : r ? pct(val(r)) : "–");
    if (r) { t.appendChild(meter(r)); t.title = detail(r); }
  }

  function table(parent, heads) {
    var wrap = add(parent, "div", "scroll"), t = add(wrap, "table"), tr = add(add(t, "thead"), "tr");
    heads.forEach(function (h, i) { add(tr, "th", i ? "n" : null, h); });
    return add(t, "tbody");
  }

  function caveats(parent, list) {
    var box = add(parent, "div", "caveats");
    add(box, "h3", null, "Read these numbers with this in mind");
    var ul = add(box, "ul");
    (list || []).forEach(function (c) { add(ul, "li", null, c); });
  }

  function section(id, title, data, draw) {
    out = add(root, "section", "sec");
    out.id = id;  // the links at the top of the page jump here
    var head = add(out, "div", "sec-head");
    add(head, "h2", null, title);
    add(head, "span", "run" + (data ? "" : " warn"), data ? "Last run " + data.run_at : "Not run yet");
    if (!data) { add(out, "div", "none", "Not measured yet. The script for this has not been run."); return; }
    add(out, "p", "dim", data.what);
    draw(data);
  }

  function techniques(d) {
    var tiles = add(out, "div", "tiles");
    tile(tiles, "Precision: of the techniques it flagged, how many the annotators also marked", d.micro.precision);
    tile(tiles, "Recall: of the techniques the annotators marked, how many it found", d.micro.recall);
    tile(tiles, "False alarms on memes with no technique", d.false_alarms.memes_with_no_technique);
    tile(tiles, "False alarms on factual posts (forecasts, scores, filings)", d.false_alarms.neutral_posts);
    add(out, "p", "meta", "Micro-F1 " + d.micro.f1.toFixed(3) + " on " + d.n_memes + " labelled meme texts and " + d.n_neutral +
      " factual posts. Micro-F1 is the measure SemEval-2021 Task 6 used. " + (d.not_answered ? d.not_answered + " texts got no answer and are not counted. " : "") +
      "Detector: " + d.detector.where + (d.detector.server_version ? ", version " + d.detector.server_version : "") + ", prompt version " + d.detector.prompt_version + ". Model: " + d.detector.model + ".");
    add(out, "h3", null, "By technique");
    var body = table(out, ["Technique", "Labelled examples", "Precision", "Recall"]);
    d.per_technique.forEach(function (r) {
      var tr = add(body, "tr", r.reportable ? null : "weak");
      add(tr, "td", null, r.technique + (r.reportable ? "" : " (too few examples to rely on)"));
      add(tr, "td", "n", String(r.labelled));
      tr.appendChild(cell(r.precision)); tr.appendChild(cell(r.recall));
    });
    caveats(out, d.caveats);
  }

  function botRows(body, now, before, label) {
    now.forEach(function (r, i) {
      var tr = add(body, "tr");
      add(tr, "td", null, label + ", score " + r.threshold + " or more");
      tr.appendChild(cell(r.recall));
      var b = before && before[i] ? before[i].recall : null;
      var td = add(tr, "td", "n", b ? pct(val(b)) : "–");
      if (b) td.title = detail(b);
      tr.appendChild(cell(r.false_positive_rate));
    });
  }

  function bots(d, before) {
    var h = d.holdout, hb = before && before.holdout;
    var tiles = add(out, "div", "tiles");
    tile(tiles, "Known bots flagged (score 0.3 or more), as the site shows it", h.as_shown[0].recall);
    tile(tiles, "Known bots flagged from behaviour alone, ignoring what the bio says", h.behaviour_only[0].recall);
    tile(tiles, "Real people wrongly flagged (score 0.3 or more)", h.as_shown[0].false_positive_rate);
    add(out, "p", "meta", "Hold-out set: " + h.n_bots + " openly automated accounts and " + h.n_humans + " verified people. These accounts were not looked at while adjusting the score.");
    add(out, "h3", null, "Hold-out set, before and after the posting-schedule rule");
    var body = table(out, ["", "Bots flagged now", "Before the change", "People wrongly flagged now"]);
    botRows(body, h.as_shown, hb && hb.as_shown, "As shown");
    botRows(body, h.behaviour_only, hb && hb.behaviour_only, "Behaviour only");
    add(out, "p", "meta", "What changed: the first run showed that no known bot was caught by its behaviour, only by saying \"bot\" in its bio. The timing test was thrown off by a single long gap. A rule for posting schedules (most gaps the same length) was added and set on a separate tuning set of " +
      d.tune.n_bots + " bots and " + d.tune.n_humans + " people, then measured here.");
    caveats(out, d.caveats);
    var det = add(out, "details");
    add(det, "summary", null, "Every account and its score (" + d.accounts.length + ")");
    var b2 = table(det, ["Account", "Set", "Is", "Score shown", "Behaviour only"]);
    d.accounts.forEach(function (a) {
      var tr = add(b2, "tr");
      var td = add(tr, "td", null, a.handle);
      if (a.reasons && a.reasons.length) td.appendChild(el("div", "of", a.reasons.join("; ")));
      add(tr, "td", "n", a.set);
      add(add(tr, "td", "n"), "span", "tag" + (a.label === "bot" ? " bot" : ""), a.label);
      add(tr, "td", "n " + level(a.score), a.score.toFixed(2)); add(tr, "td", "n " + level(a.behaviour_only), a.behaviour_only.toFixed(2));
    });
    if (d.not_scored && d.not_scored.length) add(out, "p", "meta", d.not_scored.length + " accounts could not be read and are not counted: " + d.not_scored.map(function (a) { return a.handle; }).join(", ") + ".");
  }

  // same cut-offs the panel uses to colour a bot-likeness score
  function level(score) { return score >= 0.6 ? "high" : score >= 0.3 ? "mid" : ""; }

  function similar(d) {
    var tiles = add(out, "div", "tiles");
    tile(tiles, "Unrelated texts wrongly called a copy", d.unrelated_pairs.called_a_copy);
    tile(tiles, "Unrelated texts wrongly shown as similar", d.unrelated_pairs.shown_as_similar);
    add(out, "p", "meta", d.n_texts + " real texts of 12 words or more, each edited ten ways, and " + d.unrelated_pairs.called_a_copy.n + " pairs of unrelated texts. \"Called a copy\" (70% overlap) is what counts against an author's bot-likeness; \"shown\" (30% overlap) is what appears in the list.");
    var body = table(out, ["How the copy was changed", "Still called a copy", "Still shown as similar"]);
    d.edits.forEach(function (e) {
      var tr = add(body, "tr");
      add(tr, "td", null, e.edit); tr.appendChild(cell(e.still_a_copy)); tr.appendChild(cell(e.still_shown));
    });
    caveats(out, d.caveats);
  }

  fetch("eval/results.json").then(function (r) { if (!r.ok) throw new Error(); return r.json(); }).then(function (d) {
    document.getElementById("stamp").textContent = "Results file loaded. Each section shows when its script last ran.";
    section("techniques", "Persuasion techniques", d.techniques, techniques);
    section("bots", "Bot-likeness score", d.bots, function (x) { bots(x, d.bots_before); });
    section("copies", "Copy detection", d.similar, similar);
  }).catch(function () {
    document.getElementById("stamp").textContent = "The results file could not be loaded, so no numbers are shown.";
  });
})();
