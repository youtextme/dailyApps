from tireless.dailyapps.quality_gate import run_quality_gate


def test_rejects_thin_stub():
    html = """<!DOCTYPE html><html><head>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>x</title></head>
<body data-dailyapps-ready="1"><h1>Hi</h1>
<label>Your input</label><input id="i"/><button id="go">Go</button>
<p id="out"></p>
<script>document.getElementById('go').onclick=()=>{document.getElementById('out').textContent='Ready'};</script>
</body></html>"""
    report = run_quality_gate(html)
    # thin generic scaffold should be dinged
    assert "fatal:too_thin" in report.violations or report.score < 80


def test_accepts_real_interactive_page():
    html = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>Tip calculator</title>
<style>
body { font-family: "Source Sans 3", Georgia, serif;
background: radial-gradient(circle at top, #99f6e4, #fffbeb); }
h1 { font-family: Fraunces, Georgia, serif; }
</style></head>
<body data-dailyapps-ready="1">
<header><h1>Tip</h1><p class="lead">Split the bill with friends quickly.</p></header>
<main>
<label for="bill">Bill</label>
<input id="bill" type="number"/>
<button id="go" type="button">Calculate</button>
<p id="result" aria-live="polite"></p>
</main>
<script>
document.getElementById('go').addEventListener('click', () => {
  const bill = Number(document.getElementById('bill').value || 0);
  document.getElementById('result').textContent = 'Total tip path: ' + (bill * 1.15).toFixed(2);
});
</script>
</body></html>"""
    report = run_quality_gate(html)
    assert report.ok, report.violations
    assert report.score >= 80
