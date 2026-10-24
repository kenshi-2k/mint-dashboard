// Vercel serverless function: returns dashboard data (same shape as data.json) from Neon.
// DATABASE_URL comes from an encrypted Vercel env var; it is never in the repo.
const { neon } = require("@neondatabase/serverless");

const SHEET_ID = "1GWj3ub5nyvV5MHeb_J8ih6W0SQqTxLaTXe7ToHvH_eo";
const WALLET = "0xC1408fc129512e0d6aaa93022F4B49B68647D94e";
const wita = (d) => d ? new Date(new Date(d).getTime() + 8 * 3600e3).toISOString().slice(0, 16).replace("T", " ") + " WITA" : null;

module.exports = async (req, res) => {
  res.setHeader("Cache-Control", "no-store");
  if (!process.env.DATABASE_URL) { res.statusCode = 503; return res.end(JSON.stringify({ error: "database not configured" })); }
  try {
    const sql = neon(process.env.DATABASE_URL);
    const [tx, hold, lst, cand, sur, bal, meta] = await Promise.all([
      sql`SELECT raw FROM transactions ORDER BY row_no`,
      sql`SELECT * FROM nft_holdings WHERE status <> 'Gone' ORDER BY acquired_at NULLS FIRST, token_id`,
      sql`SELECT * FROM listings WHERE status = 'Active'`,
      sql`SELECT raw FROM leads WHERE source_tab = 'Candidates' ORDER BY row_no`,
      sql`SELECT raw FROM leads WHERE source_tab = 'Suruhan Monitoring' ORDER BY row_no`,
      sql`SELECT * FROM wallet_balance ORDER BY recorded_at, seq`,
      sql`SELECT key, value FROM sync_meta`,
    ]);
    const M = Object.fromEntries(meta.map((r) => [r.key, r.value]));
    const H = M.headers || {};
    const L = Object.fromEntries(lst.map((l) => [l.contract.toLowerCase() + ":" + l.token_id, l]));
    const last = bal[bal.length - 1];
    const out = {
      generated_wita: M.synced_wita || null,
      sheet_id: SHEET_ID,
      source: "neon",
      wallet: {
        address: WALLET, chain: "BSC",
        last_balance_bnb: last ? Number(last.balance_bnb) : null,
        last_balance_wita: last ? wita(last.recorded_at) : null,
        bnb_usd_ref: M.bnb_usd_ref || 740,
      },
      budget: M.budget || { cap_usd: 10 },
      holdings: hold.map((h) => {
        const l = L[h.contract.toLowerCase() + ":" + h.token_id];
        return { collection: h.collection, token: h.token_id, contract: h.contract, status: h.status, note: h.note,
          ...(l ? { price_bnb: Number(l.price_bnb), market: l.market, listing: l.url, expires_wita: wita(l.expires_at) } : {}) };
      }),
      balance_history: bal.map((b) => ({ at_wita: wita(b.recorded_at), kind: b.kind, project: b.project, direction: b.direction,
        delta_bnb: Number(b.delta_bnb), balance_bnb: Number(b.balance_bnb), tx: "https://bscscan.com/tx/" + b.tx_hash })),
      tabs: {
        "Transactions": { headers: H["Transactions"] || [], rows: tx.map((r) => r.raw) },
        "Daily Summary": { headers: H["Daily Summary"] || [], rows: M.daily_summary || [] },
        "Candidates": { headers: H["Candidates"] || [], rows: cand.map((r) => r.raw) },
        "Wallet": { headers: H["Wallet"] || [], rows: M.wallet_tab || [] },
        "Suruhan Monitoring": { headers: H["Suruhan Monitoring"] || [], rows: sur.map((r) => r.raw) },
      },
    };
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(JSON.stringify(out));
  } catch (e) {
    console.error("api/data failed:", e && e.message ? e.message.replace(/postgres(ql)?:\/\/\S+/g, "***") : e);
    res.statusCode = 500; res.end(JSON.stringify({ error: "query failed" }));
  }
};
