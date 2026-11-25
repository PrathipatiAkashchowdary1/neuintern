// Rupee amounts as set by the admin, e.g. 150 -> "₹150", 1499.5 -> "₹1,499.5".
export function formatRupees(amount) {
  return `₹${Number(amount).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`
}
