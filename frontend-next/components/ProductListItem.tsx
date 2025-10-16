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

interface ProductListItemProps {
  product: Product;
}

export default function ProductListItem({ product }: ProductListItemProps) {
  const productUrl = `https://www.mercedesscientific.com/${product.url_key}`;

  return (
    <li className="w-full py-4 px-4 border rounded-lg hover:bg-neutral-50 transition">
      <a href={productUrl} target="_blank" rel="noopener noreferrer" className="block">
        <div className="flex gap-4">
          {product.image_url && (
            <div className="flex-shrink-0">
              <img
                src={product.image_url}
                alt={product.name}
                className="w-24 h-24 object-contain"
              />
            </div>
          )}
          <div className="flex-1 min-w-0">
            <h3 className="text-lg font-semibold mb-1 hover:text-journey-teal transition">
              {product.name}
            </h3>
            <p className="text-sm text-gray-600 mb-2">SKU: {product.sku}</p>

            {product.short_description && (
              <p className="text-sm text-gray-700 mb-2 line-clamp-2">
                {product.short_description.replace(/<[^>]*>/g, '')}
              </p>
            )}

            <div className="flex items-center gap-4 mt-2">
              {product.price !== null && product.price !== undefined && (
                <span className="text-lg font-bold text-journey-teal">
                  ${product.price.toFixed(2)}
                </span>
              )}
              <span className={`text-sm px-2 py-1 rounded-full font-medium ${
                product.stock_status === 'IN_STOCK'
                  ? 'bg-journey-teal bg-opacity-10 text-journey-teal'
                  : 'bg-red-100 text-red-800'
              }`}>
                {product.stock_status === 'IN_STOCK' ? 'In Stock' : 'Out of Stock'}
              </span>
            </div>

            {product.categories && product.categories.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-2">
                {product.categories.slice(0, 3).map((category, idx) => (
                  <span key={idx} className="text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded">
                    {category}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </a>
    </li>
  );
}
