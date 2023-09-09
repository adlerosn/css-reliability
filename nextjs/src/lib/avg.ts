export const avg = (vs: number[], d?: number) => {
  if (vs.length < 1) {
    if (d === undefined) throw new Error("Cannot get average of empty list");
    return d;
  }
  if (vs.length == 1) return vs[0];
  return vs.reduce((p, c) => p + c) / vs.length;
};
