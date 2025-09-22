import { NextResponse } from 'next/server';
import { getYoY } from '@/src/lib/budget';

export async function GET() {
  try {
    const data = await getYoY();
    return NextResponse.json({
      success: true,
      data,
      message: 'Year-over-year data retrieved successfully'
    });
  } catch (error) {
    console.error('Error fetching YoY data:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch year-over-year data',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
