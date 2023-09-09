import { ParsedUrlQuery } from "querystring";

export const matchesFirst = (puq: ParsedUrlQuery, key: string) => {
  const cont = puq[key];
  if (cont === undefined) return undefined;
  if (Array.isArray(cont)) return cont[0];
  return cont;
};
