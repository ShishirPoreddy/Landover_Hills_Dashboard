import { describe, it, expect } from 'vitest';
import { 
  getYearTotals, 
  getYoY, 
  getLineItemTotal, 
  getCategoryRanking,
  getCategoryShares 
} from '@/src/lib/budget';

describe('Budget Facts', () => {
  it('year totals match expected CSV sums', async () => {
    const rows = await getYearTotals();
    const map = Object.fromEntries(rows.map(r => [r.fiscal_year, r.total]));
    
    // These values should match your actual CSV data
    expect(map.FY24).toBe(5391635);
    expect(map.FY25).toBe(6894068);
    expect(map.FY26).toBe(2721944); // partial
  });

  it('YoY deltas are correct', async () => {
    const yoy = await getYoY();
    const fy25 = yoy.find(r => r.fiscal_year === 'FY25')!;
    const fy26 = yoy.find(r => r.fiscal_year === 'FY26')!;
    
    expect(fy25.yoy_change).toBe(1502433);
    expect(fy26.yoy_change).toBe(-4172124);
  });

  it('FY24 Admin -> Payroll Taxes total is correct', async () => {
    const n = await getLineItemTotal('FY24', 'ADMINISTRATION', 'Payroll Taxes');
    expect(n).toBe(20389);
  });

  it('FY25 category rankings are correct', async () => {
    const rankings = await getCategoryRanking('FY25', 5);
    
    // Should be ordered by total descending
    expect(rankings[0].category).toBe('TAXES');
    expect(rankings[0].total).toBe(1481200);
    
    expect(rankings[1].category).toBe('POLICE DEPARTMENT');
    expect(rankings[1].total).toBe(1249212);
  });

  it('FY25 category shares add up to 100%', async () => {
    const shares = await getCategoryShares('FY25');
    const totalPercentage = shares.reduce((sum, item) => sum + item.pct_of_year, 0);
    
    // Should be approximately 100% (allowing for rounding)
    expect(totalPercentage).toBeCloseTo(100, 0);
  });

  it('FY24 taxes percentage is correct', async () => {
    const shares = await getCategoryShares('FY24');
    const taxes = shares.find(s => s.category === 'TAXES');
    
    expect(taxes).toBeDefined();
    expect(taxes!.pct_of_year).toBeCloseTo(29.3, 1); // ~29.3% of FY24 budget
  });

  it('FY25 taxes percentage is correct', async () => {
    const shares = await getCategoryShares('FY25');
    const taxes = shares.find(s => s.category === 'TAXES');
    
    expect(taxes).toBeDefined();
    expect(taxes!.pct_of_year).toBeCloseTo(21.5, 1); // ~21.5% of FY25 budget
  });
});

describe('Data Validation', () => {
  it('all years have data', async () => {
    const totals = await getYearTotals();
    expect(totals).toHaveLength(3); // FY24, FY25, FY26
    expect(totals.every(t => t.total > 0)).toBe(true);
  });

  it('FY26 is marked as partial', async () => {
    const totals = await getYearTotals();
    const fy26 = totals.find(t => t.fiscal_year === 'FY26');
    expect(fy26).toBeDefined();
    expect(fy26!.total).toBeLessThan(4000000); // FY26 should be smaller (partial)
  });

  it('category totals are consistent across views', async () => {
    const rankings = await getCategoryRanking('FY25', 10);
    const shares = await getCategoryShares('FY25');
    
    // Both should have the same categories in the same order
    expect(rankings.map(r => r.category)).toEqual(shares.map(s => s.category));
    
    // Totals should match
    rankings.forEach(ranking => {
      const share = shares.find(s => s.category === ranking.category);
      expect(share!.total).toBe(ranking.total);
    });
  });
});
