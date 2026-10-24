#!/usr/bin/env python3
"""Build data.json from a read_range dump (UNFORMATTED_VALUE) + FORMULA dump of tx links + ledger.json.
Usage: python3 build_snapshot.py sheet_raw.json tx_formulas.csv ledger.json > data.json"""
import json, csv, io, sys, re, datetime
raw, txf, ledgerp = sys.argv[1:4]
d = json.load(open(raw)); ledger = json.load(open(ledgerp))
EXCLUDE_WALLET = re.compile(r'session|sign-in|password|private|seed|api key|token$', re.I)
def serial_date(v):
    try: f = float(v)
    except: return v
    if 40000 < f < 60000: return (datetime.date(1899,12,30)+datetime.timedelta(days=int(f))).isoformat()
    return v
def serial_time(v):
    try: f = float(v)
    except: return v
    if 0 <= f < 1:
        s = round(f*86400); return f"{s//3600:02d}:{s%3600//60:02d}"
    return v
def num(v):
    try: return float(v)
    except: return v
tabs = {}
for r in d['ranges']:
    rows = [x for x in csv.reader(io.StringIO(r['content'])) if any(c.strip() for c in x)]
    hdr = rows[0]; out = []
    for x in rows[1:]:
        x += ['']*(len(hdr)-len(x)); o = dict(zip(hdr, x)); out.append(o)
    tabs[r['sheet']] = {'headers': hdr, 'rows': out}
# normalise dates/times/numbers
for o in tabs['Transactions']['rows']:
    o['Date (WITA)'] = serial_date(o['Date (WITA)']); o['Time'] = serial_time(o['Time'])
    for k in ['Amount','USD Spent','Gas Fee (native)','Gas Fee (USD)']: o[k] = num(o[k])
for o in tabs['Daily Summary']['rows']:
    o['Date'] = serial_date(o['Date'])
    for k in list(o)[1:]: o[k] = num(o[k])
for o in tabs['Candidates']['rows']: o['Date'] = serial_date(o['Date'])
# Wallet tab: drop session/sign-in rows (no session data on a public page)
tabs['Wallet']['rows'] = [o for o in tabs['Wallet']['rows'] if o.get('Field') and not EXCLUDE_WALLET.search(o['Field'])]
# tx links from HYPERLINK formulas (cols M..R => Buy, Sell, Mint)
frows = list(csv.reader(io.StringIO(open(txf).read())))[1:]
for o, f in zip(tabs['Transactions']['rows'], frows):
    m = re.search(r'https://bscscan\.com/tx/0x[0-9a-fA-F]{64}', ','.join(f))
    o['tx'] = m.group(0) if m else ''
holdings = [
  {"collection":"Agent Nakamigos","token":5332,"contract":"0x2D7097E0f28Ea0fEB0b3b44c7d0ee0227d513103","status":"Listed","price_bnb":0.001,"market":"agentpunk","listing":"https://agentpunk.fun/collection/agent-nakamigos?id=5332","note":"Listing 7 hari, belum laku"},
  {"collection":"Agent Nakamigos","token":5333,"contract":"0x2D7097E0f28Ea0fEB0b3b44c7d0ee0227d513103","status":"Listed","price_bnb":0.001,"market":"agentpunk","listing":"https://agentpunk.fun/collection/agent-nakamigos?id=5333","note":"Listing 7 hari, belum laku"},
  {"collection":"AI Agent Chips (CHIPS)","token":258,"contract":"0x1Fe9656b1aF98d663EA88708f10f9e997fCbD89E","status":"Hold","note":"Hold sampai ada market/bid (agentpunk tolak, Element belum ada floor)"},
  {"collection":"Agent Drop Pass (ADPASS)","token":590,"contract":"0x71Bd52c7e0F577B8beAaB8AE1ddE334ABd26720A","status":"Hold","note":"Hold sampai ada market/bid; mint tutup 29 Okt"},
  {"collection":"AIVY Robot (AIVY)","token":3780,"contract":"0x77cCE940d1Fe4808aB6cf8484d45d8B51139E7D6","status":"Hold","note":"Hold; market AIVY belum terverifikasi, belum ada bid"},
  {"collection":"Fluffies (FLUFF)","token":240,"contract":"0x4b2eba0bf5399ec34C37B5Bf1F2749c7751C8c12","status":"Locked","note":"Trading dikunci sampai 10k sold out"},
]
# sanity: every ledger holding is represented
lh = sorted(t for v in ledger['holdings'].values() for t in v)
assert lh == sorted(h['token'] for h in holdings), (lh,)
now = datetime.datetime.now()
out = {
  "generated_wita": now.strftime('%Y-%m-%d %H:%M') + " WITA",
  "sheet_id": "1GWj3ub5nyvV5MHeb_J8ih6W0SQqTxLaTXe7ToHvH_eo",
  "wallet": {"address":"0xC1408fc129512e0d6aaa93022F4B49B68647D94e","chain":"BSC",
             "last_balance_bnb": ledger['last_balance_bnb'], "bnb_usd_ref": ledger.get('bnb_usd_ref',740)},
  "budget": {"cap_usd": ledger['budget_usd'], "spent_usd": ledger['cumulative_usd_spent'], "gas_bnb": ledger['cumulative_gas_bnb']},
  "holdings": holdings,
  "tabs": tabs,
}
json.dump(out, sys.stdout, indent=1, ensure_ascii=False)
