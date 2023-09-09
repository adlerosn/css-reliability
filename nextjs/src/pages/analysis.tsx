import Head from "next/head";
import { Inter, Source_Code_Pro } from "next/font/google";
import clsx from "clsx";
import { useQuery } from "react-query";
import { BASEAPI, matchesFirst, sleep } from "../lib/index";
import { AnalysisResult, JobMinimal } from "../types/index";
import axios from "axios";
import Link from "next/link";
import { useRouter } from "next/router";
import { useState } from "react";

const inter = Inter({ subsets: ["latin"] });
const scp = Source_Code_Pro({ subsets: ["latin"] });

export default function AnalysisPage() {
  const router = useRouter();
  const jobId = matchesFirst(router.query, "id");
  const jobsQuery = useQuery(
    "base-jobs",
    async () => axios.get<JobMinimal[]>(`${BASEAPI}/job`),
    {
      onError: async () => {
        await sleep(5000);
        jobsQuery.refetch();
      },
    }
  );
  const analysisQuery = useQuery(
    `analysis-${jobId}`,
    async () =>
      axios.get<AnalysisResult>(
        `${BASEAPI}/unzip/jobs/${jobId}/analysis.zip/analysis.json`
      ),
    {
      onError: async () => {
        await sleep(5000);
        jobsQuery.refetch();
      },
    }
  );
  const job: JobMinimal | undefined = Object.fromEntries(
    jobsQuery.data?.data.map((x) => [x.jobId, x]) || []
  )[parseInt(String(jobId))];
  const analysis = analysisQuery.data?.data;
  const analysisRecords = [...(analysis?.records || [])].sort(
    (a, b) => -a.rmse + b.rmse
  );
  const [errorTableExpanded, setErrorTableExpanded] = useState(false);
  const [resolutionExpanded, setResolutionExpanded] = useState(false);
  const problematicResolution = Object.entries(
    analysis?.indicators?.resolution || {}
  ).sort(([, a], [, b]) => -a + b);
  const [browserExpanded, setBrowserExpanded] = useState(false);
  const problematicBrowser = Object.entries(
    analysis?.indicators?.browser || {}
  ).sort(([, a], [, b]) => -a + b);
  const [platformExpanded, setPlatformExpanded] = useState(false);
  const problematicPlatform = Object.entries(
    analysis?.indicators?.platform || {}
  ).sort(([, a], [, b]) => -a + b);
  const [platformBrowserExpanded, setPlatformBrowserExpanded] = useState(false);
  const problematicPlatformBrowser = Object.entries(
    analysis?.indicators?.platformBrowser || {}
  ).sort(([, a], [, b]) => -a + b);
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
        <h1>
          #{job?.cronId}: {job?.url}
        </h1>
        <h2>
          #{job?.jobId}:{" "}
          {new Date((job?.lastScheduledSec || 0) * 1000).toString()}
        </h2>
        <h3>TOP-10s</h3>
        {problematicResolution.length > 0 && (
          <>
            <h4
              onClick={() => setResolutionExpanded(!resolutionExpanded)}
              style={{ cursor: "pointer" }}
            >
              Problematic resolutions [
              <u style={{ color: "blue" }}>
                show {resolutionExpanded ? "less" : "more"}
              </u>
              ]
            </h4>
            <table border={1}>
              <thead>
                <tr>
                  <th>Resolution</th>
                  <th>avg(rmse)</th>
                </tr>
              </thead>
              <tbody>
                {problematicResolution
                  .slice(0, resolutionExpanded ? undefined : 10)
                  .map(([x0, x1]) => (
                    <tr key={x0}>
                      <td>{x0}</td>
                      <td>{x1}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </>
        )}
        {problematicBrowser.length > 0 && (
          <>
            <h4
              onClick={() => setBrowserExpanded(!browserExpanded)}
              style={{ cursor: "pointer" }}
            >
              Problematic browser [
              <u style={{ color: "blue" }}>
                show {browserExpanded ? "less" : "more"}
              </u>
              ]
            </h4>
            <table border={1}>
              <thead>
                <tr>
                  <th>Browser</th>
                  <th>avg(rmse)</th>
                </tr>
              </thead>
              <tbody>
                {problematicBrowser
                  .slice(0, browserExpanded ? undefined : 10)
                  .map(([x0, x1]) => (
                    <tr key={x0}>
                      <td>{x0}</td>
                      <td>{x1}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </>
        )}
        {problematicPlatform.length > 0 && (
          <>
            <h4
              onClick={() => setPlatformExpanded(!platformExpanded)}
              style={{ cursor: "pointer" }}
            >
              Problematic Platforms [
              <u style={{ color: "blue" }}>
                show {platformExpanded ? "less" : "more"}
              </u>
              ]
            </h4>
            <table border={1}>
              <thead>
                <tr>
                  <th>Platform</th>
                  <th>avg(rmse)</th>
                </tr>
              </thead>
              <tbody>
                {problematicPlatform
                  .slice(0, platformExpanded ? undefined : 10)
                  .map(([x0, x1]) => (
                    <tr key={x0}>
                      <td>{x0}</td>
                      <td>{x1}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </>
        )}
        {problematicPlatformBrowser.length > 0 && (
          <>
            <h4
              onClick={() =>
                setPlatformBrowserExpanded(!platformBrowserExpanded)
              }
              style={{ cursor: "pointer" }}
            >
              Problematic PlatformBrowsers [
              <u style={{ color: "blue" }}>
                show {platformBrowserExpanded ? "less" : "more"}
              </u>
              ]
            </h4>
            <table border={1}>
              <thead>
                <tr>
                  <th>PlatformBrowser</th>
                  <th>avg(rmse)</th>
                </tr>
              </thead>
              <tbody>
                {problematicPlatformBrowser
                  .slice(0, platformBrowserExpanded ? undefined : 10)
                  .map(([x0, x1]) => (
                    <tr key={x0}>
                      <td>{x0}</td>
                      <td>{x1}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </>
        )}
        {analysisRecords.length > 0 && (
          <>
            <h4
              onClick={() => setErrorTableExpanded(!errorTableExpanded)}
              style={{ cursor: "pointer" }}
            >
              Error table [
              <u style={{ color: "blue" }}>
                show {errorTableExpanded ? "less" : "more"}
              </u>
              ]
            </h4>
            <table border={1}>
              <thead>
                <tr>
                  <th>resolution</th>
                  <th>printScope</th>
                  <th>hostname1</th>
                  <th>hostname2</th>
                  <th>platform1</th>
                  <th>platform2</th>
                  <th>browser1</th>
                  <th>browser2</th>
                  <th>rmse</th>
                  <th>more</th>
                </tr>
              </thead>
              <tbody>
                {analysisRecords
                  .slice(0, errorTableExpanded ? undefined : 10)
                  .map((x) => (
                    <tr
                      key={`${x.resolution}.${x.printScope}.${x.hostname1}.${x.hostname2}.${x.platform1}.${x.platform2}.${x.browser1}.${x.browser2}.${x.rmse}`}
                    >
                      <td>{x.resolution}</td>
                      <td>{x.printScope}</td>
                      <td>{x.hostname1}</td>
                      <td>{x.hostname2}</td>
                      <td>{x.platform1}</td>
                      <td>{x.platform2}</td>
                      <td>{x.browser1}</td>
                      <td>{x.browser2}</td>
                      <td
                        className={clsx(scp.className)}
                        style={{ textAlign: "right" }}
                      >
                        {x.rmse.toFixed(10)}
                      </td>
                      <td>
                        <Link
                          href={`/compare?id=${jobId}&resolution=${x.resolution}&printScope=${x.printScope}&hostname1=${x.hostname1}&hostname2=${x.hostname2}&platform1=${x.platform1}&platform2=${x.platform2}&browser1=${x.browser1}&browser2=${x.browser2}&rmse=${x.rmse}`}
                        >
                          Compare
                        </Link>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </>
        )}
      </main>
    </>
  );
}
