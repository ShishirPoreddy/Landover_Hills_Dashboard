import { NextRequest, NextResponse } from 'next/server';
import { getCategoryRanking, isPartial } from '@/src/lib/budget';

export async function GET(req: NextRequest) {
  try {
    const year = (req.nextUrl.searchParams.get('year') ?? 'FY25') as any;
    const limit = Number(req.nextUrl.searchParams.get('limit') ?? 10);
    
    const data = await getCategoryRanking(year, limit);
    
    return NextResponse.json({
      success: true,
      year,
      partial: isPartial(year),
      data,
      message: `Category rankings for ${year} retrieved successfully`
    });
  } catch (error) {
    console.error('Error fetching category rankings:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch category rankings',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
