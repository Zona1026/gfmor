export function buildConsumptionRecords(customer) {
  if (!customer) return [];
  const spending = customer.spending_records || [];
  const services = (customer.service_records || []).map(record => ({
    ...record,
    id: `work-order-${record.work_order_id}`,
    source: 'work_order',
    source_id: record.work_order_id,
    date: record.completed_at || record.scheduled_at || record.created_at,
    amount: record.total_amount,
    method: [...new Set(spending.filter(payment => payment.source === 'work_order_payment'
      && payment.source_id === record.work_order_id).map(payment => payment.method).filter(Boolean))].join('、')
  }));
  const orders = spending.filter(record => record.source === 'order').map(record => ({
    ...record,
    date: record.paid_at || record.created_at,
    payment_status: ['FULL_PAID', 'COMPLETED'].includes(record.status) ? 'PAID'
      : record.status === 'DEPOSIT_PAID' ? 'PARTIALLY_PAID'
      : record.status === 'PENDING' ? 'UNPAID' : null
  }));
  return [...services, ...orders].sort((a, b) =>
    (Date.parse(b.date) || 0) - (Date.parse(a.date) || 0) || b.source_id - a.source_id);
}
