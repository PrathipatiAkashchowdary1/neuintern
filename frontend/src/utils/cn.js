// Minimal classnames combinator — avoids pulling in an extra dependency.
export function cn(...args) {
  return args.filter(Boolean).join(' ')
}
