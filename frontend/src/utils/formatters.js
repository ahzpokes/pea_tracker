export const formatNumber = new Intl.NumberFormat('fr-FR', {
  maximumFractionDigits: 2,
  minimumFractionDigits: 2
});

export const formatPercent = (value) => {
  if (value === null || value === undefined) return '—';
  return new Intl.NumberFormat('fr-FR', {
    style: 'percent',
    maximumFractionDigits: 2,
    minimumFractionDigits: 2
  }).format(value);
};