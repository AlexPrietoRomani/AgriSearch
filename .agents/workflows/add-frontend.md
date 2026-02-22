---
description: How to add a new frontend page or component to the Astro app
---

# Adding a New Frontend Page or Component

## Adding a New Page

1. Create the `.astro` file in the appropriate directory under `frontend/src/pages/`.
   - Project-scoped pages go in `frontend/src/pages/projects/[id]/`
   - Global pages go in `frontend/src/pages/`

2. Use the `MainLayout` wrapper:
   ```astro
   ---
   import MainLayout from '../../layouts/MainLayout.astro';
   ---
   <MainLayout title="Page Title">
     <!-- content -->
   </MainLayout>
   ```

3. For interactive content, use React/Solid client components with the `client:load` or `client:visible` directive.

## Adding a New Component

1. Create the `.tsx` file in `frontend/src/components/`.
2. Components MUST:
   - Use TypeScript with explicit prop types
   - Use TailwindCSS classes for styling
   - Include proper `aria-` attributes for accessibility
   - Have unique `id` attributes on all interactive elements
3. Export the component as default.

## API Communication

- Use the API client in `frontend/src/lib/api.ts` for all backend calls.
- Never hardcode URLs; use the configured base URL from environment variables.
- All API calls should handle loading, error, and success states.

## Design Guidelines

- Use the color palette and tokens defined in `frontend/src/styles/`
- Follow dark mode first design
- Animations: Use `transition-all duration-200` for micro-interactions
- Responsive: Mobile-first with `sm:`, `md:`, `lg:` breakpoints
