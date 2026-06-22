import React from 'react';

export function makeFilterHandler<T extends Record<string, any> & { page: number }>(
  setFilters: React.Dispatch<React.SetStateAction<T>>
) {
  return (key: keyof T, value: any) => {
    setFilters(prev => ({
      ...prev,
      [key]: value,
      page: key === 'page' ? value : 1,
    } as T));
  };
}
