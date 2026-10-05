import type { ReactNode } from "react";
import type { Resource } from "../lib/useResource";
import { describeApiError } from "../lib/errors";
import { ErrorState, LoadingSkeleton, StaleBanner } from "./ui";

/** Renders a resource through one consistent set of loading, error, stale and content states. */
export function Async<T>({
  resource,
  children,
  lines = 3,
}: {
  resource: Resource<T>;
  children: (data: T) => ReactNode;
  lines?: number;
}) {
  const { data, error, loading, stale, retry } = resource;

  if (data !== null) {
    return (
      <>
        {stale || error ? <StaleBanner onRetry={retry} /> : null}
        {children(data)}
      </>
    );
  }
  if (loading) return <LoadingSkeleton lines={lines} />;
  if (error) {
    return <ErrorState message={describeApiError(error)} onRetry={retry} />;
  }
  return null;
}
