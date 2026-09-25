const EXPLICIT_TIMEZONE_PATTERN = /(Z|[+-]\d{2}:?\d{2})$/i;
const API_DATETIME_PATTERN = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/;

export const parseUtcApiDateTime = (value) => {
  if (!value) return null;

  if (value instanceof Date) {
    return Number.isNaN(value.getTime()) ? null : value;
  }

  const rawValue = String(value).trim();
  const normalizedValue = API_DATETIME_PATTERN.test(rawValue) && !EXPLICIT_TIMEZONE_PATTERN.test(rawValue)
    ? `${rawValue.replace(' ', 'T')}Z`
    : rawValue;
  const date = new Date(normalizedValue);
  return Number.isNaN(date.getTime()) ? null : date;
};

export const formatTaipeiDateTime = (value) => {
  const date = parseUtcApiDateTime(value);
  if (!date) return '-';

  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Taipei',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23'
  }).formatToParts(date);
  const values = Object.fromEntries(parts.map(({ type, value: partValue }) => [type, partValue]));

  return `${values.year}/${values.month}/${values.day} ${values.hour}:${values.minute}`;
};
