import { NextRequest, NextResponse } from 'next/server';
import { getLineItemTotal, usd, isPartial } from '@/src/lib/budget';

export async function GET(req: NextRequest) {
  try {
    const year = (req.nextUrl.searchParams.get('year') ?? 'FY24') as any;
    const category = req.nextUrl.searchParams.get('category') ?? 'ADMINISTRATION';
    const lineItem = req.nextUrl.searchParams.get('lineItem') ?? 'Payroll Taxes';
    
    const total = await getLineItemTotal(year, category, lineItem);
    
    return NextResponse.json({
      success: true,
      year,
      category,
      lineItem,
      total,
      formatted: usd(total),
      partial: isPartial(year),
      message: `Line item total for ${lineItem} in ${category} (${year}) retrieved successfully`
    });
  } catch (error) {
    console.error('Error fetching line item total:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch line item total',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
