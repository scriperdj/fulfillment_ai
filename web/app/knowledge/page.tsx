"use client";

import { useState } from "react";
import { postRequest, fetcher } from "@/lib/api";
import { GlassCard } from "@/components/ui/GlassCard";
import { Search, BookOpen, Upload, FileText, Tag } from "lucide-react";
import type { KnowledgeSearchRequest, KnowledgeSearchResponse, KnowledgeIngestResponse } from "@/lib/types";

export default function KnowledgePage() {
    const [query, setQuery] = useState("");
    const [k, setK] = useState(5);
    const [searching, setSearching] = useState(false);
    const [results, setResults] = useState<KnowledgeSearchResponse | null>(null);
    const [searchError, setSearchError] = useState<string | null>(null);

    const [ingesting, setIngesting] = useState(false);
    const [ingestResult, setIngestResult] = useState<KnowledgeIngestResponse | null>(null);
    const [ingestError, setIngestError] = useState<string | null>(null);

    async function handleSearch(e: React.FormEvent) {
        e.preventDefault();
        if (!query.trim()) return;

        setSearching(true);
        setSearchError(null);
        setResults(null);

        try {
            const body: KnowledgeSearchRequest = { query: query.trim(), k };
            const result = await postRequest<KnowledgeSearchRequest, KnowledgeSearchResponse>("/knowledge/search", body);
            setResults(result);
        } catch {
            setSearchError("Search failed. Make sure the knowledge base is indexed.");
        } finally {
            setSearching(false);
        }
    }

    async function handleIngest() {
        setIngesting(true);
        setIngestError(null);
        setIngestResult(null);

        try {
            const result = await postRequest<Record<string, never>, KnowledgeIngestResponse>("/knowledge/ingest", {});
            setIngestResult(result);
        } catch {
            setIngestError("Ingest failed. Check backend logs.");
        } finally {
            setIngesting(false);
        }
    }

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-slate-100 to-slate-400">
                    Knowledge Base
                </h1>
                <button
                    onClick={handleIngest}
                    disabled={ingesting}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-ai-500/20 border border-ai-500/30 text-ai-400 text-sm font-medium hover:bg-ai-500/30 transition-colors disabled:opacity-50"
                >
                    <Upload className="h-4 w-4" />
                    {ingesting ? "Ingesting..." : "Re-Index Knowledge Base"}
                </button>
            </div>

            {ingestResult && (
                <GlassCard className="border-success-500/20">
                    <p className="text-sm text-success-400">
                        Successfully ingested <span className="font-bold">{ingestResult.chunks_ingested}</span> chunks into the knowledge base.
                    </p>
                </GlassCard>
            )}
            {ingestError && (
                <GlassCard className="border-critical-500/20">
                    <p className="text-sm text-critical-400">{ingestError}</p>
                </GlassCard>
            )}

            {/* Search form */}
            <GlassCard>
                <form onSubmit={handleSearch} className="space-y-4">
                    <div className="flex gap-3">
                        <div className="relative flex-1">
                            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
                            <input
                                type="text"
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                placeholder="Search the knowledge base..."
                                className="h-10 w-full rounded-lg border border-white/10 bg-black/20 pl-10 pr-4 text-sm text-slate-200 placeholder-slate-500 focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
                            />
                        </div>
                        <button
                            type="submit"
                            disabled={searching}
                            className="px-6 h-10 rounded-lg bg-primary-500/20 border border-primary-500/30 text-primary-400 text-sm font-medium hover:bg-primary-500/30 transition-colors disabled:opacity-50"
                        >
                            {searching ? "Searching..." : "Search"}
                        </button>
                    </div>
                    <div className="flex items-center gap-3">
                        <label className="text-xs text-slate-400">Results count:</label>
                        <input
                            type="range"
                            min={1}
                            max={20}
                            value={k}
                            onChange={(e) => setK(parseInt(e.target.value))}
                            className="flex-1 accent-primary-500"
                        />
                        <span className="text-xs text-slate-300 w-6 text-right">{k}</span>
                    </div>
                </form>
            </GlassCard>

            {searchError && (
                <GlassCard className="border-warning-500/20">
                    <p className="text-sm text-warning-400">{searchError}</p>
                </GlassCard>
            )}

            {/* Results */}
            {results && (
                <div className="space-y-4">
                    <p className="text-sm text-slate-400">
                        {results.results.length} result{results.results.length !== 1 ? "s" : ""} found
                    </p>
                    {results.results.map((result, i) => {
                        const score = typeof result.score === "number" ? result.score : 0;
                        const metadata = result.metadata || {};
                        const metaTags = Object.entries(metadata).filter(
                            ([, v]) => typeof v === "string" || typeof v === "number"
                        );

                        return (
                            <GlassCard key={i}>
                                <div className="flex items-start justify-between mb-3">
                                    <div className="flex items-center gap-2">
                                        <FileText className="h-4 w-4 text-primary-400" />
                                        <span className="text-xs text-slate-400">Result #{i + 1}</span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs text-slate-500">Relevance</span>
                                        <div className="w-24 h-1.5 rounded-full bg-white/10">
                                            <div
                                                className="h-1.5 rounded-full bg-primary-500 transition-all"
                                                style={{ width: `${Math.min(score * 100, 100)}%` }}
                                            />
                                        </div>
                                        <span className="text-xs text-primary-400 w-10 text-right">
                                            {(score * 100).toFixed(0)}%
                                        </span>
                                    </div>
                                </div>
                                <p className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
                                    {result.content}
                                </p>
                                {metaTags.length > 0 && (
                                    <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-white/5">
                                        {metaTags.map(([key, value]) => (
                                            <span
                                                key={key}
                                                className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-slate-400"
                                            >
                                                <Tag className="h-2.5 w-2.5" />
                                                {key}: {String(value)}
                                            </span>
                                        ))}
                                    </div>
                                )}
                            </GlassCard>
                        );
                    })}
                    {results.results.length === 0 && (
                        <GlassCard>
                            <div className="py-8 text-center text-slate-500">
                                <BookOpen className="h-12 w-12 mx-auto opacity-20 mb-2" />
                                <p>No results found. Try a different query.</p>
                            </div>
                        </GlassCard>
                    )}
                </div>
            )}

            {/* Empty state */}
            {!results && !searchError && (
                <GlassCard>
                    <div className="py-12 text-center text-slate-500">
                        <BookOpen className="h-16 w-16 mx-auto opacity-20 mb-4" />
                        <p className="text-lg font-medium text-slate-400">Search the Knowledge Base</p>
                        <p className="text-sm mt-1">
                            Query ingested policies, procedures, and documentation used by AI agents.
                        </p>
                    </div>
                </GlassCard>
            )}
        </div>
    );
}
