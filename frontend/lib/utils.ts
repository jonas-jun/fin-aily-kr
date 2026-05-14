export function formatPrice(price: number | null): string {
  if (price === null || price === undefined) return "—";
  return `₩${price.toLocaleString("ko-KR")}`;
}
