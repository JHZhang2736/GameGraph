"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import {
  getConcepts,
  getDeveloperProfile,
  getGameProfile,
  getGoldenFlow,
  getNeighbors,
  getOpportunityFrame,
  getPrototypeBrief,
  getSeedGames,
  importGame,
  listGames,
  buildOpportunityFrame,
  matchOpportunities,
  parseDeveloperProfileInput,
  searchGraphNodes,
  type NeighborsParams,
} from "@/lib/data";
import type { DeveloperProfile, OpportunityArea, ProfileParseInput } from "@/lib/types";
import type { ImportDocument } from "@/lib/import/schema";

export function useGoldenFlow() {
  return useQuery({ queryKey: ["golden-flow"], queryFn: getGoldenFlow });
}

export function useSeedGames() {
  return useQuery({ queryKey: ["seed-games"], queryFn: getSeedGames });
}

export function useGameProfile(id: string) {
  return useQuery({
    queryKey: ["game-profile", id],
    queryFn: () => getGameProfile(id),
  });
}

export function useDeveloperProfile() {
  return useQuery({ queryKey: ["developer-profile"], queryFn: getDeveloperProfile });
}

// Pass null to leave the query idle (no parse on first load); the page seeds a
// real input only after the user clicks 解析画像.
export function useParseDeveloperProfileInput(input: ProfileParseInput | null) {
  return useQuery({
    queryKey: ["profile-parse", input],
    queryFn: () => parseDeveloperProfileInput(input as ProfileParseInput),
    enabled: input !== null,
  });
}

export function useOpportunityFrame() {
  return useQuery({ queryKey: ["opportunity-frame"], queryFn: getOpportunityFrame });
}

export function useConcepts() {
  return useQuery({ queryKey: ["concepts"], queryFn: getConcepts });
}

export function usePrototypeBrief() {
  return useQuery({ queryKey: ["prototype-brief"], queryFn: getPrototypeBrief });
}

export function useGames() {
  return useQuery({ queryKey: ["games"], queryFn: listGames });
}

export function useNeighbors(params: NeighborsParams | null) {
  return useQuery({
    queryKey: ["neighbors", params],
    queryFn: () => getNeighbors(params as NeighborsParams),
    enabled: params !== null,
  });
}

export function useGraphSearch(q: string) {
  return useQuery({
    queryKey: ["graph-search", q],
    queryFn: () => searchGraphNodes(q),
    enabled: q.trim().length > 0,
  });
}

export function useImportGame() {
  return useMutation({ mutationFn: (doc: ImportDocument) => importGame(doc) });
}

export function useMatchOpportunities() {
  return useMutation({
    mutationFn: (profile: DeveloperProfile) => matchOpportunities(profile),
  });
}

export function useBuildOpportunityFrame() {
  return useMutation({
    mutationFn: ({ profile, area }: { profile: DeveloperProfile; area: OpportunityArea }) =>
      buildOpportunityFrame(profile, area),
  });
}
