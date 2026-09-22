"use client";
import React, { createContext, useContext, useState, ReactNode } from 'react';

interface OptimizeResult {
    optimized_content: string;
    json_ld_snippet: string;
    simulation?: any;
}

export interface SolPageContent {
    page?: number; 
    title: string;
    type: string; 
    key_points_hint?: string;
    
    // Generated details
    bullets?: string[];
    image_suggestion?: string;
    // Generated data sources
    data_source?: string;
    speaker_notes?: string;
    
    // UI State
    isGenerating?: boolean;
    isGenerated?: boolean;
}

interface GlobalState {
  // Config / Dashboard
  brand: string;
  setBrand: (val: string) => void;
  query: string;
  setQuery: (val: string) => void;
  
  // Optimize Lab
  optInputContent: string;
  setOptInputContent: (val: string) => void;
  optSelectedTypes: string[];
  setOptSelectedTypes: (val: string[]) => void;
  optSimBrand: string;
  setOptSimBrand: (val: string) => void;
  optSimQuery: string;
  setOptSimQuery: (val: string) => void;
  optResults: Record<string, OptimizeResult>;
  setOptResults: (val: Record<string, OptimizeResult> | ((prev: Record<string, OptimizeResult>) => Record<string, OptimizeResult>)) => void;

  // Distribution Center
  distJobs: any[];
  setDistJobs: (val: any[] | ((prev: any[]) => any[])) => void;
  distExpandedJobId: number | null;
  setDistExpandedJobId: (val: number | null) => void;

  // Diagnosis / Brand Insight
  diagBrand: string;
  setDiagBrand: (val: string) => void;
  diagCompetitor: string;
  setDiagCompetitor: (val: string) => void;
  diagUserQueries: string;
  setDiagUserQueries: (val: string) => void;
  diagSelectedModel: string;
  setDiagSelectedModel: (val: string) => void;
  diagResult: any;
  setDiagResult: (val: any) => void;

  // Content Factory (Optimize) State
  contentTopic: string;
  setContentTopic: (val: string) => void;
  contentPlatform: string;
  setContentPlatform: (val: string) => void;
  contentTone: string;
  setContentTone: (val: string) => void;
  contentPoints: string;
  setContentPoints: (val: string) => void;
  contentResult: any;
  setContentResult: (val: any) => void;
  contentLogs: any[];
  setContentLogs: (val: any) => void;

  // Enterprise Brain State
  brainHistory: any[];
  setBrainHistory: (val: any[] | ((prev: any[]) => any[])) => void;
  brainSessions: any[];
  setBrainSessions: (val: any[] | ((prev: any[]) => any[])) => void;
  brainCurrentSessionId: number | null;
  setBrainCurrentSessionId: (val: number | null) => void;
  brainQuery: string;
  setBrainQuery: (val: string) => void;
  brainActiveModelName: string;
  setBrainActiveModelName: (val: string) => void;

  // Solution Generator State
  solTopic: string;
  setSolTopic: (val: string) => void;
  solAudience: string;
  setSolAudience: (val: string) => void;
  solPages: SolPageContent[];
  setSolPages: (val: SolPageContent[] | ((prev: SolPageContent[]) => SolPageContent[])) => void;
  solSelectedPageIndex: number | null;
  setSolSelectedPageIndex: (val: number | null) => void;
  solSelectedTemplateId: string;
  setSolSelectedTemplateId: (val: string) => void;
}

const GlobalStateContext = createContext<GlobalState | undefined>(undefined);

export function GlobalStateProvider({ children }: { children: ReactNode }) {
  // Dashboard State
  const [brand, setBrand] = useState('GlobalPilot AI');
  const [query, setQuery] = useState('GEO平台有哪些？');

  // Enterprise Brain State
  const [brainHistory, setBrainHistory] = useState<any[]>([]);
  const [brainSessions, setBrainSessions] = useState<any[]>([]);
  const [brainCurrentSessionId, setBrainCurrentSessionId] = useState<number | null>(null);
  const [brainQuery, setBrainQuery] = useState("");
  const [brainActiveModelName, setBrainActiveModelName] = useState("Loading...");

  // Solution Generator State
  const [solTopic, setSolTopic] = useState('');
  const [solAudience, setSolAudience] = useState('企业高管');
  const [solPages, setSolPages] = useState<SolPageContent[]>([]);
  const [solSelectedPageIndex, setSolSelectedPageIndex] = useState<number | null>(null);
  const [solSelectedTemplateId, setSolSelectedTemplateId] = useState<string>('');

  // Diagnosis State
  const [diagBrand, setDiagBrand] = useState('GlobalPilot AI');
  const [diagCompetitor, setDiagCompetitor] = useState('');
  const [diagUserQueries, setDiagUserQueries] = useState("适合中小企业的使用的GEO平台有哪些？");
  const [diagSelectedModel, setDiagSelectedModel] = useState('auto');
  const [diagResult, setDiagResult] = useState<any>(null);

  // Content Factory State
  const [contentTopic, setContentTopic] = useState("");
  const [contentPlatform, setContentPlatform] = useState('redbook');
  const [contentTone, setContentTone] = useState('professional');
  const [contentPoints, setContentPoints] = useState("");
  const [contentResult, setContentResult] = useState<any>(null);
  const [contentLogs, setContentLogs] = useState<any[]>([]);

  // Optimize Lab State
  const [optInputContent, setOptInputContent] = useState('');
  const [optSelectedTypes, setOptSelectedTypes] = useState<string[]>(['website']);
  const [optSimBrand, setOptSimBrand] = useState('');
  const [optSimQuery, setOptSimQuery] = useState('');
  const [optResults, setOptResults] = useState<Record<string, OptimizeResult>>({});

  // Distribution State
  const [distJobs, setDistJobs] = useState<any[]>([]);
  const [distExpandedJobId, setDistExpandedJobId] = useState<number | null>(null);

  return (
    <GlobalStateContext.Provider value={{
      brand, setBrand,
      query, setQuery,
      optInputContent, setOptInputContent,
      optSelectedTypes, setOptSelectedTypes,
      optSimBrand, setOptSimBrand,
      optSimQuery, setOptSimQuery,
      optResults, setOptResults,
      distJobs, setDistJobs,
      distExpandedJobId, setDistExpandedJobId,
      diagBrand, setDiagBrand,
      diagCompetitor, setDiagCompetitor,
      diagUserQueries, setDiagUserQueries,
      diagSelectedModel, setDiagSelectedModel,
      diagResult, setDiagResult,
      contentTopic, setContentTopic,
      contentPlatform, setContentPlatform,
      contentTone, setContentTone,
      contentPoints, setContentPoints,
      contentResult, setContentResult,
      contentLogs, setContentLogs,
      brainHistory, setBrainHistory,
      brainSessions, setBrainSessions,
      brainCurrentSessionId, setBrainCurrentSessionId,
      brainQuery, setBrainQuery,
      brainActiveModelName, setBrainActiveModelName,
      solTopic, setSolTopic,
      solAudience, setSolAudience,
      solPages, setSolPages,
      solSelectedPageIndex, setSolSelectedPageIndex,
      solSelectedTemplateId, setSolSelectedTemplateId
    }}>
      {children}
    </GlobalStateContext.Provider>
  );
}

export function useGlobalState() {
  const context = useContext(GlobalStateContext);
  if (context === undefined) {
    throw new Error('useGlobalState must be used within a GlobalStateProvider');
  }
  return context;
}
