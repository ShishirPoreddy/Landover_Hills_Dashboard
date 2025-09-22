import { NextResponse } from 'next/server';
import { getYearTotals } from '@/src/lib/budget';

export async function GET() {
  try {
    const data = await getYearTotals();
    return NextResponse.json({
      success: true,
      data,
      message: 'Year totals retrieved successfully'
    });
  } catch (error) {
    console.error('Error fetching year totals:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch year totals',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
