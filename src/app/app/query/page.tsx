"use client"

import React, { useState, useEffect } from "react"
import { useSearchParams } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Search, Send, Loader2, ArrowLeft, Clock, FileText, Video, Brain, AlertCircle } from "lucide-react"
import Link from "next/link"

// --- THIS INTERFACE IS NOW 100% ALIGNED WITH `core/schemas.py` ---
interface APIResponseSource {
  id: string;
  source_video: string;
  timestamp: string;
  content: string; // This is the query-aware VLM description
  score: number;
}

interface APIQueryResponse {
  query: string;
  answer: string;
  retrieved_sources: APIResponseSource[];
}
// ----------------------------------------------------------------------

export default function QueryPage() {
  const [query, setQuery] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [response, setResponse] = useState<APIQueryResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const searchParams = useSearchParams()

  // Effect to pre-fill the query if coming from the library page
  useEffect(() => {
    const videoId = searchParams.get('video')
    if (videoId) {
      setQuery(`Summarize the key points from the video with ID: ${videoId}`)
    }
  }, [searchParams]);

  // This function correctly calls the backend API. No changes needed to its logic.
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!query.trim()) return

    setIsLoading(true)
    setError(null)
    setResponse(null)

    try {
      const res = await fetch("/api/v1/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query.trim() }),
      })

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Failed to process query. The server returned an error.");
      }

      const data: APIQueryResponse = await res.json()
      setResponse(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : "An unknown error occurred")
    } finally {
      setIsLoading(false)
    }
  }

  // --- UI Rendering Logic ---
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-20 right-20 w-64 h-64 bg-blue-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse"></div>
        <div className="absolute bottom-20 left-20 w-64 h-64 bg-purple-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse delay-1000"></div>
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
              <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <Search className="w-4 h-4 text-white" />
              </div>
              <span className="text-xl font-bold text-white">Query Interface</span>
            </div>
          </nav>
        </header>

        <div className="container mx-auto px-6 py-12">
          <div className="max-w-4xl mx-auto">
            {/* Query Form Card is unchanged */}
            <Card className="bg-white/10 backdrop-blur-sm border-white/20 mb-8">
              <CardHeader>
                <CardTitle className="text-2xl text-white flex items-center space-x-2">
                  <Search className="w-6 h-6 text-blue-400" />
                  <span>Ask Your Question</span>
                </CardTitle>
                <CardDescription className="text-white/70">
                  Query your indexed video library with natural language
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Textarea
                      placeholder="What would you like to know about your videos? e.g., 'What are the main topics discussed in the presentation?'"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      className="min-h-[120px] bg-white/5 border-white/20 text-white placeholder:text-white/50 focus:border-blue-400 focus:ring-blue-400/20 resize-none"
                      disabled={isLoading}
                    />
                  </div>
                  <Button
                    type="submit"
                    disabled={!query.trim() || isLoading}
                    className="w-full bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-semibold py-3 rounded-xl transition-all duration-300 transform hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                        Processing...
                      </>
                    ) : (
                      <>
                        <Send className="w-5 h-5 mr-2" />
                        Submit Query
                      </>
                    )}
                  </Button>
                </form>
              </CardContent>
            </Card>

            {/* --- UPDATED ERROR AND RESPONSE DISPLAY --- */}
            
            {/* Error Display */}
            {error && (
              <Card className="bg-red-500/10 backdrop-blur-sm border-red-500/20 mb-8">
                 <CardHeader>
                    <CardTitle className="text-red-400 flex items-center space-x-2">
                       <AlertCircle className="w-6 h-6" />
                       <span>Query Error</span>
                    </CardTitle>
                 </CardHeader>
                 <CardContent>
                    <p className="text-white/80">{error}</p>
                 </CardContent>
              </Card>
            )}

            {/* Response Display */}
            {response && (
              <div className="space-y-6 animate-fade-in">
                {/* Answer */}
                <Card className="bg-white/10 backdrop-blur-sm border-white/20">
                  <CardHeader>
                    <CardTitle className="text-xl text-white flex items-center space-x-2">
                      <div className="w-8 h-8 bg-gradient-to-r from-green-500 to-blue-500 rounded-lg flex items-center justify-center">
                        <Brain className="w-4 h-4 text-white" />
                      </div>
                      <span>Synthesized Answer</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="bg-black/20 rounded-xl p-6 border border-white/10 prose prose-invert max-w-none text-white/90 leading-relaxed">
                       <p>{response.answer}</p>
                    </div>
                  </CardContent>
                </Card>

                {/* --- THIS IS THE UPDATED SOURCE RENDERING LOGIC --- */}
                {response.retrieved_sources && response.retrieved_sources.length > 0 && (
                  <Card className="bg-white/10 backdrop-blur-sm border-white/20">
                    <CardHeader>
                      <CardTitle className="text-xl text-white flex items-center space-x-2">
                        <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
                          <Video className="w-4 h-4 text-white" />
                        </div>
                        <span>Retrieved Sources</span>
                      </CardTitle>
                      <CardDescription className="text-white/70">
                        The following video segments were used as evidence to generate the answer.
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-4">
                        {response.retrieved_sources.map((source, index) => (
                          <div
                            key={source.id} // Use the unique clip ID as the key
                            className="bg-black/20 rounded-xl p-4 border border-white/10"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                              <div className="flex items-center space-x-2 flex-wrap gap-2">
                                <Badge variant="secondary" className="bg-blue-500/20 text-blue-300 border-blue-500/30">
                                  Source {index + 1}
                                </Badge>
                                <Badge variant="outline" className="border-white/30 text-white/70 font-mono">
                                  <FileText className="w-3 h-3 mr-1.5" />
                                  {source.source_video}
                                </Badge>
                                <Badge variant="outline" className="border-white/30 text-white/70 font-mono">
                                  <Clock className="w-3 h-3 mr-1.5" />
                                  {source.timestamp}
                                </Badge>
                              </div>
                              <Badge
                                variant="outline"
                                className="border-green-500/30 bg-green-500/10 text-green-300"
                              >
                                {Math.round(source.score * 100)}% Match
                              </Badge>
                            </div>
                            <p className="text-white/90 leading-relaxed italic border-l-2 border-purple-400 pl-4 py-1">
                              "{source.content}"
                            </p>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
                {/* -------------------------------------------------------------------- */}
              </div>
            )}
            
            {/* Example Queries */}
            {!response && !isLoading && (
              <Card className="bg-white/5 backdrop-blur-sm border-white/10">
                <CardHeader>
                  <CardTitle className="text-lg text-white">Example Queries</CardTitle>
                  <CardDescription className="text-white/70">Try these sample questions to get started</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid gap-3">
                    {[
                      "What are the main topics discussed in the presentation?",
                      "Can you summarize the key findings from the research video?",
                      "What technical concepts are explained in the tutorial?",
                      "Who are the speakers mentioned in the conference recording?",
                    ].map((example, index) => (
                      <button
                        key={index}
                        onClick={() => setQuery(example)}
                        className="text-left p-3 bg-white/5 hover:bg-white/10 rounded-lg border border-white/10 hover:border-white/20 transition-all duration-200 text-white/80 hover:text-white"
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}