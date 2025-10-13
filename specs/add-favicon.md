# Chore: Add Favicon to Frontend

## Chore Description
Add a favicon (favorite icon) to the ScriptGrabber frontend application. The favicon is the small icon that appears in browser tabs, bookmarks, and browser history, providing visual identification for the application. This will enhance the professional appearance and user experience of the web interface by making it easier to identify among multiple open tabs.

The favicon should:
- Be themed appropriately for ScriptGrabber (using the rocket emoji 🚀 from the app branding)
- Support multiple sizes for different device contexts
- Follow web standards for favicon implementation
- Be properly linked in the HTML for browser compatibility

## Relevant Files
Use these files to resolve the chore:

- **apps/frontend/index.html** (line 1-6) - Main HTML file where favicon links need to be added in the `<head>` section
  - Currently contains basic meta tags and title
  - Need to add `<link>` tags for favicon references

### New Files
- **apps/frontend/public/favicon.ico** - Traditional ICO format favicon (16x16, 32x32, 48x48)
  - Required for legacy browser support and bookmarks
  - Will be automatically served at `/favicon.ico` by Vite

- **apps/frontend/public/favicon.svg** - Modern SVG favicon
  - Scalable vector format for modern browsers
  - Better quality at all sizes
  - Smaller file size

- **apps/frontend/public/apple-touch-icon.png** - Apple touch icon (180x180)
  - Required for iOS home screen bookmarks
  - Standard size is 180x180 pixels

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### Step 1: Create public directory structure
- Create `apps/frontend/public` directory if it doesn't exist
- This directory is the standard location for static assets in Vite projects
- Files in this directory are served at the root path

### Step 2: Generate favicon assets
- Create an SVG favicon with rocket emoji (🚀) or appropriate icon
- Use the SVG as source to generate ICO format with multiple sizes (16x16, 32x32, 48x48)
- Create Apple touch icon (180x180 PNG) for iOS devices
- Ensure all icons have transparent backgrounds where appropriate
- Use simple, recognizable design that works at small sizes

### Step 3: Add favicon files to public directory
- Place `favicon.ico` in `apps/frontend/public/`
- Place `favicon.svg` in `apps/frontend/public/`
- Place `apple-touch-icon.png` in `apps/frontend/public/`

### Step 4: Update HTML with favicon references
- Open `apps/frontend/index.html`
- Add favicon link tags in the `<head>` section after the viewport meta tag
- Include references for:
  - ICO format: `<link rel="icon" href="/favicon.ico" sizes="any">`
  - SVG format: `<link rel="icon" href="/favicon.svg" type="image/svg+xml">`
  - Apple touch icon: `<link rel="apple-touch-icon" href="/apple-touch-icon.png">`

### Step 5: Test favicon in development
- Run `cd apps/frontend && npm run dev` to start the development server
- Open browser to `http://localhost:5173`
- Verify favicon appears in:
  - Browser tab
  - Bookmarks (if you create one)
  - Browser history
- Test on multiple browsers (Chrome, Firefox, Safari) if available
- Clear browser cache if favicon doesn't update

### Step 6: Test production build
- Run `cd apps/frontend && npm run build` to create production build
- Run `cd apps/frontend && npm run preview` to preview production build
- Verify favicon works in production build
- Check that all favicon assets are included in the dist directory

### Step 7: Validate with Podman deployment
- Run `./scripts/stop-pod.sh` to stop any running pods
- Run `./scripts/create-pod.sh` to create fresh pod with updated frontend
- Open browser to `http://localhost:5173`
- Verify favicon appears correctly in containerized deployment
- Check browser console for any 404 errors related to favicon

## Validation Commands
Execute every command to validate the chore is complete with zero regressions.

- `test -f apps/frontend/public/favicon.ico && echo "✓ favicon.ico exists" || echo "✗ favicon.ico missing"` - Verify ICO favicon exists
- `test -f apps/frontend/public/favicon.svg && echo "✓ favicon.svg exists" || echo "✗ favicon.svg missing"` - Verify SVG favicon exists
- `test -f apps/frontend/public/apple-touch-icon.png && echo "✓ apple-touch-icon.png exists" || echo "✗ apple-touch-icon.png missing"` - Verify Apple touch icon exists
- `grep -q 'favicon.ico' apps/frontend/index.html && echo "✓ ICO favicon linked" || echo "✗ ICO favicon not linked"` - Verify ICO link in HTML
- `grep -q 'favicon.svg' apps/frontend/index.html && echo "✓ SVG favicon linked" || echo "✗ SVG favicon not linked"` - Verify SVG link in HTML
- `grep -q 'apple-touch-icon' apps/frontend/index.html && echo "✓ Apple touch icon linked" || echo "✗ Apple touch icon not linked"` - Verify Apple icon link in HTML
- `cd apps/frontend && npm run build` - Build frontend to verify no errors introduced
- `cd apps/frontend && npm run preview &` - Start preview server to test production build
- `sleep 3 && curl -s -o /dev/null -w "%{http_code}" http://localhost:4173/favicon.ico | grep -q 200 && echo "✓ favicon.ico accessible" || echo "✗ favicon.ico not accessible"` - Test favicon accessibility in preview

## Notes
- Vite automatically serves files from the `public` directory at the root path
- The `public` directory is copied as-is to the build output directory during build
- Modern browsers prefer SVG favicons for better quality, but ICO format provides fallback
- Apple touch icon is specifically for iOS devices when users add the site to home screen
- Consider using a favicon generator tool (like https://realfavicongenerator.net/) if manual creation is difficult
- The rocket emoji 🚀 from the app title is a good candidate for favicon design
- Favicon caching is aggressive in browsers - users may need to hard-refresh (Ctrl+Shift+R) to see updates
- For production deployments, consider adding a `theme-color` meta tag to match the app's color scheme
