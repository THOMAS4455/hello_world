export const computeDrawdownSeries = (equityCurve = []) => {
  if (!Array.isArray(equityCurve) || equityCurve.length < 2) {
    return [];
  }
  let peak = equityCurve[0] || 1;
  return equityCurve.map((value) => {
    const v = Number(value) || 0;
    if (v > peak) peak = v;
    return peak > 0 ? (v - peak) / peak : 0;
  });
};
