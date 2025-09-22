import { NextRequest, NextResponse } from 'next/server';
import { getCategoryShares, isPartial } from '@/src/lib/budget';

export async function GET(req: NextRequest) {
  try {
    const year = (req.nextUrl.searchParams.get('year') ?? 'FY25') as any;
    const data = await getCategoryShares(year);
    
    return NextResponse.json({
      success: true,
      year,
      partial: isPartial(year),
      data,
      message: `Category shares for ${year} retrieved successfully`
    });
  } catch (error) {
    console.error('Error fetching category shares:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch category shares',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
