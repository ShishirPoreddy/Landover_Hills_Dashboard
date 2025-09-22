import type { Intent, Year } from './types';

const USD = (n: number | null | undefined) =>
  typeof n === 'number' && !isNaN(n) ? `$${n.toLocaleString('en-US')}` : '$0';

const PARTIAL_NOTE = 'Note: FY26 data is partial.';

export async function handleIntent(intent: Intent): Promise<string> {
  switch (intent.action) {
    case 'year_total': {
      const res = await fetch('http://127.0.0.1:8000/api/budget/year-totals');
      const rows: { fiscal_year: Year; total: number }[] = await res.json();
      const row = rows.find(r => r.fiscal_year === intent.year);
      const msg = `Total ${intent.year} budget: ${USD(row?.total)}. Source: v_year_totals(${intent.year}).`;
      return intent.year === 'FY26' ? `${msg} ${PARTIAL_NOTE}` : msg;
    }

    case 'yoy_difference': {
      const res = await fetch('http://127.0.0.1:8000/api/budget/yoy');
      const rows: { fiscal_year: Year; total: number; yoy_change: number|null }[] = await res.json();
      const toRow = rows.find(r => r.fiscal_year === intent.year_to);
      const fromRow = rows.find(r => r.fiscal_year === intent.year_from);
      if (!toRow || !fromRow) return 'I could not find the requested years.';
      const delta = toRow.total - fromRow.total;
      const msg = `Change from ${intent.year_from} to ${intent.year_to}: ${USD(delta)} (${USD(fromRow.total)} → ${USD(toRow.total)}). Source: v_year_yoy.`;
      return intent.year_to === 'FY26' || intent.year_from === 'FY26' ? `${msg} ${PARTIAL_NOTE}` : msg;
    }

    case 'yoy_all': {
      const res = await fetch('http://127.0.0.1:8000/api/budget/yoy');
      const rows: { fiscal_year: Year; total: number; yoy_change: number|null }[] = await res.json();
      const lines = rows.map(r => {
        if (r.yoy_change == null) return `${r.fiscal_year}: base ${USD(r.total)}`;
        const sign = r.yoy_change >= 0 ? '+' : '−';
        return `${r.fiscal_year}: ${sign}${USD(Math.abs(r.yoy_change))} (total ${USD(r.total)})`;
      });
      const msg = `Year-over-year changes:\n- ${lines.join('\n- ')}\nSource: v_year_yoy.`;
      return rows.some(r => r.fiscal_year === 'FY26') ? `${msg}\n${PARTIAL_NOTE}` : msg;
    }

    case 'category_rank': {
      const limit = intent.top_n ?? 10;
      const res = await fetch(`http://127.0.0.1:8000/api/budget/category?year=${encodeURIComponent(intent.year)}&limit=${limit}`);
      const json = await res.json();
      const rows: { category: string; total: number }[] = json.data;
      if (!rows?.length) return `No categories found for ${intent.year}.`;
      const list = rows.map((r, i) => `${i+1}. ${r.category}: ${USD(r.total)}`).join('\n');
      const msg = `Top ${limit} categories in ${intent.year}:\n${list}\nSource: v_category_totals(${intent.year}).`;
      return json.partial ? `${msg}\n${PARTIAL_NOTE}` : msg;
    }

    case 'category_share': {
      const res = await fetch(`http://127.0.0.1:8000/api/budget/shares?year=${encodeURIComponent(intent.year)}`);
      const json = await res.json();
      const rows: { category: string; total: number; pct_of_year: number }[] = json.data;
      const row = rows.find(r => r.category.toUpperCase() === intent.category.toUpperCase());
      if (!row) return `No data for ${intent.category} in ${intent.year}.`;
      const msg = `${intent.category} in ${intent.year}: ${USD(row.total)} (${row.pct_of_year}% of total). Source: v_category_shares(${intent.year}).`;
      return intent.year === 'FY26' ? `${msg} ${PARTIAL_NOTE}` : msg;
    }

    case 'line_item_total': {
      const url = `http://127.0.0.1:8000/api/budget/line-item?year=${encodeURIComponent(intent.year)}&category=${encodeURIComponent(intent.category)}&lineItem=${encodeURIComponent(intent.line_item)}`;
      const res = await fetch(url);
      const json = await res.json();
      const msg = `${intent.year} ${intent.category} → ${intent.line_item}: ${USD(json.total)}. Source: v_line_items.`;
      return json.partial ? `${msg} ${PARTIAL_NOTE}` : msg;
    }

    case 'help':
      return intent.question;

    default:
      return 'Sorry, I could not interpret that request.';
  }
}
