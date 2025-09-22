import { NextRequest, NextResponse } from 'next/server';
import { getCategoryYoY } from '@/src/lib/budget';

export async function GET(req: NextRequest) {
  try {
    const year1 = (req.nextUrl.searchParams.get('year1') ?? 'FY24') as any;
    const year2 = (req.nextUrl.searchParams.get('year2') ?? 'FY25') as any;
    const category = req.nextUrl.searchParams.get('category') ?? '';
    
    if (!category) {
      return NextResponse.json(
        { 
          success: false, 
          error: 'Category parameter is required'
        },
        { status: 400 }
      );
    }
    
    const data = await getCategoryYoY(year1, year2, category);
    
    return NextResponse.json({
      success: true,
      year1,
      year2,
      category,
      data,
      message: `Category YoY change for ${category} from ${year1} to ${year2} retrieved successfully`
    });
  } catch (error) {
    console.error('Error fetching category YoY:', error);
    return NextResponse.json(
      { 
        success: false, 
        error: 'Failed to fetch category year-over-year data',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
