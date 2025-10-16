# Deploying Frontend to GitHub Pages

Alternative to Vercel - deploy your Next.js frontend as a static site on GitHub Pages (100% free).

## Prerequisites

- ✅ GitHub account
- ✅ Repository pushed to GitHub
- ✅ Backend deployed (Render/Railway/Fly.io)

---

## Limitations to Know

**GitHub Pages only supports static sites**, so:

❌ **Won't work:**
- Server-Side Rendering (SSR)
- API routes in Next.js
- Server components
- Dynamic routing with getServerSideProps

✅ **Will work:**
- Client-side rendering
- Static pages
- Calling external APIs (your backend on Render)
- All client-side Next.js features

**For your search app:** This works perfectly because you're just making API calls to your backend!

---

## Step 1: Configure Next.js for Static Export

### 1.1: Update next.config.mjs

Update `frontend-next/next.config.mjs`:

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',  // Enable static export
  images: {
    unoptimized: true,  // GitHub Pages doesn't support Next.js image optimization
  },
  // If deploying to repo (not custom domain), uncomment:
  // basePath: '/mercedes-nl-search',  // Replace with your repo name
  // assetPrefix: '/mercedes-nl-search/',
}

export default nextConfig
```

**Important:**
- If using `username.github.io` (custom domain or user page): Don't set `basePath`
- If using `username.github.io/repo-name`: Set `basePath` to `/repo-name`

### 1.2: Update package.json

Add export script to `frontend-next/package.json`:

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "export": "next build"  // Add this
  }
}
```

### 1.3: Create .nojekyll file

```bash
cd frontend-next
touch public/.nojekyll
```

This tells GitHub Pages not to process files with Jekyll.

---

## Step 2: Set Environment Variables

Create `frontend-next/.env.production`:

```bash
# Your backend API URL (deployed on Render)
NEXT_PUBLIC_API_URL=https://your-api.onrender.com
```

**Important:** Next.js bakes env vars into the build, so rebuild after changing this file.

---

## Step 3: Build Static Site Locally (Test)

```bash
cd frontend-next

# Install dependencies
npm install

# Build static site
npm run build

# This creates an 'out' folder with static HTML/CSS/JS
```

**Verify:** Check that `frontend-next/out` folder was created with HTML files.

---

## Step 4: Deploy to GitHub Pages

### Option A: Using GitHub Actions (Recommended - Auto-deploy)

Create `.github/workflows/deploy-frontend.yml`:

```yaml
name: Deploy Frontend to GitHub Pages

on:
  push:
    branches:
      - main  # Deploy when pushing to main branch
    paths:
      - 'frontend-next/**'  # Only deploy when frontend changes

  # Allow manual trigger
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend-next/package-lock.json

      - name: Install dependencies
        run: |
          cd frontend-next
          npm ci

      - name: Build Next.js site
        env:
          NEXT_PUBLIC_API_URL: ${{ secrets.NEXT_PUBLIC_API_URL }}
        run: |
          cd frontend-next
          npm run build

      - name: Setup Pages
        uses: actions/configure-pages@v4

      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: frontend-next/out

      - name: Deploy to GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```

**Then:**

1. **Add secret to GitHub:**
   - Go to your repo → Settings → Secrets and variables → Actions
   - Click "New repository secret"
   - Name: `NEXT_PUBLIC_API_URL`
   - Value: `https://your-api.onrender.com`
   - Click "Add secret"

2. **Enable GitHub Pages:**
   - Repo → Settings → Pages
   - Source: "GitHub Actions"
   - Click "Save"

3. **Push to GitHub:**
   ```bash
   git add .
   git commit -m "Add GitHub Pages deployment"
   git push
   ```

4. **Wait for deployment:**
   - Go to repo → Actions
   - Watch the workflow run
   - When done, your site is live!

**Your URL:** `https://USERNAME.github.io/REPO-NAME/`

---

### Option B: Manual Deploy (Quick but no auto-updates)

```bash
cd frontend-next

# Build
npm run build

# Install gh-pages package
npm install --save-dev gh-pages

# Add deploy script to package.json
npm pkg set scripts.deploy="gh-pages -d out"

# Deploy
npm run deploy
```

**Then:**
- Go to repo → Settings → Pages
- Source: "Deploy from a branch"
- Branch: `gh-pages` / `root`
- Click "Save"

**Your URL:** `https://USERNAME.github.io/REPO-NAME/`

---

## Step 5: Configure Custom Domain (Optional)

If you have a custom domain:

1. **Add CNAME file:**
   ```bash
   echo "search.yourdomain.com" > frontend-next/public/CNAME
   ```

2. **Update DNS:**
   - Add CNAME record: `search` → `USERNAME.github.io`

