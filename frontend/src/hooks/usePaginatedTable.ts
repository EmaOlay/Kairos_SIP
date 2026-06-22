import { useMemo } from 'react';

export interface UsePaginatedTableParams<T> {
  items: T[];
  filterFn: (item: T) => boolean;
  page: number;
  pageSize: number;
}

export interface UsePaginatedTableResult<T> {
  paginatedItems: T[];
  totalFiltered: number;
  totalPages: number;
  currentPage: number;
}

export function usePaginatedTable<T>({
  items,
  filterFn,
  page,
  pageSize,
}: UsePaginatedTableParams<T>): UsePaginatedTableResult<T> {
  return useMemo(() => {
    const filtered = items.filter(filterFn);
    const totalFiltered = filtered.length;
    const totalPages = Math.max(1, Math.ceil(totalFiltered / pageSize));
    const clampedPage = Math.max(1, Math.min(page, totalPages));
    const start = (clampedPage - 1) * pageSize;
    const paginatedItems = filtered.slice(start, start + pageSize);

    return { paginatedItems, totalFiltered, totalPages, currentPage: clampedPage };
  }, [items, filterFn, page, pageSize]);
}
