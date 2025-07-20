"use client"

import React, { useState, useEffect, useCallback, useMemo } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { ArrowLeft, Search, Database, Video, Clock, FileText, Filter, MoreVertical, Loader2, AlertCircle } from "lucide-react"
import Link from "next/link"

// This interface now exactly matches the VideoLibraryItem Pydantic model from `library_router.py`
interface VideoLibraryItem {
  id: string;
  title: string;
  duration: string;
  indexedAt: string; // Comes as an ISO string from the backend
  size: string;
  status: "indexed" | "processing" | "error"; // We'll hardcode this, but it could come from the API
  tags: string[];
  description?: string;
}

// A custom hook for debouncing input value changes
const useDebounce = (value: string, delay: number): string => {
  const [debouncedValue, setDebouncedValue] = useState(value);
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);
    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);
  return debouncedValue;
};


// --- Main Library Page Component ---
export default function LibraryPage() {
  const [searchQuery, setSearchQuery] = useState("")
  const [selectedFilter, setSelectedFilter] = useState<"all" | "indexed" | "processing" | "error">("all")
  
  const [allVideos, setAllVideos] = useState<VideoLibraryItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  
  // Use the debounced search query to trigger API calls, preventing excessive requests
  const debouncedSearchQuery = useDebounce(searchQuery, 300);

  // --- REAL API DATA FETCHING ---
  useEffect(() => {
    const fetchLibrary = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const params = new URLSearchParams();
        // The backend `library_router` now supports a `search` query parameter
        if (debouncedSearchQuery) {
          params.append("search", debouncedSearchQuery);
        }
        
        const res = await fetch(`/api/v1/library?${params.toString()}`);
        if (!res.ok) {
          throw new Error("Failed to fetch video library. The server may be unavailable.");
        }
        const data: VideoLibraryItem[] = await res.json();
        setAllVideos(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "An unknown error occurred.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchLibrary();
  }, [debouncedSearchQuery]); // Re-fetch only when the debounced search query changes

  // --- CLIENT-SIDE FILTERING LOGIC ---
  const filteredVideos = useMemo(() => {
    return allVideos.filter((video) => {
      // The backend already handles the search, but we can keep client-side filtering for status
      const matchesFilter = selectedFilter === "all" || video.status === selectedFilter;
      return matchesFilter;
    });
  }, [allVideos, selectedFilter]);

  // --- DYNAMICALLY CALCULATED FILTER OPTIONS ---
  const filterOptions = useMemo(() => [
    { value: "all", label: "All Videos", count: allVideos.length },
    { value: "indexed", label: "Indexed", count: allVideos.filter((v) => v.status === "indexed").length },
    // These statuses would come from a more complex state management system in a full app
    { value: "processing", label: "Processing", count: 0 },
    { value: "error", label: "Error", count: 0 },
  ], [allVideos]);

  // --- UI RENDERING LOGIC ---
  const getStatusColor = (status: VideoLibraryItem["status"]) => {
    switch (status) {
      case "indexed": return "bg-green-500/20 text-green-300 border-green-500/30";
      case "processing": return "bg-blue-500/20 text-blue-300 border-blue-500/30";
      case "error": return "bg-red-500/20 text-red-300 border-red-500/30";
    }
  };

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, index) => (
            <Card key={index} className="bg-white/10 backdrop-blur-sm border-white/10 p-4 animate-pulse">
              <div className="h-8 bg-slate-700 rounded w-3/4 mb-4"></div>
              <div className="h-4 bg-slate-700 rounded w-full mb-2"></div>
              <div className="h-4 bg-slate-700 rounded w-1/2 mb-4"></div>
              <div className="flex justify-between items-center mt-4">
                <div className="h-8 bg-slate-700 rounded w-2/5"></div>
                <div className="h-8 bg-slate-700 rounded w-1/3"></div>
              </div>
            </Card>
          ))}
        </div>
      );
    }
    
    if (error) {
      return (
        <Card className="bg-red-500/10 backdrop-blur-sm border-red-500/20">
          <CardContent className="text-center py-12 flex flex-col items-center">
            <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">Failed to Load Library</h3>
            <p className="text-red-300">{error}</p>
          </CardContent>
        </Card>
      );
    }
    
    if (filteredVideos.length === 0) {
      return (
        <Card className="bg-white/5 backdrop-blur-sm border-white/10">
          <CardContent className="text-center py-12">
            <Database className="w-16 h-16 text-blue-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">
              {searchQuery ? "No Videos Found" : "Your Library is Empty"}
            </h3>
            <p className="text-white/70 mb-6">
              {searchQuery ? "Try adjusting your search query." : "Start by indexing videos to populate your library."}
            </p>
            {!searchQuery && (
              <Link href="/index">
                <Button className="bg-gradient-to-r from-purple-500 to-pink-600 hover:from-purple-600 hover:to-pink-700 text-white">
                  <Video className="w-4 h-4 mr-2" /> Index Your First Video
                </Button>
              </Link>
            )}
          </CardContent>
        </Card>
      );
    }

    return (
      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredVideos.map((video) => (
          <Card key={video.id} className="bg-white/10 backdrop-blur-sm border-white/20 hover:bg-white/15 transition-all duration-300 transform hover:scale-[1.02] group flex flex-col">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between">
                 <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center shrink-0">
                    <Video className="w-5 h-5 text-white" />
                 </div>
                 <Badge variant="outline" className={getStatusColor(video.status)}>
                    {video.status.charAt(0).toUpperCase() + video.status.slice(1)}
                 </Badge>
              </div>
              <CardTitle className="text-lg text-white line-clamp-2 pt-2">{video.title}</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col flex-grow">
              <div className="space-y-3 flex-grow">
                <CardDescription className="text-white/70 line-clamp-2">{video.description}</CardDescription>
                <div className="flex items-center justify-between text-sm text-white/60">
                  <div className="flex items-center space-x-1"><Clock className="w-4 h-4" /><span>{video.duration}</span></div>
                  <div className="flex items-center space-x-1"><FileText className="w-4 h-4" /><span>{video.size}</span></div>
                </div>
                <div className="flex flex-wrap gap-1">
                  {video.tags.map((tag) => <Badge key={tag} variant="secondary" className="bg-white/10 text-white/80 border-white/20 text-xs">{tag}</Badge>)}
                </div>
              </div>
              <div className="text-xs text-white/50 pt-3">Indexed on {new Date(video.indexedAt).toLocaleDateString()}</div>
              <div className="flex space-x-2 pt-4 mt-auto">
                <Link href={`/query?video=${video.id}`} className="flex-1">
                  <Button size="sm" className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white"><Search className="w-4 h-4 mr-1" />Query</Button>
                </Link>
                <Button size="sm" variant="outline" className="border-white/30 text-white/70 hover:text-white hover:bg-white/10 bg-transparent">Details</Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-20 right-20 w-64 h-64 bg-indigo-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse"></div>
        <div className="absolute bottom-20 left-20 w-64 h-64 bg-blue-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse delay-1000"></div>
      </div>
      <div className="relative z-10">
        {/* Header */}
        <header className="container mx-auto px-6 py-8">
          <nav className="flex items-center justify-between">
            <Link href="/" className="flex items-center space-x-2 text-white hover:text-blue-300 transition-colors">
              <ArrowLeft className="w-5 h-5" />
              <span>Back to Home</span>
            </Link>
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-gradient-to-r from-indigo-500 to-blue-600 rounded-lg flex items-center justify-center">
                <Database className="w-4 h-4 text-white" />
              </div>
              <span className="text-xl font-bold text-white">Video Library</span>
            </div>
          </nav>
        </header>

        <div className="container mx-auto px-6 py-12">
          <div className="max-w-6xl mx-auto">
            {/* Search and Filters Card */}
            <Card className="bg-white/10 backdrop-blur-sm border-white/20 mb-8">
              <CardContent className="pt-6">
                <div className="flex flex-col lg:flex-row gap-4">
                  <div className="flex-1">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-white/50" />
                      <Input placeholder="Search videos by title or description..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-12 bg-white/5 border-white/20 text-white placeholder:text-white/50
                      focus:border-blue-400 focus:ring-blue-400/20" />
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <Filter className="w-5 h-5 text-white/70" />
                    <div className="flex space-x-2">
                      {filterOptions.map((option) => (
                        <Button key={option.value} onClick={() => setSelectedFilter(option.value as any)} /* ... */ >
                          {option.label} ({option.count})
                        </Button>
                      ))}
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
            {renderContent()}
          </div>
        </div>
      </div>
    </div>
  );
}