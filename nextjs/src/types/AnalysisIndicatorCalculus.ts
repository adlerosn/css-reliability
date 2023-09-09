export type AnalysisIndicatorCalculus = {
  resolution: Record<string, number[]>;
  platform: Record<string, number[]>;
  browser: Record<string, number[]>;
  platformBrowser: Record<string, number[]>;
};
