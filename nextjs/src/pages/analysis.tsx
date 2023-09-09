import Head from "next/head";
import { Inter, Source_Code_Pro } from "next/font/google";
import clsx from "clsx";
import { useQuery } from "react-query";
import { BASEAPI, avg, matchesFirst, sleep } from "../lib/index";
import {
  AnalysisIndicator,
  AnalysisIndicatorCalculus,
  AnalysisResult,
  Job,
} from "../types/index";
import axios from "axios";
import Link from "next/link";
import { useRouter } from "next/router";
import { useState } from "react";

const inter = Inter({ subsets: ["latin"] });
const scp = Source_Code_Pro({ subsets: ["latin"] });

export default function AnalysisPage() {
  const router = useRouter();
  const [filters, setFilters] = useState<string[]>([]);
  const addFilter = (f: string) => {
    setFilters([...filters.filter((x) => x !== f), f]);
  };
  const removeFilter = (f: string) => {
    setFilters(filters.filter((x) => x !== f));
  };
  const resetFilters = () => setFilters([]);

  const jobId = matchesFirst(router.query, "id");
  const jobsQuery = useQuery(
    "base-jobs",
    async () => axios.get<Job[]>(`${BASEAPI}/job`),
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
        analysisQuery.refetch();
      },
    }
  );
  const job: Job | undefined = Object.fromEntries(
    jobsQuery.data?.data.map((x) => [x.jobId, x]) || []
  )[parseInt(String(jobId))];
  const analysis = analysisQuery.data?.data;
  const analysisRecords = [...(analysis?.records || [])]
    .sort((a, b) => -a.rmse + b.rmse)
    .filter(
      (x) =>
        filters.length === 0 ||
        filters.includes(`${x.resolution}.${x.printScope}`) ||
        filters.includes(`${x.platform1}.${x.browser1}`) ||
        filters.includes(`${x.platform2}.${x.browser2}`) ||
        filters.includes(x.browser1) ||
        filters.includes(x.browser2) ||
        filters.includes(x.platform1) ||
        filters.includes(x.platform2)
    );
  const newScoresCalculus: AnalysisIndicatorCalculus = {
    resolution: {},
    platform: {},
    browser: {},
    platformBrowser: {},
  };
  for (const analysisRecord of analysisRecords) {
    let key1 = `${analysisRecord.resolution}.${analysisRecord.printScope}`;
    let key2 = `${analysisRecord.platform1}.${analysisRecord.browser1}`;
    let key3 = `${analysisRecord.platform2}.${analysisRecord.browser2}`;
    let key4 = analysisRecord.browser1;
    let key5 = analysisRecord.browser2;
    let key6 = analysisRecord.platform1;
    let key7 = analysisRecord.platform2;
    if (!Object.keys(newScoresCalculus.resolution).includes(key1))
      newScoresCalculus.resolution[key1] = [];
    if (!Object.keys(newScoresCalculus.platformBrowser).includes(key2))
      newScoresCalculus.platformBrowser[key2] = [];
    if (!Object.keys(newScoresCalculus.platformBrowser).includes(key3))
      newScoresCalculus.platformBrowser[key3] = [];
    if (!Object.keys(newScoresCalculus.browser).includes(key4))
      newScoresCalculus.browser[key4] = [];
    if (!Object.keys(newScoresCalculus.browser).includes(key5))
      newScoresCalculus.browser[key5] = [];
    if (!Object.keys(newScoresCalculus.platform).includes(key6))
      newScoresCalculus.platform[key6] = [];
    if (!Object.keys(newScoresCalculus.platform).includes(key7))
      newScoresCalculus.platform[key7] = [];
    newScoresCalculus.resolution[key1].push(analysisRecord.rmse);
    if (key4 !== key5 || key6 !== key7) {
      newScoresCalculus.platformBrowser[key2].push(analysisRecord.rmse);
      newScoresCalculus.platformBrowser[key3].push(analysisRecord.rmse);
    }
    if (key4 !== key5) {
      newScoresCalculus.browser[key4].push(analysisRecord.rmse);
      newScoresCalculus.browser[key5].push(analysisRecord.rmse);
    }
    if (key6 !== key7) {
      newScoresCalculus.platform[key6].push(analysisRecord.rmse);
      newScoresCalculus.platform[key7].push(analysisRecord.rmse);
    }
  }
  const newScores: AnalysisIndicator = Object.fromEntries(
    Object.entries(newScoresCalculus).map(([k1, o]) => [
      k1,
      Object.fromEntries(Object.entries(o).map(([k2, v]) => [k2, avg(v, 0)])),
    ])
  );
  const [errorTableExpanded, setErrorTableExpanded] = useState(false);
  const [resolutionExpanded, setResolutionExpanded] = useState(false);
  const problematicResolution = Object.entries(
    analysis?.indicators?.resolution || {}
  )
    .sort(([, a], [, b]) => -a + b)
    .map(([x, y]) => [x, y, newScores.resolution[x] ?? 0]) satisfies [
    string,
    number,
    number
  ][];
  const [browserExpanded, setBrowserExpanded] = useState(false);
  const problematicBrowser = Object.entries(analysis?.indicators?.browser || {})
    .sort(([, a], [, b]) => -a + b)
    .map(([x, y]) => [x, y, newScores.browser[x] ?? 0]) satisfies [
    string,
    number,
    number
  ][];
  const [platformExpanded, setPlatformExpanded] = useState(false);
  const problematicPlatform = Object.entries(
    analysis?.indicators?.platform || {}
  )
    .sort(([, a], [, b]) => -a + b)
    .map(([x, y]) => [x, y, newScores.platform[x] ?? 0]) satisfies [
    string,
    number,
    number
  ][];
  const [platformBrowserExpanded, setPlatformBrowserExpanded] = useState(false);
  const problematicPlatformBrowser = Object.entries(
    analysis?.indicators?.platformBrowser || {}
  )
    .sort(([, a], [, b]) => -a + b)
    .map(([x, y]) => [x, y, newScores.platformBrowser[x] ?? 0]) satisfies [
    string,
    number,
    number
  ][];
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
        <p>
          {filters.length === 0 ? (
            "No filters set"
          ) : (
            <>
              Filtering by: {filters.join(", ")}{" "}
              <button onClick={resetFilters}>reset</button>
            </>
          )}
        </p>
        {problematicResolution.length > 2 && (
          <>
            <h3
              onClick={() => setResolutionExpanded(!resolutionExpanded)}
              style={{ cursor: "pointer" }}
            >
              Problematic resolutions
              {problematicResolution.length > 10 && (
                <>
                  {" "}
                  [
                  <u style={{ color: "blue" }}>
                    show {resolutionExpanded ? "less" : "more"}
                  </u>
                  ]
                </>
              )}
            </h3>
            <table border={1}>
              <thead>
                <tr>
                  <th>Resolution</th>
                  <th>Global avg(rmse)</th>
                  <th>Filter avg(rmse)</th>
                  <th>Filter</th>
                </tr>
              </thead>
              <tbody>
                {problematicResolution
                  .slice(0, resolutionExpanded ? undefined : 10)
                  .map(([x0, x1, x2]) => (
                    <tr key={x0}>
                      <td>{x0}</td>
                      <td
                        className={clsx(scp.className)}
                        style={{ textAlign: "right" }}
                      >
                        {x1.toFixed(6)}
                      </td>
                      <td
                        className={clsx(scp.className)}
                        style={{ textAlign: "right" }}
                      >
                        {x2.toFixed(6)}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <button onClick={() => addFilter(x0)}>+</button>
                        <button onClick={() => removeFilter(x0)}>
                          {"\u2013"}
                        </button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
            {problematicResolution.length > 10 && !resolutionExpanded && (
              <span
                style={{
                  textDecoration: "underline",
                  color: "blue",
                  cursor: "pointer",
                }}
                onClick={() => setResolutionExpanded(!resolutionExpanded)}
              >
                Show {problematicResolution.length - 10} more
              </span>
            )}
          </>
        )}
        {problematicBrowser.length > 2 && (
          <>
            <h3
              onClick={() => setBrowserExpanded(!browserExpanded)}
              style={{ cursor: "pointer" }}
            >
              Problematic browser
              {problematicBrowser.length > 10 && (
                <>
                  {" "}
                  [
                  <u style={{ color: "blue" }}>
                    show {browserExpanded ? "less" : "more"}
                  </u>
                  ]
                </>
              )}
            </h3>
            <table border={1}>
              <thead>
                <tr>
                  <th>Browser</th>
                  <th>Global avg(rmse)</th>
                  <th>Filter avg(rmse)</th>
                  <th>Filter</th>
                </tr>
              </thead>
              <tbody>
                {problematicBrowser
                  .slice(0, browserExpanded ? undefined : 10)
                  .map(([x0, x1, x2]) => (
                    <tr key={x0}>
                      <td>{x0}</td>
                      <td
                        className={clsx(scp.className)}
                        style={{ textAlign: "right" }}
                      >
                        {x1.toFixed(6)}
                      </td>
                      <td
                        className={clsx(scp.className)}
                        style={{ textAlign: "right" }}
                      >
                        {x2.toFixed(6)}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <button onClick={() => addFilter(x0)}>+</button>
                        <button onClick={() => removeFilter(x0)}>
                          {"\u2013"}
                        </button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
            {problematicBrowser.length > 10 && !browserExpanded && (
              <span
                style={{
                  textDecoration: "underline",
                  color: "blue",
                  cursor: "pointer",
                }}
                onClick={() => setBrowserExpanded(!browserExpanded)}
              >
                Show {problematicBrowser.length - 10} more
              </span>
            )}
          </>
        )}
        {problematicPlatform.length > 2 && (
          <>
            <h3
              onClick={() => setPlatformExpanded(!platformExpanded)}
              style={{ cursor: "pointer" }}
            >
              Problematic Platforms
              {problematicPlatform.length > 10 && (
                <>
                  {" "}
                  [
                  <u style={{ color: "blue" }}>
                    show {platformExpanded ? "less" : "more"}
                  </u>
                  ]
                </>
              )}
            </h3>
            <table border={1}>
              <thead>
                <tr>
                  <th>Platform</th>
                  <th>Global avg(rmse)</th>
                  <th>Filter avg(rmse)</th>
                  <th>Filter</th>
                </tr>
              </thead>
              <tbody>
                {problematicPlatform
                  .slice(0, platformExpanded ? undefined : 10)
                  .map(([x0, x1, x2]) => (
                    <tr key={x0}>
                      <td>{x0}</td>
                      <td
                        className={clsx(scp.className)}
                        style={{ textAlign: "right" }}
                      >
                        {x1.toFixed(6)}
                      </td>
                      <td
                        className={clsx(scp.className)}
                        style={{ textAlign: "right" }}
                      >
                        {x2.toFixed(6)}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <button onClick={() => addFilter(x0)}>+</button>
                        <button onClick={() => removeFilter(x0)}>
                          {"\u2013"}
                        </button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
            {problematicPlatform.length > 10 && !platformExpanded && (
              <span
                style={{
                  textDecoration: "underline",
                  color: "blue",
                  cursor: "pointer",
                }}
                onClick={() => setPlatformExpanded(!platformExpanded)}
              >
                Show {problematicPlatform.length - 10} more
              </span>
            )}
          </>
        )}
        {problematicPlatformBrowser.length > 2 && (
          <>
            <h3
              onClick={() =>
                setPlatformBrowserExpanded(!platformBrowserExpanded)
              }
              style={{ cursor: "pointer" }}
            >
              Problematic PlatformBrowsers
              {problematicPlatformBrowser.length > 10 && (
                <>
                  {" "}
                  [
                  <u style={{ color: "blue" }}>
                    show {platformBrowserExpanded ? "less" : "more"}
                  </u>
                  ]
                </>
              )}
            </h3>
            <table border={1}>
              <thead>
                <tr>
                  <th>PlatformBrowser</th>
                  <th>Global avg(rmse)</th>
                  <th>Filter avg(rmse)</th>
                  <th>Filter</th>
                </tr>
              </thead>
              <tbody>
                {problematicPlatformBrowser
                  .slice(0, platformBrowserExpanded ? undefined : 10)
                  .map(([x0, x1, x2]) => (
                    <tr key={x0}>
                      <td>{x0}</td>
                      <td
                        className={clsx(scp.className)}
                        style={{ textAlign: "right" }}
                      >
                        {x1.toFixed(6)}
                      </td>
                      <td
                        className={clsx(scp.className)}
                        style={{ textAlign: "right" }}
                      >
                        {x2.toFixed(6)}
                      </td>
                      <td style={{ textAlign: "center" }}>
                        <button onClick={() => addFilter(x0)}>+</button>
                        <button onClick={() => removeFilter(x0)}>
                          {"\u2013"}
                        </button>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
            {problematicPlatformBrowser.length > 10 &&
              !platformBrowserExpanded && (
                <span
                  style={{
                    textDecoration: "underline",
                    color: "blue",
                    cursor: "pointer",
                  }}
                  onClick={() =>
                    setPlatformBrowserExpanded(!platformBrowserExpanded)
                  }
                >
                  Show {problematicPlatformBrowser.length - 10} more
                </span>
              )}
          </>
        )}
        {analysisRecords.length > 0 && (
          <>
            <h3
              onClick={() => setErrorTableExpanded(!errorTableExpanded)}
              style={{ cursor: "pointer" }}
            >
              Error table
              {analysisRecords.length > 10 && (
                <>
                  {" "}
                  [
                  <u style={{ color: "blue" }}>
                    show {errorTableExpanded ? "less" : "more"}
                  </u>
                  ]
                </>
              )}
            </h3>
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
                        {x.rmse.toFixed(6)}
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
            {analysisRecords.length > 10 && !errorTableExpanded && (
              <span
                style={{
                  textDecoration: "underline",
                  color: "blue",
                  cursor: "pointer",
                }}
                onClick={() => setErrorTableExpanded(!errorTableExpanded)}
              >
                Show {analysisRecords.length - 10} more
              </span>
            )}
          </>
        )}
      </main>
    </>
  );
}
