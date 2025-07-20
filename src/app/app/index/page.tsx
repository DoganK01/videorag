"use client"

import React from "react"
import { useState, useEffect, useRef, useCallback } from "react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Upload, ArrowLeft, Play, CheckCircle, AlertCircle, Loader2, FolderOpen, File } from "lucide-react"
import Link from "next/link"

// This interface now matches the backend's JobStatus Pydantic model
interface JobStatus {
  id: string;
  status: "pending" | "processing" | "completed" | "error";
  progress: number;
  error?: string | null;
}

// We extend the backend interface with frontend-specific fields for display
interface IndexingJob extends JobStatus {
  videoPath: string;
  startTime: Date;
  endTime?: Date;
}

export default function IndexPage() {
  const [videoPath, setVideoPath] = useState("")
  const [jobs, setJobs] = useState<IndexingJob[]>([])
  // A ref to store active interval IDs to manage them properly
  const pollingIntervals = useRef<Record<string, NodeJS.Timeout>>({});

  // --- REAL API INTEGRATION FOR JOB SUBMISSION ---
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!videoPath.trim()) return

    const tempId = `temp_${Date.now()}`
    const newJob: IndexingJob = {
      id: tempId,
      videoPath: videoPath.trim(),
      status: "pending",
      progress: 0,
      startTime: new Date(),
    }
    setJobs((prev) => [newJob, ...prev])
    setVideoPath("")

    try {
      const res = await fetch("/api/v1/indexing/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ video_path: videoPath.trim() }),
      });

      const responseData = await res.json();
      if (!res.ok) {
        throw new Error(responseData.detail || "Failed to start indexing job on the server.");
      }

      const { job_id } = responseData;
      
      // Update the temporary job with the real ID from the backend
      setJobs((prev) => 
        prev.map((job) => 
          job.id === tempId ? { ...job, id: job_id, status: "processing" } : job
        )
      );

    } catch (error) {
      // If starting the job fails, update the UI to show the error
      setJobs((prev) =>
        prev.map((job) =>
          job.id === tempId
            ? { ...job, status: "error", error: error instanceof Error ? error.message : "An unknown error occurred", endTime: new Date() }
            : job,
        ),
      )
    }
  }

  // --- ROBUST LIVE STATUS POLLING ---
  const pollJobStatus = useCallback(async (jobId: string) => {
    try {
      const res = await fetch(`/api/v1/indexing/status/${jobId}`);
      if (!res.ok) {
        // If the job is not found (e.g., expired), treat it as an error
        if (res.status === 404) {
          throw new Error("Job status not found. It may have expired or failed to start.");
        }
        throw new Error("Failed to fetch job status.");
      }
      
      const statusData: JobStatus = await res.json();
      
      setJobs((prevJobs) =>
        prevJobs.map((j) => {
          if (j.id === statusData.id) {
            const isFinished = statusData.status === "completed" || statusData.status === "error";
            if (isFinished && pollingIntervals.current[jobId]) {
              clearInterval(pollingIntervals.current[jobId]);
              delete pollingIntervals.current[jobId];
            }
            return { ...j, ...statusData, endTime: isFinished ? new Date() : undefined };
          }
          return j;
        })
      );
    } catch (e) {
      console.error(`Failed to poll status for job ${jobId}`, e);
      // Update the job with an error state if polling fails
      setJobs(prev => prev.map(j => j.id === jobId ? {...j, status: "error", error: e instanceof Error ? e.message : "Polling failed"} : j));
      if (pollingIntervals.current[jobId]) {
        clearInterval(pollingIntervals.current[jobId]);
        delete pollingIntervals.current[jobId];
      }
    }
  }, []);

  useEffect(() => {
    // Identify jobs that need polling
    const activeJobs = jobs.filter(
      (job) => (job.status === "processing" || job.status === "pending") && !pollingIntervals.current[job.id]
    );

    activeJobs.forEach((job) => {
      // Start polling for each new active job
      pollingIntervals.current[job.id] = setInterval(() => {
        pollJobStatus(job.id);
      }, 3000); // Poll every 3 seconds
    });

    // Cleanup function to clear all intervals when the component unmounts
    return () => {
      Object.values(pollingIntervals.current).forEach(clearInterval);
    };
  }, [jobs, pollJobStatus]);


  // --- UI RENDERING LOGIC (NO CHANGES NEEDED IN JSX) ---

  const getStatusIcon = (status: IndexingJob["status"]) => {
    switch (status) {
        case "pending": return <Loader2 className="w-4 h-4 text-yellow-400 animate-spin" />
        case "processing": return <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />
        case "completed": return <CheckCircle className="w-4 h-4 text-green-400" />
        case "error": return <AlertCircle className="w-4 h-4 text-red-400" />
    }
  }

  const getStatusColor = (status: IndexingJob["status"]) => {
    switch (status) {
        case "pending": return "bg-yellow-500/20 text-yellow-300 border-yellow-500/30"
        case "processing": return "bg-blue-500/20 text-blue-300 border-blue-500/30"
        case "completed": return "bg-green-500/20 text-green-300 border-green-500/30"
        case "error": return "bg-red-500/20 text-red-300 border-red-500/30"
    }
  }

  // The 'isIndexing' state is now derived from the jobs list for robustness
  const isAnyJobActive = jobs.some(job => job.status === 'pending' || job.status === 'processing');

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute top-20 right-20 w-64 h-64 bg-purple-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse"></div>
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
              <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-pink-600 rounded-lg flex items-center justify-center">
                <Upload className="w-4 h-4 text-white" />
              </div>
              <span className="text-xl font-bold text-white">Video Indexing</span>
            </div>
          </nav>
        </header>

        <div className="container mx-auto px-6 py-12">
          <div className="max-w-4xl mx-auto">
            {/* Indexing Form: `disabled` logic is now more robust */}
            <Card className="bg-white/10 backdrop-blur-sm border-white/20 mb-8">
              <CardHeader>
                <CardTitle className="text-2xl text-white flex items-center space-x-2">
                  <Upload className="w-6 h-6 text-purple-400" />
                  <span>Index New Video</span>
                </CardTitle>
                <CardDescription className="text-white/70">
                  Provide the path to your video file or directory to start indexing
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-6">
                  <div className="space-y-2">
                    <Label htmlFor="videoPath" className="text-white font-medium">
                      Video Path
                    </Label>
                    <div className="relative">
                      <FolderOpen className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-white/50" />
                      <Input
                        id="videoPath"
                        type="text"
                        placeholder="/path/to/video.mp4 or /path/to/video/directory"
                        value={videoPath}
                        onChange={(e) => setVideoPath(e.target.value)}
                        className="pl-12 bg-white/5 border-white/20 text-white placeholder:text-white/50 focus:border-purple-400 focus:ring-purple-400/20"
                        disabled={isAnyJobActive}
                      />
                    </div>
                    <p className="text-sm text-white/60">Supported formats: MP4, MKV, MOV, AVI</p>
                  </div>
                  <Button
                    type="submit"
                    disabled={!videoPath.trim() || isAnyJobActive}
                    variant="gradient-secondary"
                    className="w-full py-3 rounded-xl font-semibold"
                  >
                    {isAnyJobActive ? (
                      <>
                        <Loader2 className="w-5 h-5 mr-2 animate-spin" />
                        Indexing in Progress...
                      </>
                    ) : (
                      <>
                        <Play className="w-5 h-5 mr-2" />
                        Start Indexing
                      </>
                    )}
                  </Button>
                </form>
              </CardContent>
            </Card>

            {/* Indexing Jobs */}
            {jobs.length > 0 && (
              <Card className="bg-white/10 backdrop-blur-sm border-white/20">
                <CardHeader>
                  <CardTitle className="text-xl text-white flex items-center space-x-2">
                    <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-lg flex items-center justify-center">
                      <File className="w-4 h-4 text-white" />
                    </div>
                    <span>Indexing Jobs</span>
                  </CardTitle>
                  <CardDescription className="text-white/70">
                    Track the progress of your video indexing operations
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {jobs.map((job) => (
                      <div key={job.id} className="bg-white/5 rounded-xl p-4 border border-white/10">
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center space-x-2 mb-1">
                              {getStatusIcon(job.status)}
                              <span className="text-white font-medium truncate">{job.videoPath}</span>
                            </div>
                            <div className="flex items-center space-x-2 text-sm text-white/60">
                              <span>Started: {job.startTime.toLocaleTimeString()}</span>
                              {job.endTime && <span>• Completed: {job.endTime.toLocaleTimeString()}</span>}
                            </div>
                          </div>
                          <Badge variant={job.status}>
                            {job.status.charAt(0).toUpperCase() + job.status.slice(1)}
                          </Badge>
                        </div>

                        {job.status === "processing" && (
                          <div className="space-y-2">
                            <div className="flex justify-between text-sm">
                              <span className="text-white/70">Progress</span>
                              <span className="text-white/70">{job.progress}%</span>
                            </div>
                            <Progress value={job.progress} className="h-2 bg-white/10" />
                          </div>
                        )}

                        {job.status === "error" && job.error && (
                          <div className="mt-2 p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                            <p className="text-red-400 text-sm">{job.error}</p>
                          </div>
                        )}

                        {job.status === "completed" && (
                          <div className="mt-2 p-3 bg-green-500/10 border border-green-500/20 rounded-lg">
                            <p className="text-green-400 text-sm">Video successfully indexed and ready for querying</p>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Instructions */}
            {jobs.length === 0 && (
              <Card className="bg-white/5 backdrop-blur-sm border-white/10">
                <CardHeader>
                  <CardTitle className="text-lg text-white">How It Works</CardTitle>
                  <CardDescription className="text-white/70">Understanding the video indexing process</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="flex items-start space-x-3">
                      <div className="w-8 h-8 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white font-bold text-sm">
                        1
                      </div>
                      <div>
                        <h4 className="text-white font-medium">Video Processing</h4>
                        <p className="text-white/70 text-sm">
                          The system extracts audio, generates transcripts, and analyzes visual content
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start space-x-3">
                      <div className="w-8 h-8 bg-gradient-to-r from-purple-500 to-pink-500 rounded-full flex items-center justify-center text-white font-bold text-sm">
                        2
                      </div>
                      <div>
                        <h4 className="text-white font-medium">Content Analysis</h4>
                        <p className="text-white/70 text-sm">
                          AI models analyze the content to understand context and meaning
                        </p>
                      </div>
                    </div>
                    <div className="flex items-start space-x-3">
                      <div className="w-8 h-8 bg-gradient-to-r from-pink-500 to-red-500 rounded-full flex items-center justify-center text-white font-bold text-sm">
                        3
                      </div>
                      <div>
                        <h4 className="text-white font-medium">Vector Storage</h4>
                        <p className="text-white/70 text-sm">
                          Content is converted to embeddings and stored for fast retrieval
                        </p>
                      </div>
                    </div>
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