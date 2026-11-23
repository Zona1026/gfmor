export function vehicleBrandOptions(values = [], current = '') {
  const options = new Set(values.map(value => value?.trim()).filter(Boolean));
  if (current) options.add(current);
  return [...options].sort((a, b) => a.localeCompare(b, 'zh-Hant'));
}
