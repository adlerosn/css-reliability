import { AnalysisIndicator, AnalysisRecord } from ".";

export type AnalysisResult = {
  indicators: AnalysisIndicator;
  records: AnalysisRecord[];
};
