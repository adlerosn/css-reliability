import { AnalysisResult, Uptime } from ".";

export type Analysis = {
  cronId: number;
  jobId: number;
  finished: boolean;
  assignee: string | null;
  assigneeTime: number | null;
  completeness: number;
  workers: Record<string, string | null>;
  analysisFile: string | null;
  analysis: null | AnalysisResult;
};
