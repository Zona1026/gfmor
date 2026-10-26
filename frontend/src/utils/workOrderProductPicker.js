export const MANUAL_PRODUCT_CATEGORY = '__manual__';

export function productCategories(product) {
  return primaryCategories(product);
}

function primaryCategories(product) {
  if (product.categories?.length) return product.categories.map(category => ({ ...category, value: String(category.id) }));
  if (product.category_id) return [{ ...product.category_info, id: product.category_id, value: String(product.category_id), name: product.category_info?.name || product.category || '未命名分類' }];
  return product.category ? [{ value: `name:${product.category}`, name: product.category }] : [];
}

export function compareCategories(a, b) {
  return (a.sort_order ?? 0) - (b.sort_order ?? 0)
    || a.name.localeCompare(b.name, 'zh-TW')
    || (Number(a.id) || 0) - (Number(b.id) || 0);
}

export function categoryOptions(products, { selectedValue = '', includeInactive = false } = {}) {
  const options = new Map();
  products.forEach(product => productCategories(product).forEach(category => options.set(category.value, category)));
  return [...options.values()]
    .filter(category => includeInactive || category.is_active == null || Boolean(category.is_active) || category.value === selectedValue)
    .sort(compareCategories);
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

export function manufacturerOptions(products, category = '') {
  const names = filterPickerProducts(products, category)
    .map(product => (product.manufacturer || '').trim())
    .filter(Boolean);
  return [...new Set(names)].sort((a, b) => a.localeCompare(b, 'zh-TW'));
}

export function filterWorkOrderProducts(products, category = '', manufacturer = '') {
  return filterPickerProducts(products, category)
    .filter(product => !manufacturer || (product.manufacturer || '').trim() === manufacturer);
}
