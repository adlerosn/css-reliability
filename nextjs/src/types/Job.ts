import { Uptime } from ".";

export type Job = {
  cronId: number;
  url: string;
  jobId: number;
  lastScheduledSec: number;
  checkReadyJs: number;
  historySize: number;
  hours: number;
  preRunJs: string;
  scrolltoJs: string;
  scrolltox: number;
  scrolltoy: number;
  wait: number;
  waitJs: number;
  workers?: Uptime;
};
