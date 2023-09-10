import { BASEAPI, countUntil, sleep, useShortPolling } from "../lib";
import { Analysis, Job, Uptime } from "../types";
import axios from "axios";
import clsx from "clsx";
import { Inter } from "next/font/google";
import Head from "next/head";
import { useEffect } from "react";
import { useQuery } from "react-query";

const inter = Inter({ subsets: ["latin"] });

export default function StatusPage() {
  const analysisQuery = useQuery(
    "base-analysis",
    async () => axios.get<Analysis[]>(`${BASEAPI}/analysis`),
    {
      onError: async () => {
        await sleep(5000);
        analysisQuery.refetch();
      },
    }
  );
  const jobsQuery = useQuery(
    "base-jobs",
    async () => axios.get<Job[]>(`${BASEAPI}/job/submission`),
    {
      onError: async () => {
        await sleep(5000);
        jobsQuery.refetch();
      },
    }
  );
  const uptime1Query = useQuery(
    "base-uptime1",
    async () => axios.get<Uptime>(`${BASEAPI}/uptime`),
    {
      onError: async () => {
        await sleep(5000);
        uptime1Query.refetch();
      },
    }
  );
  const uptime2Query = useQuery(
    "base-uptime2",
    async () => axios.get<Uptime>(`${BASEAPI}/uptime2`),
    {
      onError: async () => {
        await sleep(5000);
        uptime2Query.refetch();
      },
    }
  );
  useShortPolling(10000, () => {
    analysisQuery.refetch();
    jobsQuery.refetch();
    uptime1Query.refetch();
    uptime2Query.refetch();
  });
  const maxSampleCount =
    jobsQuery.data?.data
      .map((x) => x.historySize)
      .reduce((p, c) => Math.max(p, c)) ?? 0;
  const screenshooters = Object.keys(uptime1Query.data?.data ?? {});
  const comparators = Object.keys(uptime2Query.data?.data ?? {});
  const jobsAll = jobsQuery.data?.data ?? [];
  const analysisAll = analysisQuery.data?.data ?? [];
  const analysisObj = Object.fromEntries(analysisAll.map((x) => [x.jobId, x]));
  const jobsObj = Object.fromEntries(jobsAll.map((x) => [x.jobId, x]));
  const cronJobs = {} as Record<string, number[]>;
  const jobWorkerCount = {} as Record<string, number>;
  const analysiss = {} as Record<string, boolean | null>;
  for (const job of jobsAll) {
    const scid = String(job.cronId);
    const sjid = String(job.jobId);
    if (!(scid in cronJobs)) cronJobs[scid] = [];
    cronJobs[scid].unshift(job.jobId);
    jobWorkerCount[sjid] = Object.values(job.workers ?? {}).filter(
      (x) => x != null
    ).length;
    const analysis: Analysis | undefined = analysisObj[sjid];
    analysiss[sjid] =
      (analysis?.assignee === null ? undefined : analysis?.finished) ?? null;
  }
  const now = new Date();
  return (
    <>
      <Head>
        <title>CSS Reliability</title>
        <meta name="description" content="Measuring CSS reliability" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <link rel="icon" href="/favicon.png" />
        <link rel="icon" href="/favicon.ico" />
      </Head>
      <main className={clsx(inter.className)}>
        <h1>Status</h1>
        <h2>Comparison Schedule Overview</h2>
        <table border={1} style={{ textAlign: "center" }}>
          <thead>
            <tr>
              <th>CronID</th>
              {countUntil(maxSampleCount).map((x) => (
                <th key={x}>{-1 - x}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Object.entries(cronJobs).map(([k, vs]) => (
              <tr key={k}>
                <th>#{k}</th>
                {countUntil(maxSampleCount).map((i) => {
                  return (
                    <td
                      key={`${k}-${i}`}
                      style={{
                        backgroundColor:
                          analysiss[vs[i]] === undefined
                            ? "#808080"
                            : analysisObj[vs[i]]?.completeness === 0
                            ? "#CCCCCC"
                            : analysiss[vs[i]] === false
                            ? "#FFFFBB"
                            : analysiss[vs[i]] === true
                            ? analysisObj[vs[i]]?.completeness ===
                              screenshooters.length
                              ? "#BBFFBB"
                              : "#CCCCFF"
                            : undefined,
                      }}
                    >
                      {analysiss[vs[i]] !== undefined && (
                        <>
                          {analysiss[vs[i]] === true
                            ? "\u2611"
                            : analysiss[vs[i]] === false
                            ? "\u2612"
                            : "\u2610"}{" "}
                          {analysisObj[vs[i]]?.completeness ?? "?"}/
                          {screenshooters.length}
                          <br />#{vs[i]}
                        </>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        <h2>Screenshooting Schedule Overview</h2>
        <table border={1} style={{ textAlign: "center" }}>
          <thead>
            <tr>
              <th>CronID</th>
              {countUntil(maxSampleCount).map((x) => (
                <th key={x}>{-1 - x}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {Object.entries(cronJobs).map(([k, vs]) => (
              <tr key={k}>
                <th>#{k}</th>
                {countUntil(maxSampleCount).map((i) => (
                  <td
                    key={`${k}-${i}`}
                    style={{
                      backgroundColor:
                        jobWorkerCount[vs[i]] === undefined
                          ? "#808080"
                          : jobWorkerCount[vs[i]] === 0
                          ? "#BBBBBB"
                          : jobWorkerCount[vs[i]] === screenshooters.length
                          ? "#BBFFBB"
                          : undefined,
                    }}
                  >
                    {jobWorkerCount[vs[i]] !== undefined && (
                      <>
                        {jobWorkerCount[vs[i]] === screenshooters.length
                          ? "\u2611"
                          : "\u2610"}{" "}
                        {jobWorkerCount[vs[i]]}/{screenshooters.length}
                        <br />#{vs[i]}
                      </>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        <h2>Screenshooting Scheduling Per-Worker Detail</h2>
        <table border={1} style={{ textAlign: "center" }}>
          <thead>
            <tr>
              <th>JobID</th>
              {screenshooters.map((x) => (
                <th key={x}>{x}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {[...jobsAll].reverse().map((j) => (
              <tr key={j.jobId}>
                <th>#{j.jobId}</th>
                {screenshooters.map((s) => (
                  <td
                    key={`${j}-${s}`}
                    style={{
                      backgroundColor:
                        (j.workers ?? {})[s] !== null ? "#AAFFAA" : undefined,
                    }}
                  >
                    {(j.workers ?? {})[s] !== null ? "\u2611" : "\u2610"}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        <h2>Screenshooters</h2>
        <table border={1}>
          <thead>
            <tr>
              <th>Worker</th>
              <th>Last seen</th>
              <th>Since</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(uptime1Query.data?.data ?? {}).map(([i, j]) => {
              const d = new Date((j ?? 0) * 1000);
              const k = (now.getTime() - d.getTime()) / 1000;
              return (
                <tr
                  key={`scrsht-${i}`}
                  style={{ backgroundColor: k > 300 ? "#FFCCCC" : undefined }}
                >
                  <td>{i}</td>
                  <td>{d.toString()}</td>
                  <td style={{ textAlign: "right" }}>{k.toFixed(0)}s</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <h2>Comparators</h2>
        <table border={1}>
          <thead>
            <tr>
              <th>Worker</th>
              <th>Last seen</th>
              <th>Since</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(uptime2Query.data?.data ?? {}).map(([i, j]) => {
              const d = new Date((j ?? 0) * 1000);
              const k = (now.getTime() - d.getTime()) / 1000;
              return (
                <tr
                  key={`imgcmp-${i}`}
                  style={{ backgroundColor: k > 300 ? "#FFCCCC" : undefined }}
                >
                  <td>{i}</td>
                  <td>{d.toString()}</td>
                  <td style={{ textAlign: "right" }}>{k.toFixed(0)}s</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </main>
    </>
  );
}
