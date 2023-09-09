import { useEffect } from "react";
import { sleep } from ".";

export const useShortPolling = (time: number, task: () => void) => {
  useEffect(() => {
    let stop = false;
    (async () => {
      while (!stop) {
        await sleep(time);
        if (stop) break;
        task();
      }
    })();
    return () => {
      stop = true;
    };
  });
};
