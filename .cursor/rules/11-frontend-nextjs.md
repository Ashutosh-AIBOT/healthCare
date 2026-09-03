---
description: Next.js App Router patterns, data fetching, auth handling and component boundaries
globs: frontend/**/*.{ts,tsx}
alwaysApply: false
---

# Next.js patterns

## Server vs client components

Default to server components. Add `"use client"` only when the component needs state, effects, browser APIs or event handlers. Keep the client boundary as low in the tree as possible — push interactivity into small leaf components rather than marking a whole page.

## Auth: the browser never holds a token

Access and refresh tokens live in httpOnly cookies. All API calls go through Next route handlers acting as a thin proxy, so no token is ever reachable from client JavaScript. Role-based route access is enforced in `middleware.ts` before render.

```ts
// BAD
localStorage.setItem("token", res.access_token);

// GOOD - route handler proxies and forwards the httpOnly cookie
const res = await fetch("/api/proxy/lab-reports", { method: "POST", body });
```

## Data fetching

```tsx
// BAD - effect fetching, no cache, no error or loading handling
useEffect(() => { fetch("/api/members").then(r => r.json()).then(setMembers); }, []);

// GOOD
const { data, isPending, error } = useQuery({
  queryKey: ["members", familyId],
  queryFn: () => api.members.list({ familyId }),
});
```

- Server components fetch directly; client components use TanStack Query.
- Query keys are arrays starting with the resource name, then scope identifiers.
- Mutations invalidate affected query keys, and use optimistic updates for logs, reminders and toggles.
- Never call `fetch` directly in a component. Use the generated client in `lib/api`.

## Types and validation

Types and zod schemas are generated from the backend OpenAPI spec into `packages/shared-types`. Never hand-write a request or response type, and never hand-edit the generated package — regenerate it. Forms use `react-hook-form` with the generated zod schema as the resolver, so frontend and backend validation cannot drift.

## Structure and naming

- Route groups: `(marketing)`, `(auth)`, `(family)`, `(doctor)`, `(lab)`, `(admin)`.
- Components in `PascalCase.tsx`, hooks in `useThing.ts`, utilities in `kebab-case.ts`.
- Named exports only; no default exports except Next's required `page`, `layout`, `route` and `middleware` files.
- Colocate a feature's components under `components/features/<feature>/`.
- Dynamically import charts, the voice recorder and the video room — they must not land in the initial bundle.

## Streaming and jobs

AI answers stream token-by-token into an `aria-live="polite"` region. Background jobs are tracked by subscribing to the job SSE endpoint and rendering the named stage ("Extracting values 3 of 4"), never an unlabelled spinner.
