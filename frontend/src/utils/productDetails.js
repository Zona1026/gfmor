const textFields = ['vehicle_model', 'model_number', 'barcode', 'specification', 'color', 'manufacturer'];
const moneyFields = ['installation_labor'];
const blankSupplier = () => ({ supplier_name: '', purchase_price: '', wholesale_price: '' });

export function productDetailsForm(product = {}, supplierPrices = []) {
  const details = {};
  textFields.forEach(field => { details[field] = product[field] ?? ''; });
  moneyFields.forEach(field => { details[field] = product[field] ?? ''; });
  details.extra_category_ids = (product.extra_categories || []).map(category => String(category.id));
  details.category_ids = (product.categories || []).map(category => String(category.id)).filter(id => id !== String(product.category_id));
  details.legacy_wholesale_price = product.wholesale_price ?? '';
  details.supplier_prices = supplierPrices.length
    ? supplierPrices.map(price => ({ ...price, wholesale_price: price.wholesale_price ?? '' }))
    : Array.from({ length: 3 }, blankSupplier);
  return details;
}

export function appendProductDetails(formData, form) {
  const metadata = {};
  textFields.forEach(field => { metadata[field] = form[field]?.trim() || null; });
  moneyFields.forEach(field => {
    const raw = form[field];
    const value = raw === '' || raw === null || raw === undefined ? null : Number(raw);
    if (value !== null && (!Number.isSafeInteger(value) || value < 0)) {
      throw new Error('安裝工資須為非負整數');
    }
    metadata[field] = value;
  });
  const supplierPrices = form.supplier_prices
    .filter(price => price.supplier_name.trim() || price.purchase_price !== '' || (price.wholesale_price != null && price.wholesale_price !== ''))
    .map(price => {
      const name = price.supplier_name.trim();
      const value = Number(price.purchase_price);
      if (!name || price.purchase_price === '' || !Number.isSafeInteger(value) || value < 0) {
        throw new Error('請填寫進貨廠商名稱及非負整數進價，或移除未完成的列');
      }
      const rawWholesale = price.wholesale_price;
      const wholesale = rawWholesale === '' || rawWholesale == null ? null : Number(rawWholesale);
      if (wholesale !== null && (!Number.isSafeInteger(wholesale) || wholesale < 0)) {
        throw new Error('各廠商同行價須為非負整數，未設定請留空');
      }
      return { supplier_name: name, purchase_price: value, wholesale_price: wholesale };
    });
  const categoryIds = [...new Set([form.category_id, ...(form.category_ids || [])].filter(Boolean).map(Number))];
  formData.append('category_ids', JSON.stringify(categoryIds));
  formData.append('extra_category_ids', JSON.stringify((form.extra_category_ids || []).map(Number)));
  if (metadata.barcode && !/^[!-~]{1,100}$/.test(metadata.barcode)) throw new Error('商品條碼限 100 字以內的英數字或符號，不可包含空白');
  formData.append('product_metadata', JSON.stringify(metadata));
  formData.append('supplier_prices', JSON.stringify({ supplier_prices: supplierPrices }));
}

export function supplierWholesaleQuote(product) {
  const rows = product.supplier_wholesale_prices || [];
  const quote = value => value == null ? '未設定' : `NT$ ${Number(value).toLocaleString('zh-TW')}`;
  const entries = rows.map(row => `${row.supplier_name}：${quote(row.wholesale_price)}`);
  if (product.wholesale_price != null) entries.push(`舊單一同行價：${quote(product.wholesale_price)}（待確認廠商）`);
  return entries.join(' ／ ') || '未設定';
}
