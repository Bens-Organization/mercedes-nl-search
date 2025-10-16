'use client';
import { Search } from 'lucide-react';
import { FormEvent } from 'react';

interface FormProps {
  query: string;
  setQuery: (query: string) => void;
  onSubmit: (e: FormEvent) => void;
  placeholder?: string;
  autoFocus?: boolean;
}

export default function Form({
  query,
  setQuery,
  onSubmit,
  placeholder,
  autoFocus = false
}: FormProps) {
  return (
    <form onSubmit={onSubmit} className="w-full flex gap-2.5 mb-4">
      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder={placeholder || "Search for products..."}
        className="flex-1 px-3 py-2 border-2 border-gray-300 rounded-lg placeholder:font-light text-sm focus:border-journey-teal focus:outline-none transition"
        autoFocus={autoFocus}
      />
      <button
        type="submit"
        className="bg-journey-navy aspect-square w-10 grid place-content-center rounded-lg hover:bg-journey-navy-dark transition"
      >
        <Search className="w-5 h-5 text-white" />
      </button>
    </form>
  );
}
