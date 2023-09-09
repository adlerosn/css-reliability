import Head from "next/head";
import { Inter, Source_Code_Pro } from "next/font/google";
import clsx from "clsx";
import { useQuery } from "react-query";
import { BASEAPI, matchesFirst, sleep } from "../lib/index";
import { JobMinimal } from "../types/index";
import axios from "axios";
import { useRouter } from "next/router";

const inter = Inter({ subsets: ["latin"] });
const scp = Source_Code_Pro({ subsets: ["latin"] });

export default function ComparePage() {
  const router = useRouter();
  const jobId = matchesFirst(router.query, "id");
  const resolution = matchesFirst(router.query, "resolution");
  const printScope = matchesFirst(router.query, "printScope");
  const hostname1 = matchesFirst(router.query, "hostname1");
  const hostname2 = matchesFirst(router.query, "hostname2");
  const platform1 = matchesFirst(router.query, "platform1");
  const platform2 = matchesFirst(router.query, "platform2");
  const browser1 = matchesFirst(router.query, "browser1");
  const browser2 = matchesFirst(router.query, "browser2");
  const rmse = parseFloat(matchesFirst(router.query, "rmse") || "0");
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
  const job: JobMinimal | undefined = Object.fromEntries(
    jobsQuery.data?.data.map((x) => [x.jobId, x]) || []
  )[parseInt(String(jobId))];
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
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>{resolution}</td>
              <td>{printScope}</td>
              <td>{hostname1}</td>
              <td>{hostname2}</td>
              <td>{platform1}</td>
              <td>{platform2}</td>
              <td>{browser1}</td>
              <td>{browser2}</td>
              <td className={clsx(scp.className)}>{rmse}</td>
            </tr>
          </tbody>
        </table>
        <h3>Images</h3>
        <table border={1}>
          <thead>
            <tr>
              <th>1</th>
              <th>cmp</th>
              <th>2</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>
                <img
                  src={`${BASEAPI}/unzip/jobs/${jobId}/${hostname1}.zip/${platform1}.${hostname1}.${browser1}.${resolution}.${printScope}.png`}
                  alt={""}
                  style={{ maxWidth: "calc(33.33333vw - 1rem)" }}
                />
              </td>
              <td>
                <img
                  src={`${BASEAPI}/unzip/jobs/${jobId}/analysis.zip/${resolution}.${printScope}.${hostname1}.${hostname2}.${platform1}.${platform2}.${browser1}.${browser2}.png`}
                  alt={""}
                  style={{ maxWidth: "calc(33.33333vw - 1rem)" }}
                />
              </td>
              <td>
                <img
                  src={`${BASEAPI}/unzip/jobs/${jobId}/${hostname2}.zip/${platform2}.${hostname2}.${browser2}.${resolution}.${printScope}.png`}
                  alt={""}
                  style={{ maxWidth: "calc(33.33333vw - 1rem)" }}
                />
              </td>
            </tr>
          </tbody>
        </table>
      </main>
    </>
  );
}
