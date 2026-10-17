export function moveLineItem(items, index, offset) {
  const target = index + offset;
  if (index < 0 || index >= items.length || target < 0 || target >= items.length) return;
  const [item] = items.splice(index, 1);
  items.splice(target, 0, item);
}

// Moving a row does not change promotion eligibility or require another quote.
export const promotionLineKey = lines => JSON.stringify(lines
  .filter(item => !item.promotion_gift_id)
  .map(item => JSON.stringify([item.product_id, item.type, item.quantity, item.is_confirmed]))
  .sort());

export function mergePromotionGifts(lines, gifts) {
  const remaining = [...gifts];
  const result = [];
  for (const item of lines) {
    if (!item.promotion_gift_id) {
      result.push(item);
      continue;
    }
    const index = remaining.findIndex(gift => gift.promotion_gift_id === item.promotion_gift_id
      && gift.product_id === item.product_id);
    if (index >= 0) result.push({ ...item, ...remaining.splice(index, 1)[0] });
  }
  return [...result, ...remaining];
}
