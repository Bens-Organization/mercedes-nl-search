# Customer JourneyAI Branding

## Color Palette

```css
/* Primary Colors */
--journey-teal: #00CE9D      /* Primary brand color - CTAs, links, accents */
--journey-navy: #003C5B      /* Dark navy blue - buttons, headings */
--journey-navy-dark: #002840 /* Darker navy - hover states */

/* Neutral Colors */
--background: #F9FAFB        /* Light gray background */
--card-bg: #FFFFFF           /* White card backgrounds */
--border: #E5E7EB            /* Light gray borders */
```

## Usage in Tailwind

The colors are configured in `tailwind.config.ts`:

```typescript
colors: {
  'journey': {
    teal: '#00CE9D',
    navy: '#003C5B',
    'navy-dark': '#002840',
  }
}
```

### Examples

```tsx
// Buttons
className="bg-journey-navy hover:bg-journey-navy-dark"

// Links
className="text-journey-teal hover:underline"

// Input focus
className="focus:border-journey-teal"

// Badges
className="bg-journey-teal text-white"
```

## Logo

**File**: `public/journey-logo.png`
- Teal circular logo with submarine icon
- Used in the "Powered by" section
- Size: 24x24px

## Typography

- **Headings**: Bold, gray-800 color
- **Body**: Regular weight, gray-700
- **Links**: Teal color, underline on hover

## Components Styled

1. **Search Button** - Navy background with white search icon
2. **Input Border** - Teal border on focus
3. **Load More Button** - Teal background, white text
4. **Product Prices** - Teal color
5. **In Stock Badges** - Teal background (10% opacity), teal text
6. **Example Query Cards** - Teal border on hover
7. **Product Links** - Teal on hover

## Design System

Following the Customer JourneyAI website design:
- Clean, modern B2B aesthetic
- Generous white space
- Rounded corners (rounded-lg)
- Subtle shadows
- Professional color palette