3. **In GitHub:**
   - Repo → Settings → Pages
   - Custom domain: `search.yourdomain.com`
   - Click "Save"
   - Enable "Enforce HTTPS"

---

## Step 6: Test Your Deployment

Visit your GitHub Pages URL:
- **With repo name:** `https://USERNAME.github.io/mercedes-nl-search/`
- **Custom domain:** `https://search.yourdomain.com`

**Test search:**
1. Type a query
2. Check browser console (F12)
3. Verify API calls go to your Render backend

---

## Troubleshooting

### Issue: 404 errors on page refresh

**Cause:** GitHub Pages doesn't support client-side routing by default.

**Fix:** Add `404.html` that redirects to `index.html`:

Create `frontend-next/public/404.html`:
```html
<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <title>Redirecting...</title>
    <script>
      sessionStorage.redirect = location.href;
    </script>
    <meta http-equiv="refresh" content="0;URL='/'">
  </head>
</html>
```

### Issue: Images not loading

**Cause:** Next.js Image component requires server.

**Fix:** Use regular `<img>` tags or unoptimized images (already in config).

### Issue: API calls failing (CORS)

**Cause:** GitHub Pages URL not in backend CORS.

**Fix:** Update `src/app.py`:
```python
CORS(app, origins=[
    "http://localhost:3000",
    "https://USERNAME.github.io",  # Add GitHub Pages
    "https://*.vercel.app"
])
```

Then redeploy backend.

### Issue: Blank page after deployment

**Check:**
1. Browser console for errors (F12)
2. Verify `basePath` is correct in `next.config.mjs`
3. Check `NEXT_PUBLIC_API_URL` is set
4. Rebuild: `npm run build`

---

## Comparison: GitHub Pages vs Vercel

### GitHub Pages ✅

**Pros:**
- ✅ 100% free forever
- ✅ 100GB bandwidth/month
- ✅ Custom domains supported
- ✅ No account needed (just GitHub)
- ✅ Good for static sites

**Cons:**
- ❌ More setup (need to configure static export)
- ❌ No automatic deployments (need GitHub Actions)
- ❌ No server-side features
- ❌ No preview deployments
- ❌ Slower builds

### Vercel ✅ (Recommended)

**Pros:**
- ✅ Built for Next.js (by Next.js creators)
- ✅ Zero config - just works
- ✅ Auto-deploy on git push
- ✅ Preview deployments for PRs
- ✅ Full Next.js features (SSR, API routes, etc.)
- ✅ Edge network (faster globally)
- ✅ Free tier: 100GB bandwidth

**Cons:**
- ⚠️ Need Vercel account (but free)

---

## Decision Matrix

**Use GitHub Pages if:**
- ✅ You want 100% GitHub-only workflow
- ✅ You don't need Next.js server features
- ✅ You're comfortable with static export setup
- ✅ You prefer not to create another account

**Use Vercel if:**
- ✅ You want the easiest setup (5 minutes)
- ✅ You might use Next.js server features later
- ✅ You want automatic preview deployments
- ✅ You value speed and simplicity

---

## My Recommendation

**For your specific app:** Both work fine!

**Easiest:** Vercel (5 minutes, zero config)
**Most GitHub-native:** GitHub Pages (15 minutes, some config)

**If you want to learn:** Try GitHub Pages!
**If you want to ship fast:** Use Vercel!

---

## Complete Deployment Checklist (GitHub Pages)

- [ ] Update `next.config.mjs` with `output: 'export'`
- [ ] Create `.nojekyll` file in `public/`
- [ ] Create `.env.production` with API URL
- [ ] Test build locally: `npm run build`
- [ ] Create GitHub Actions workflow (or use manual deploy)
- [ ] Add `NEXT_PUBLIC_API_URL` secret in GitHub
- [ ] Enable GitHub Pages in repo settings
- [ ] Push to GitHub
- [ ] Update backend CORS with GitHub Pages URL
- [ ] Test live site

---

## Quick Start Commands

```bash
# 1. Configure Next.js
cd frontend-next
# (Edit next.config.mjs as shown above)

# 2. Create .nojekyll
touch public/.nojekyll

# 3. Create .env.production
echo "NEXT_PUBLIC_API_URL=https://your-api.onrender.com" > .env.production

# 4. Test build
npm run build

# 5. Push to GitHub
git add .
git commit -m "Configure for GitHub Pages"
git push

# 6. Set up GitHub Actions workflow (copy YAML above)

# Done! Site will deploy automatically
```

---

**Your choice!** Both GitHub Pages and Vercel are free and work great for this app.

**Questions?** See `DEPLOYMENT_QUICKSTART.md` for Vercel option, or follow this guide for GitHub Pages.
