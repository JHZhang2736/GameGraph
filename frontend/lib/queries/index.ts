"use client";

import { useQuery } from "@tanstack/react-query";
import {
  getConcepts,
  getDeveloperProfile,
  getGameProfile,
  getGoldenFlow,
  getGraph,
  getOpportunityFrame,
  getPrototypeBrief,
  getSeedGames,
  parseDeveloperProfileInput,
} from "@/lib/data";
import type { ProfileParseInput } from "@/lib/types";

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

export function useGraph() {
  return useQuery({ queryKey: ["graph"], queryFn: getGraph });
}

export function useDeveloperProfile() {
  return useQuery({ queryKey: ["developer-profile"], queryFn: getDeveloperProfile });
}

export function useParseDeveloperProfileInput(input: ProfileParseInput) {
  return useQuery({
    queryKey: ["profile-parse", input],
    queryFn: () => parseDeveloperProfileInput(input),
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
