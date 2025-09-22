export type Year = 'FY24'|'FY25'|'FY26';

export type Intent =
  | { action: 'year_total'; year: Year; partial_data?: boolean }
  | { action: 'yoy_difference'; year_from: Year; year_to: Year }
  | { action: 'yoy_all' }
  | { action: 'category_rank'; year: Year; top_n?: number }
  | { action: 'category_share'; year: Year; category: string }
  | { action: 'line_item_total'; year: Year; category: string; line_item: string }
  | { action: 'help'; question: string };
