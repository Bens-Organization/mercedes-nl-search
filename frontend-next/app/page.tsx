'use client';
import { useState, FormEvent } from 'react';
import { Loader2 } from 'lucide-react';
import Heading from '@/components/Heading';
import Form from '@/components/Form';
import ProductListItem from '@/components/ProductListItem';

interface Product {
  product_id: number;
  uid: string;
  name: string;
  sku: string;
  url_key: string;
  stock_status: string;
  type_id: string;
  description?: string;
  short_description?: string;
  price?: number;
  currency: string;
  image_url?: string;
  categories: string[];
  category_ids: number[];
}

interface SearchStats {
  total: number;
  queryTime: number;
  typesenseQuery: any;
}

export default function Home() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<SearchStats | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  const exampleQueries = [
    'Nitrile gloves, powder-free, in stock, under $30',
    'Pipettes with at least 10μL capacity, under $500',
    'Sterile surgical instruments, stainless steel',
    'Safety goggles with anti-fog coating',
    'Show me the most popular lab equipment',
    'Give me the latest microscopes',
    'Digital thermometers, in stock, under $100',
    'Centrifuge tubes, 50ml capacity',
  ];

  const handleSearch = async (searchQuery: string, pageNum = 1, append = false) => {
    if (!searchQuery.trim()) {
      return;
    }

    if (append) {
      setLoadingMore(true);
    } else {
      setLoading(true);
      setPage(1);
    }

    setError(null);
    setHasSearched(true);
    setQuery(searchQuery);

    try {
      const response = await fetch('http://localhost:5001/api/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchQuery,
          max_results: 20 * pageNum,
        }),
      });

      if (!response.ok) {
        throw new Error('Search failed');
      }

      const data = await response.json();
      const newResults = data.results || [];

      setResults(newResults);
      setStats({
        total: data.total,
        queryTime: data.query_time_ms,
        typesenseQuery: data.typesense_query,
      });

      setHasMore(newResults.length < data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
      if (!append) {
        setResults([]);
        setStats(null);
      }
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    handleSearch(query, nextPage, true);
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!query.trim()) {
      handleBackToHome();
      return;
    }
    handleSearch(query);
  };

  const handleExampleClick = (example: string) => {
    handleSearch(example);
  };

  const handleBackToHome = () => {
    setHasSearched(false);
    setQuery('');
    setResults([]);
    setStats(null);
    setError(null);
    setPage(1);
    setHasMore(false);
  };

  // Landing page
  if (!hasSearched) {
    return (
      <main className="flex flex-col items-center px-8 py-10 max-w-screen-lg m-auto font-medium bg-white rounded-lg shadow-sm my-8">
        <Heading onClick={handleBackToHome} />

        {/* Search Section */}
        <div className="w-full mb-8">
          <Form
            query={query}
            setQuery={setQuery}
            onSubmit={handleSubmit}
            placeholder="Type in the product specification, e.g. nitrile gloves, powder-free, under $50..."
            autoFocus
          />
        </div>

        {/* Example Queries */}
        <div className="w-full">
          <h2 className="w-full text-base font-medium mb-2">
            Here are some example queries to try:
          </h2>
          <ul className="w-full flex flex-col gap-2 text-sm font-light">
            {exampleQueries.map((example, index) => (
              <li
                key={index}
                onClick={() => handleExampleClick(example)}
                className="w-full py-2.5 px-3 border border-gray-200 rounded-lg cursor-pointer hover:border-journey-teal hover:bg-gray-50 transition"
              >
                {example}
              </li>
            ))}
          </ul>
        </div>
      </main>
    );
  }

  // Results page
  return (
    <main className="flex flex-col items-center px-8 py-10 max-w-screen-lg m-auto font-medium bg-white rounded-lg shadow-sm my-8">
      <Heading onClick={handleBackToHome} />

      {/* Search Bar */}
      <div className="w-full mb-4">
        <Form
          query={query}
          setQuery={setQuery}
          onSubmit={handleSubmit}
          placeholder="Type in the product specification, e.g. nitrile gloves, powder-free, under $50..."
        />
      </div>

      {/* Parsed Query Display */}
      {stats && !loading && stats.typesenseQuery && (
        <pre className="text-xs mb-4 block max-w-full overflow-auto w-full">
          {(() => {
            const parsed = stats.typesenseQuery.parsed || {};
            const parts = [];

            if (parsed.q) parts.push(`"q":"${parsed.q}"`);
            if (parsed.filter_by) parts.push(`"filter_by":"${parsed.filter_by}"`);
            if (parsed.sort_by) parts.push(`"sort_by":"${parsed.sort_by}"`);

            if (parts.length === 0) {
              return `{"q":"${query}"}`;
            }

            return `{${parts.join(', ')}}`;
          })()}
        </pre>
      )}

      {/* Results Count */}
      {stats && !loading && !error && (
        <div className="self-start mb-2 w-full">
          Found {stats.total.toLocaleString()} result{stats.total !== 1 ? 's' : ''} in {stats.queryTime.toFixed(0)}ms.
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex flex-col items-center my-10">
          <Loader2 className="h-8 w-8 animate-spin" />
          <p className="mt-4">Searching...</p>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="text-center py-12">
          <p className="text-red-600 font-semibold mb-2">{error}</p>
          <p className="text-xs text-gray-600">
            Make sure the API server is running on http://localhost:5001
          </p>
        </div>
      )}

      {/* Results List */}
      {!loading && !error && results.length > 0 && (
        <>
          <ul className="w-full flex flex-col gap-4 mb-8">
            {results.map((product) => (
              <ProductListItem key={product.product_id} product={product} />
            ))}
          </ul>

          {/* Load More / End Message */}
          <div className="text-center py-4 w-full">
            {hasMore ? (
              <button
                onClick={handleLoadMore}
                disabled={loadingMore}
                className="px-6 py-3 bg-journey-teal text-white font-semibold rounded-lg hover:bg-opacity-90 transition disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loadingMore ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin mr-2 inline" />
                    Loading...
                  </>
                ) : (
                  `Load More (${(stats.total - results.length).toLocaleString()} remaining)`
                )}
              </button>
            ) : (
              <p className="text-sm text-gray-600">No more items found.</p>
            )}
          </div>
        </>
      )}

      {/* No Results */}
      {!loading && !error && results.length === 0 && stats && (
        <div className="mt-20 text-gray-600">
          Oops! Couldn&apos;t find what you are looking for.
        </div>
      )}
    </main>
  );
}
