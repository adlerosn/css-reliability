import clsx from "clsx";
import { Inter } from "next/font/google";
import Head from "next/head";

const inter = Inter({ subsets: ["latin"] });

export default function AboutPage() {
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
        <h1>About</h1>
        <h2>What is this?</h2>
        <p>
          This is an effort to reduce uncertainty on how frontend looks across
          multiple browsers on each platform.
        </p>
        <h2>Why?</h2>
        <p>
          Should you trust documentation enough not to double check with
          implementations?
        </p>
        <p>
          Why only the back-end gets this cool continuous monitoring and the
          front-end is this wild unmonitored land in which you make a lot of
          effort to draw pixels on the screen and don&apos;t track them?
        </p>
        <p>
          Is opening up a browser in your docker-based CI/CD pipeline enough to
          regain confidence that pixels on the screen will be the same?
        </p>
        <p>
          Why “are” browsers considered to be the same across operiating systems
          even when they draw pixels differently on every single one of them?
        </p>
        <p>
          If the interface with your customer is the front-end, and you truly
          care about it being your flagship, your money-maker, your
          spokesperson, then why you wait users to report it being broken?
        </p>
        <p>Why not doing this?</p>
        <h2>How?</h2>
        <img src="/blockdiagram.png" alt="Block diagram" />
        <p>
          In short, there is a job queue on the API, which are taken by the
          screenshooter workers. Such images enters the comparator queue, which
          then generates enough reporting material to send back to the API.
        </p>
        <p>The API, then sends data to the frontend.</p>
      </main>
    </>
  );
}
