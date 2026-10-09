export const lineItemTotal = (item) => {
  const amount = Math.max(0, Number(item.quantity) || 0)
    * Math.max(0, Number(item.unit_price) || 0);
  return item.type === 'DISCOUNT' && amount > 0 ? -amount : amount;
};

export const calculateTotal = (items) => {
  return Math.max(0, items.reduce((total, item) => total + lineItemTotal(item), 0));
};

export const calculateMembershipTotal = (items) => {
  const eligibleAmount = items.reduce((total, item) => {
    return item.counts_toward_membership ? total + lineItemTotal(item) : total;
  }, 0);
  return Math.min(calculateTotal(items), Math.max(0, eligibleAmount));
};
