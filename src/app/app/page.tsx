"use client"

import React, { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Search, Upload, Database, Sparkles, Video, Brain, Zap } from "lucide-react"
import Link from "next/link"

export default function HomePage() {
  const [hoveredCard, setHoveredCard] = useState<number | null>(null)

  const features = [
    {
      icon: Search,
      title: "Intelligent Query",
      description: "Ask questions about your video content and get precise, context-aware answers",
      href: "/query",
      gradient: "from-blue-500 to-purple-600",
    },
    {
      icon: Upload,
      title: "Video Indexing",
      description: "Upload and index your videos for intelligent search and retrieval",
      href: "/index",
      gradient: "from-purple-500 to-pink-600",
    },
    {
      icon: Database,
      title: "Knowledge Base",
      description: "Manage your indexed video library and explore your content",
      href: "/library",
      gradient: "from-indigo-500 to-blue-600",
    },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Animated background elements */}
      <div className="absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-blue-500 rounded-full mix-blend-multiply filter blur-xl opacity-20 animate-pulse delay-1000"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-80 h-80 bg-indigo-500 rounded-full mix-blend-multiply filter blur-xl opacity-10 animate-pulse delay-500"></div>
      </div>

      <div className="relative z-10">
        {/* Header */}
        <header className="container mx-auto px-6 py-8">
          <nav className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                <Video className="w-6 h-6 text-white" />
              </div>
              <span className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                VideoRAG
              </span>
            </div>
            <div className="flex items-center space-x-4">
              <Button variant="ghost" className="text-white hover:text-blue-300 transition-colors">
                Documentation
              </Button>
              <Button variant="ghost" className="text-white hover:text-purple-300 transition-colors">
                API
              </Button>
            </div>
          </nav>
        </header>

        {/* Hero Section */}
        <section className="container mx-auto px-6 py-20 text-center">
          <div className="max-w-4xl mx-auto">
            <div className="inline-flex items-center space-x-2 bg-white/10 backdrop-blur-sm rounded-full px-4 py-2 mb-8 border border-white/20">
              <Sparkles className="w-4 h-4 text-yellow-400" />
              <span className="text-sm text-white/90">Powered by Advanced AI</span>
            </div>

            <h1 className="text-6xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-white via-blue-100 to-purple-100 bg-clip-text text-transparent leading-tight">
              Intelligent Video
              <br />
              <span className="bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                Understanding
              </span>
            </h1>

            <p className="text-xl text-white/80 mb-12 max-w-2xl mx-auto leading-relaxed">
              Transform your video content into an intelligent knowledge base. Ask questions, get answers, and unlock
              insights from your video library with cutting-edge AI.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Link href="/query" passHref>
                <Button
                  size="lg"
                  variant="gradient-primary"
                  className="px-8 py-4 rounded-xl font-semibold"
                >
                  <Search className="w-5 h-5 mr-2" />
                  Start Querying
                </Button>
              </Link>
              <Link href="/index" passHref>
                <Button
                  size="lg"
                  variant="outline"
                  className="border-white/30 text-white hover:bg-white/10 px-8 py-4 rounded-xl font-semibold transition-all duration-300 backdrop-blur-sm bg-transparent"
                >
                  <Upload className="w-5 h-5 mr-2" />
                  Index Videos
                </Button>
              </Link>
            </div>
          </div>
        </section>

        {/* Features Section */}
        <section className="container mx-auto px-6 py-20">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-white mb-4">Powerful Features</h2>
            <p className="text-xl text-white/70 max-w-2xl mx-auto">
              Everything you need to build intelligent video applications
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto">
            {features.map((feature, index) => (
              <Link key={index} href={feature.href}>
                <Card
                  className="bg-white/10 backdrop-blur-sm border-white/20 hover:bg-white/15 transition-all duration-500 transform hover:scale-105 hover:shadow-2xl cursor-pointer group"
                  onMouseEnter={() => setHoveredCard(index)}
                  onMouseLeave={() => setHoveredCard(null)}
                >
                  <CardHeader className="text-center pb-4">
                    <div
                      className={`w-16 h-16 mx-auto mb-4 bg-gradient-to-r ${feature.gradient} rounded-2xl flex items-center justify-center transform transition-transform duration-300 ${hoveredCard === index ? "rotate-6 scale-110" : ""}`}
                    >
                      <feature.icon className="w-8 h-8 text-white" />
                    </div>
                    <CardTitle className="text-xl text-white group-hover:text-blue-300 transition-colors">
                      {feature.title}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="text-white/70 text-center leading-relaxed">
                      {feature.description}
                    </CardDescription>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </section>

        {/* Stats Section */}
        <section className="container mx-auto px-6 py-20">
          <div className="bg-white/5 backdrop-blur-sm rounded-3xl border border-white/10 p-12">
            <div className="grid md:grid-cols-3 gap-8 text-center">
              <div className="space-y-2">
                <div className="flex items-center justify-center space-x-2">
                  <Brain className="w-8 h-8 text-blue-400" />
                  <span className="text-4xl font-bold text-white">AI-Powered</span>
                </div>
                <p className="text-white/70">Advanced multimodal understanding</p>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-center space-x-2">
                  <Zap className="w-8 h-8 text-purple-400" />
                  <span className="text-4xl font-bold text-white">Lightning Fast</span>
                </div>
                <p className="text-white/70">Optimized vector search</p>
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-center space-x-2">
                  <Database className="w-8 h-8 text-indigo-400" />
                  <span className="text-4xl font-bold text-white">Scalable</span>
                </div>
                <p className="text-white/70">Handle massive video libraries</p>
              </div>
            </div>
          </div>
        </section>

        {/* Footer */}
        <footer className="container mx-auto px-6 py-12 text-center">
          <div className="border-t border-white/10 pt-8">
            <p className="text-white/50">© 2024 VideoRAG. Built with cutting-edge AI technology.</p>
          </div>
        </footer>
      </div>
    </div>
  )
}
