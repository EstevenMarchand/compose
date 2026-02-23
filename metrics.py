import json
import re
import subprocess
from pathlib import Path
from datetime import datetime

def run(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True, shell=True)
    return p.returncode, p.stdout, p.stderr

def parse_total_coverage(text):
    # Busca: total: (statements) XX.X%
    m = re.search(r"total:\s+\(statements\)\s+([\d.]+)%", text)
    return float(m.group(1)) if m else None

def safe_read_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None

report = {
    "generated_at": datetime.now().isoformat(timespec="seconds"),
    "lint_exit_code": None,
    "lint_issues": None,
    "test_exit_code": None,
    "coverage_total_percent": None,
    "notes": []
}

# 1) Lint -> JSON
code, out, err = run("golangci-lint run --out-format json")
report["lint_exit_code"] = code

if out.strip():
    Path("golangci-lint-report.json").write_text(out, encoding="utf-8")
    data = json.loads(out)
    report["lint_issues"] = len(data.get("Issues", []))
else:
    report["lint_issues"] = 0
    if code != 0:
        report["notes"].append("golangci-lint no devolvió JSON; revisa configuración/linters.")
        if err.strip():
            Path("golangci-lint-error.txt").write_text(err, encoding="utf-8")

# 2) Tests + coverage
code, out, err = run("go test ./... -coverprofile=coverage.out")
report["test_exit_code"] = code

if Path("coverage.out").exists():
    code2, out2, err2 = run("go tool cover -func=coverage.out")
    Path("coverage.txt").write_text(out2, encoding="utf-8")
    report["coverage_total_percent"] = parse_total_coverage(out2)
else:
    report["notes"].append("No se generó coverage.out (los tests fallaron o no se ejecutaron).")
    if err.strip():
        Path("go-test-error.txt").write_text(err, encoding="utf-8")

# Guardar JSON
Path("metrics.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

# HTML bonito
coverage = report["coverage_total_percent"]
lint_issues = report["lint_issues"]
lint_code = report["lint_exit_code"]
test_code = report["test_exit_code"]

def badge(text, kind):
    # kind: ok, warn, bad
    cls = {"ok":"ok","warn":"warn","bad":"bad"}[kind]
    return f'<span class="badge {cls}">{text}</span>'

# Badges
lint_badge = badge("OK", "ok") if lint_code == 0 else badge(f"FALLÓ (exit {lint_code})", "bad")
issues_badge = badge(f"{lint_issues} issues", "ok") if (lint_issues == 0) else badge(f"{lint_issues} issues", "warn")
test_badge = badge("OK", "ok") if test_code == 0 else badge(f"FALLÓ (exit {test_code})", "bad")

if coverage is None:
    cov_badge = badge("N/A", "warn")
else:
    cov_kind = "ok" if coverage >= 80 else ("warn" if coverage >= 50 else "bad")
    cov_badge = badge(f"{coverage:.1f}%", cov_kind)

notes_html = ""
if report["notes"]:
    notes_html = "<ul>" + "".join(f"<li>{n}</li>" for n in report["notes"]) + "</ul>"
else:
    notes_html = "<p class='muted'>Sin notas.</p>"

html = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Reporte de métricas</title>
  <style>
    body {{ font-family: Arial, Helvetica, sans-serif; background:#0b0f14; color:#e6edf3; margin:0; }}
    .wrap {{ max-width: 980px; margin: 0 auto; padding: 28px 16px 40px; }}
    h1 {{ margin: 0 0 6px; font-size: 26px; }}
    .sub {{ color:#9fb1c1; margin:0 0 18px; }}
    .card {{ background:#111824; border:1px solid #1f2a3a; border-radius:14px; padding:16px; margin: 12px 0; }}
    table {{ width:100%; border-collapse: collapse; }}
    th, td {{ text-align:left; padding: 10px 8px; border-bottom: 1px solid #1f2a3a; }}
    th {{ color:#9fb1c1; font-weight: 600; }}
    .badge {{ display:inline-block; padding: 6px 10px; border-radius:999px; font-weight:700; font-size: 12px; }}
    .ok {{ background:#113a2b; color:#7ee2b8; border:1px solid #1e5a41; }}
    .warn {{ background:#3a2a11; color:#ffd08a; border:1px solid #5a431e; }}
    .bad {{ background:#3a1111; color:#ff9a9a; border:1px solid #5a1e1e; }}
    .muted {{ color:#9fb1c1; }}
    .grid {{ display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }}
    @media (max-width: 720px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    code {{ background:#0d1520; border:1px solid #1f2a3a; padding:2px 6px; border-radius:8px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Reporte de métricas</h1>
    <p class="sub">Generado: <b>{report["generated_at"]}</b></p>

    <div class="grid">
      <div class="card">
        <h3 style="margin:0 0 10px;">Lint</h3>
        <table>
          <tr><th>Estado</th><td>{lint_badge}</td></tr>
          <tr><th>Issues</th><td>{issues_badge}</td></tr>
          <tr><th>Archivo</th><td><code>golangci-lint-report.json</code></td></tr>
        </table>
      </div>

      <div class="card">
        <h3 style="margin:0 0 10px;">Tests</h3>
        <table>
          <tr><th>Estado</th><td>{test_badge}</td></tr>
          <tr><th>Coverage total</th><td>{cov_badge}</td></tr>
          <tr><th>Archivos</th><td><code>coverage.out</code> y <code>coverage.txt</code></td></tr>
        </table>
      </div>
    </div>

    <div class="card">
      <h3 style="margin:0 0 10px;">Notas</h3>
      {notes_html}
    </div>

    <div class="card">
      <h3 style="margin:0 0 10px;">Salida</h3>
      <p class="muted" style="margin:0;">
        - <code>metrics.json</code><br/>
        - <code>metrics.html</code>
      </p>
    </div>
  </div>
</body>
</html>
"""

Path("metrics.html").write_text(html, encoding="utf-8")

print("✅ Generado: metrics.json y metrics.html")
