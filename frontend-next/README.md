# Mercedes Scientific Search - Next.js Frontend

Clean **Next.js + TypeScript + Tailwind** implementation - no Shadcn complexity!

## Stack

- **Next.js 14** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS** - Utility-first styling (easy to customize!)
- **Lucide React** - Icons

## Running

```bash
# From project root
./start-nextjs.sh

# Or manually
cd frontend-next
npm run dev
```

**Dev server**: http://localhost:3000

## Structure

```
frontend-next/
├── app/
│   ├── page.tsx          # Main search page
│   ├── layout.tsx        # Root layout
│   └── globals.css       # Tailwind imports
├── components/
│   ├── Heading.tsx       # Title + branding
│   ├── Form.tsx          # Search bar
│   └── ProductListItem.tsx  # Product cards
└── lib/
    └── utils.ts          # Helper functions
```

## Easy Customization

All styling is plain Tailwind classes - no complex component libraries!

**Change button color:**
```tsx
// In Form.tsx
className="bg-blue-600 hover:bg-blue-700"  // Change from neutral-900
```

**Change spacing:**
```tsx
className="mb-6"   // margin-bottom: 1.5rem
className="px-4"   // padding-left/right: 1rem
className="gap-2"  // gap: 0.5rem
```

**Tailwind Size Reference:**
- `0.5` = 0.125rem (2px)
- `1` = 0.25rem (4px)
- `2` = 0.5rem (8px)
- `4` = 1rem (16px)
- `6` = 1.5rem (24px)
- `8` = 2rem (32px)

## Backend API

Connects to Flask backend at `http://localhost:5001/api/search`

Make sure to start the backend:
```bash
python src/app.py
```

## Benefits Over Old Frontend

✅ **TypeScript** - Catch errors before runtime
✅ **Next.js** - Better performance, SEO, routing
✅ **No Shadcn** - Simple, direct styling
✅ **Hot reload works perfectly** - No more refresh issues!
✅ **Cleaner code** - Plain HTML elements with Tailwind

## Migration from Old Frontend

The old React + Vite frontend is in `../frontend/`. You can:

1. **Test both**: Run old on :5173, new on :3000
2. **Switch permanently**: Delete `../frontend` when ready
3. **Compare**: Both work with same backend API
