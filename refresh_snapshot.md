# Regenerate data.json (fallback snapshot)

index.html tries the live Sheet first (gviz CSV per tab, needs "Anyone with the link: Viewer").
If that fails it falls back to `data.json`. Regenerate the snapshot whenever the tracker changes:

1. Read all tabs with the Google Sheets tool `read_range`, **valueRenderOption = UNFORMATTED_VALUE**
   (raw numbers, so the comma-decimal locale doesn't matter; dates come back as serials, e.g. 46319 = 2026-10-24,
   times as day fractions; build_snapshot.py converts them):
   spreadsheetId `1GWj3ub5nyvV5MHeb_J8ih6W0SQqTxLaTXe7ToHvH_eo`, ranges
   `Transactions 1:500`, `Daily Summary 1:500`, `Candidates 1:500`, `Wallet 1:500`, `Suruhan Monitoring 1:500`.
   Save the JSON result (`{"ranges":[{sheet,content}]}`) as `/workspace/sheet_raw.json`.
2. Read `Transactions!M1:O500` with **valueRenderOption = FORMULA** (tx links live in `=HYPERLINK(...)`, which the
   CSV export drops). Save that range's `content` string as `/workspace/tx_formulas.csv`.
3. Update the `holdings` list in `build_snapshot.py` if NFTs were minted/sold (it asserts the token IDs match
   `/workspace/findings/mint-hunting/ledger.json` → `holdings`).
4. Run:
   ```
   cd /workspace/dashboard
   python3 build_snapshot.py /workspace/sheet_raw.json /workspace/tx_formulas.csv \
       /workspace/findings/mint-hunting/ledger.json > data.json
   ```
5. Test: `python3 -m http.server 8765` then open http://localhost:8765/ . To force fallback mode in headless Chrome:
   `google-chrome --headless=new --host-resolver-rules="MAP docs.google.com 127.0.0.1:9" --dump-dom http://localhost:8765/`
   → indicator should read "Data: snapshot <time> WITA".
6. Re-deploy the folder (index.html + data.json) to wherever it's hosted.

Safety: the builder drops Wallet-tab rows matching session/sign-in/password/private/seed/api key.
Never put API keys, private keys, wallets.csv, or session data in data.json — the page is public.
