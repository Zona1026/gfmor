export const MANUAL_PRODUCT_CATEGORY = '__manual__';

export function productCategories(product) {
  return primaryCategories(product);
}

function primaryCategories(product) {
  if (product.categories?.length) return product.categories.map(category => ({ value: String(category.id), name: category.name }));
  if (product.category_id) return [{ value: String(product.category_id), name: product.category_info?.name || product.category || '未命名分類' }];
  return product.category ? [{ value: `name:${product.category}`, name: product.category }] : [];
}

export function categoryOptions(products) {
  const options = new Map();
  products.forEach(product => productCategories(product).forEach(category => options.set(category.value, category)));
  return [...options.values()].sort((a, b) => a.name.localeCompare(b.name, 'zh-TW'));
}

export function supplierOptions(products, category = '') {
  const names = new Set();
  products.filter(product => !category || productCategories(product).some(entry => entry.value === category))
    .forEach(product => (product.supplier_wholesale_prices || []).forEach(row => names.add(row.supplier_name)));
  return [...names].sort((a, b) => a.localeCompare(b, 'zh-TW'));
}

export function filterPickerProducts(products, category = '', supplier = '') {
  return products.filter(product => (!category || productCategories(product).some(entry => entry.value === category))
    && (!supplier || (product.supplier_wholesale_prices || []).some(row => row.supplier_name === supplier)));
}
