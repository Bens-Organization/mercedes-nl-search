'use client';
import { useState, FormEvent, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import Heading from '@/components/Heading';
import { PlaceholdersAndVanishInput } from '@/components/ui/placeholders-and-vanish-input';
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

// Wrapper component to handle Suspense boundary for useSearchParams
export default function Home() {
  return (
    <Suspense fallback={
      <main className="flex flex-col items-center px-8 py-10 max-w-screen-lg m-auto font-medium bg-white rounded-lg shadow-sm my-8">
        <div className="flex flex-col items-center my-10">
          <Loader2 className="h-8 w-8 animate-spin" />
          <p className="mt-4">Loading...</p>
        </div>
      </main>
    }>
      <HomeContent />
    </Suspense>
  );
}

function HomeContent() {
  const searchParams = useSearchParams();
  const router = useRouter();

  // Check if we should show debug info
  // Only show if explicitly set to 'development' OR running on localhost
  const environment = process.env.NEXT_PUBLIC_ENVIRONMENT;
  const isLocalhost = typeof window !== 'undefined' &&
    (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');
  const shouldShowDebugInfo = environment === 'development' || isLocalhost;

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [stats, setStats] = useState<SearchStats | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [hoveredExampleIndex, setHoveredExampleIndex] = useState<number | undefined>(undefined);
  const [initialLoadDone, setInitialLoadDone] = useState(false);

  const exampleQueries = [
    'Gloves in stock under $50',
    'Pipettes with at least 10μL capacity, under $500',
    'Sterile surgical instruments, stainless steel',
    'Safety goggles with anti-fog coating',
    'Show me the most popular lab equipment',
    'Laboratory gloves, size medium, in stock',
    'Test tubes, glass, in stock',
    'Centrifuge tubes, 50ml capacity',
  ];

  const handleSearch = async (searchQuery: string, pageNum = 1, append = false, updateUrl = true) => {
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

    // Update URL with query parameter (without page reload)
    if (updateUrl && !append) {
      const params = new URLSearchParams();
      params.set('query', searchQuery);
      router.push(`?${params.toString()}`, { scroll: false });
    }

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001';

      let response;

      try {
        response = await fetch(`${apiUrl}/api/search`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            query: searchQuery,
            max_results: 20 * pageNum,
            debug: shouldShowDebugInfo, // Enable debug in development environment
          }),
        });
      } catch (fetchError) {
        // Network error - couldn't reach the server at all
        throw new Error('Cannot reach Journey AI. Please check your connection.');
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));

        if (response.status === 503) {
          throw new Error('Journey AI is currently unavailable. Please try again later.');
        } else if (response.status === 500) {
          throw new Error(errorData.message || 'Search service error. Please try again.');
        } else if (response.status >= 400 && response.status < 500) {
          throw new Error(errorData.error || 'Invalid search request');
        } else {
          throw new Error('Search failed. Please try again.');
        }
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
      setError(err instanceof Error ? err.message : 'An unexpected error occurred');
      if (!append) {
        setResults([]);
        setStats(null);
      }
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  // Read query from URL on initial page load
  useEffect(() => {
    if (initialLoadDone) return;

    const queryFromUrl = searchParams.get('query');
    if (queryFromUrl) {
      setQuery(queryFromUrl);
      handleSearch(queryFromUrl, 1, false, false); // Don't update URL again
    }
    setInitialLoadDone(true);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams, initialLoadDone]);

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
    setQuery(example);
    handleSearch(example);
  };

  const handleBackToHome = () => {
    setHasSearched(false);
    setQuery('');
    setResults([]);
    setStats(null);
    // Clear query from URL
    router.push('/', { scroll: false });
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
          <PlaceholdersAndVanishInput
            placeholders={exampleQueries}
            onChange={(e) => setQuery(e.target.value)}
            onSubmit={handleSubmit}
            currentPlaceholderIndex={hoveredExampleIndex}
            value={query}
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
                onMouseEnter={() => setHoveredExampleIndex(index)}
                onMouseLeave={() => setHoveredExampleIndex(undefined)}
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
        <PlaceholdersAndVanishInput
          placeholders={exampleQueries}
          onChange={(e) => setQuery(e.target.value)}
          onSubmit={handleSubmit}
          currentPlaceholderIndex={hoveredExampleIndex}
          value={query}
        />
      </div>

      {/* Parsed Query Display - only show in development */}
      {shouldShowDebugInfo && stats && !loading && (
        <pre className="text-xs mb-4 block max-w-full overflow-auto w-full">
          {(() => {
            // Display middleware-extracted query and filters
            // Support both legacy (top-level) and new (nested in typesense_query) API response formats
            const response = stats as any;
            const tq = stats.typesenseQuery || {};
            const parts = [];

            // Check both top-level (legacy API) and nested locations (new API)
            const extractedQuery = response.extracted_query ||  // Legacy: top-level
                                   tq.extracted_query ||        // New: nested in typesense_query
                                   tq.parsed_nl_query?.generated_params?.q ||
                                   tq.nl_extracted_query ||
                                   tq.parsed?.q ||
                                   query;

            const extractedFilters = response.filters_applied ||  // Legacy: top-level
                                     tq.filters_applied ||        // New: nested in typesense_query
                                     tq.parsed_nl_query?.generated_params?.filter_by ||
                                     tq.nl_extracted_filters ||
                                     tq.parsed?.filter_by;

            const extractedSort = tq.parsed_nl_query?.augmented_params?.sort_by ||
                                  tq.nl_extracted_sort ||
                                  tq.parsed?.sort_by;

            if (extractedQuery && extractedQuery !== query) {
              parts.push(`"q":"${extractedQuery}"`);
            }

            if (extractedFilters && extractedFilters !== 'none' && extractedFilters !== '') {
              // Remove leading < if present (legacy format issue)
              let cleanedFilters = extractedFilters.replace(/^</, '');

              // Wrap category values in backticks for better readability
              const formattedFilters = cleanedFilters.replace(
                /categories:=([^&\s]+)/g,
                'categories:=`$1`'
              );
              parts.push(`"filter_by":"${formattedFilters}"`);
            }

            if (extractedSort && extractedSort !== 'default') parts.push(`"sort_by":"${extractedSort}"`);

            if (parts.length === 0) {
              return `{"q":"${query}"}`;
            }

            return `{${parts.join(', ')}}`;
          })()}
        </pre>
      )}

      {/* Results Count */}
      {stats && !loading && !error && (
        <div className="self-start mb-2 w-full text-sm text-gray-600">
          Showing {stats.total.toLocaleString()} {stats.total === 1 ? 'product' : 'products'}{shouldShowDebugInfo && ` (${stats.queryTime.toFixed(0)}ms)`}
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
                  `Load More (${stats ? (stats.total - results.length).toLocaleString() : '0'} remaining)`
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
