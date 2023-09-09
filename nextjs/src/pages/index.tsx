import Head from "next/head";
import { Inter } from "next/font/google";
import clsx from "clsx";
import { useQuery } from "react-query";
import { BASEAPI, sleep } from "../lib/index";
import { Analysis, JobMinimal } from "../types/index";
import axios from "axios";
import Link from "next/link";

const inter = Inter({ subsets: ["latin"] });

export default function Home() {
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
    async () => axios.get<JobMinimal[]>(`${BASEAPI}/job`),
    {
      onError: async () => {
        await sleep(5000);
        jobsQuery.refetch();
      },
    }
  );
  const jobs = Object.fromEntries(
    jobsQuery.data?.data.map((x) => [x.jobId, x]) || []
  );
  const analyses = analysisQuery.data?.data.filter(
    (x) => x.finished && x.analysisFile
  );
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
        <h1>CSS Reliability</h1>
        {analysisQuery.status != "success" && "Loading"}
        {analysisQuery.status == "success" && (
          <ul>
            {analyses?.map((x) => (
              <li key={`analysis.${x.jobId}`}>
                <Link href={`/analysis?id=${x.analysisFile?.split("/")[1]}`}>
                  #{jobs[x.jobId]?.jobId}
                  {" - "}
                  {new Date(
                    (jobs[x.jobId]?.lastScheduledSec || 0) * 1000
                  ).toString()}{" "}
                  @ {jobs[x.jobId]?.url} (#{jobs[x.jobId]?.cronId})
                </Link>
              </li>
            ))}
          </ul>
        )}
        <p>Some pages have meaningful CSS... that breaks; this doesn&apos;t.</p>
      </main>
    </>
  );
}
