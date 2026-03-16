import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import Dashboard from "./pages/Dashboard";
import StockScreener from "./pages/StockScreener";
import ChartAnalyzer from "./pages/ChartAnalyzer";
import SentimentAnalyzer from "./pages/SentimentAnalyzer";
import LearningModule from "./pages/LearningModule";
import Simulator from "./pages/Simulator";
import Leaderboard from "./pages/Leaderboard";
import Social from "./pages/Social";
import Messages from "./pages/Messages";
import ETFRecommender from "./pages/ETFRecommender";
import ETFAllocator from "./pages/ETFAllocator";
import AIStockDiscovery from "./pages/AIStockDiscovery";
import NotFound from "./pages/NotFound";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/screener" element={<StockScreener />} />
          <Route path="/analyzer" element={<ChartAnalyzer />} />
          <Route path="/sentiment" element={<SentimentAnalyzer />} />
          <Route path="/learn/:moduleId" element={<LearningModule />} />
          <Route path="/simulator" element={<Simulator />} />
          <Route path="/leaderboard" element={<Leaderboard />} />
          <Route path="/social" element={<Social />} />
          <Route path="/messages" element={<Messages />} />
          <Route path="/etf-recommender" element={<ETFRecommender />} />
          <Route path="/etf-allocator" element={<ETFAllocator />} />
          <Route path="/ai-discovery" element={<AIStockDiscovery />} />
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
