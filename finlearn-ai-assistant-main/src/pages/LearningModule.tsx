import { useState, useEffect } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { supabase } from "@/integrations/supabase/client";
import { ChatPanel } from "@/components/ChatPanel";
import { Quiz } from "@/components/Quiz";
import { Leaderboard } from "@/components/Leaderboard";
import { 
  InflationCalculator, 
  CompoundCalculator, 
  RiskReturnChart, 
  DiversificationDemo 
} from "@/components/InteractiveElements";
import { MODULES } from "@/data/moduleContent";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  CheckCircle,
  Circle,
  Trophy,
  Users,
  Target,
  Loader2,
} from "lucide-react";

// Interactive element renderer
const InteractiveElement = ({ type }: { type: string }) => {
  switch (type) {
    case 'InflationCalculator':
      return <InflationCalculator />;
    case 'CompoundCalculator':
      return <CompoundCalculator />;
    case 'RiskReturnChart':
      return <RiskReturnChart />;
    case 'DiversificationDemo':
      return <DiversificationDemo />;
    default:
      return null;
  }
};

export default function LearningModule() {
  const navigate = useNavigate();
  const { moduleId } = useParams();
  const [currentLessonIndex, setCurrentLessonIndex] = useState(0);
  const [completedLessons, setCompletedLessons] = useState<string[]>([]);
  const [showQuiz, setShowQuiz] = useState(false);
  const [showFinalQuiz, setShowFinalQuiz] = useState(false);
  const [showLeaderboard, setShowLeaderboard] = useState(false);
  const [userId, setUserId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [quizCompleted, setQuizCompleted] = useState(false);
  const [lessonQuizScores, setLessonQuizScores] = useState<Record<string, number>>({});

  const module = moduleId ? MODULES[moduleId] : null;

  useEffect(() => {
    const init = async () => {
      const { data: { session } } = await supabase.auth.getSession();
      if (!session) {
        navigate("/");
        return;
      }
      setUserId(session.user.id);
      
      // Load user progress
      await loadProgress(session.user.id);
      setLoading(false);
    };
    init();
  }, [navigate, moduleId]);

  const loadProgress = async (uid: string) => {
    const { API_URL } = await import("@/lib/api");
    try {
      const response = await fetch(`${API_URL}/api/progress/${uid}`);
      if (response.ok) {
        const data = await response.json();
        const moduleProgress = data.progress[moduleId || ''] || {};
        setCompletedLessons(moduleProgress.completed_lessons || []);
      }
    } catch (err) {
      console.error('Failed to load progress:', err);
    }
    
    // Load quiz scores
    try {
      const response = await fetch(`${API_URL}/api/quiz/scores/${uid}`);
      if (response.ok) {
        const data = await response.json();
        const scores: Record<string, number> = {};
        for (const score of data.lesson_scores) {
          if (score.module_id === moduleId) {
            scores[score.lesson_id] = score.best_score;
          }
        }
        setLessonQuizScores(scores);
      }
    } catch (err) {
      console.error('Failed to load quiz scores:', err);
    }
  };

  const saveProgress = async (lessonId: string) => {
    if (!userId || !moduleId) return;
    
    const { API_URL: progressUrl } = await import("@/lib/api");
    try {
      await fetch(`${progressUrl}/api/progress`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          module_id: moduleId,
          lesson_id: lessonId,
          completed: true
        })
      });
    } catch (err) {
      console.error('Failed to save progress:', err);
    }
  };

  const submitQuizScore = async (score: number, total: number, isFinal: boolean = false) => {
    if (!userId || !moduleId) return;
    
    const currentLesson = module?.lessons[currentLessonIndex];
    
    const { API_URL: quizUrl } = await import("@/lib/api");
    try {
      await fetch(`${quizUrl}/api/quiz/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: userId,
          module_id: moduleId,
          lesson_id: isFinal ? null : currentLesson?.id,
          score,
          total_questions: total,
          is_final_quiz: isFinal
        })
      });
      
      if (!isFinal && currentLesson) {
        setLessonQuizScores(prev => ({ ...prev, [currentLesson.id]: score }));
      }
    } catch (err) {
      console.error('Failed to submit quiz:', err);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Loader2 className="w-8 h-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!module) {
    return (
      <div className="min-h-screen flex items-center justify-center flex-col gap-4">
        <p className="text-xl">Module not found</p>
        <button
          onClick={() => navigate("/dashboard")}
          className="px-4 py-2 bg-primary text-primary-foreground rounded-lg"
        >
          Back to Dashboard
        </button>
      </div>
    );
  }

  const currentLesson = module.lessons[currentLessonIndex];
  const allLessonsComplete = module.lessons.every(l => completedLessons.includes(l.id));

  const handleLessonComplete = async () => {
    if (!completedLessons.includes(currentLesson.id)) {
      setCompletedLessons([...completedLessons, currentLesson.id]);
      await saveProgress(currentLesson.id);
    }
    
    // Show quiz if lesson has one
    if (currentLesson.quiz && currentLesson.quiz.length > 0 && !quizCompleted) {
      setShowQuiz(true);
    } else if (currentLessonIndex < module.lessons.length - 1) {
      setCurrentLessonIndex(currentLessonIndex + 1);
      setQuizCompleted(false);
    }
  };

  const handleQuizComplete = async (score: number, total: number) => {
    await submitQuizScore(score, total, false);
    setQuizCompleted(true);
    setShowQuiz(false);
    
    // Move to next lesson after quiz
    if (currentLessonIndex < module.lessons.length - 1) {
      setTimeout(() => {
        setCurrentLessonIndex(currentLessonIndex + 1);
        setQuizCompleted(false);
      }, 1500);
    }
  };

  const handleFinalQuizComplete = async (score: number, total: number) => {
    await submitQuizScore(score, total, true);
    setShowLeaderboard(true);
  };

  // Simple markdown renderer
  const renderContent = (content: string) => {
    return content.split("\n").map((line, i) => {
      const trimmed = line.trim();
      
      if (trimmed.startsWith("## ")) {
        return <h2 key={i} className="text-2xl font-bold mt-8 mb-4 text-foreground">{trimmed.replace("## ", "")}</h2>;
      }
      if (trimmed.startsWith("### ")) {
        return <h3 key={i} className="text-xl font-semibold mt-6 mb-3 text-foreground">{trimmed.replace("### ", "")}</h3>;
      }
      if (trimmed.startsWith("---")) {
        return <hr key={i} className="my-6 border-border" />;
      }
      if (trimmed.startsWith("- ")) {
        return <li key={i} className="ml-6 text-muted-foreground list-disc">{renderInlineFormatting(trimmed.replace("- ", ""))}</li>;
      }
      if (trimmed.match(/^\d+\./)) {
        return <li key={i} className="ml-6 text-muted-foreground list-decimal">{renderInlineFormatting(trimmed.replace(/^\d+\.\s*/, ""))}</li>;
      }
      if (trimmed) {
        return (
          <p key={i} className="text-muted-foreground leading-relaxed my-2">
            {renderInlineFormatting(trimmed)}
          </p>
        );
      }
      return null;
    });
  };

  const renderInlineFormatting = (text: string) => {
    // Handle bold text
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, j) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return <strong key={j} className="text-foreground">{part.replace(/\*\*/g, "")}</strong>;
      }
      return part;
    });
  };

  // Final Quiz View
  if (showFinalQuiz) {
    return (
      <div className="min-h-screen bg-background">
        <header className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur-md">
          <div className="max-w-4xl mx-auto px-6 h-14 flex items-center justify-between">
            <button
              onClick={() => setShowFinalQuiz(false)}
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="w-4 h-4" />
              Back to Module
            </button>
            <div className="flex items-center gap-2">
              <Trophy className="w-5 h-5 text-primary" />
              <span className="font-semibold">{module.title} - Final Quiz</span>
            </div>
          </div>
        </header>
        
        <div className="max-w-2xl mx-auto px-6 py-8">
          {showLeaderboard ? (
            <div className="space-y-6">
              <div className="text-center mb-8">
                <Trophy className="w-16 h-16 text-primary mx-auto mb-4" />
                <h2 className="text-2xl font-bold">Module Complete!</h2>
                <p className="text-muted-foreground">See how you compare to other learners</p>
              </div>
              <Leaderboard moduleId={moduleId} currentUserId={userId || undefined} />
              <button
                onClick={() => navigate("/dashboard")}
                className="w-full py-3 bg-primary text-primary-foreground rounded-lg font-medium"
              >
                Back to Dashboard
              </button>
            </div>
          ) : (
            <Quiz
              questions={module.finalQuiz}
              onComplete={handleFinalQuizComplete}
              title="Module Final Quiz"
              allowRetake={true}
            />
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      {/* Main Content */}
      <div className="flex-1 overflow-y-auto">
        {/* Header */}
        <header className="sticky top-0 z-10 border-b border-border bg-background/80 backdrop-blur-md">
          <div className="max-w-4xl mx-auto px-6 h-14 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={() => navigate("/dashboard")}
                className="p-2 rounded-lg hover:bg-muted transition-colors"
              >
                <ArrowLeft className="w-4 h-4" />
              </button>
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-primary/10">
                  <BookOpen className="w-4 h-4 text-primary" />
                </div>
                <span className="font-display text-sm font-semibold">{module.title}</span>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <button
                onClick={() => setShowLeaderboard(!showLeaderboard)}
                className="p-2 rounded-lg hover:bg-muted transition-colors"
                title="Leaderboard"
              >
                <Users className="w-4 h-4" />
              </button>
              <span className="text-sm text-muted-foreground">
                {completedLessons.length}/{module.lessons.length} complete
              </span>
            </div>
          </div>
        </header>

        <div className="max-w-4xl mx-auto px-6 py-8">
          {/* Module Goal Banner */}
          {module.goal && currentLessonIndex === 0 && completedLessons.length === 0 && (
            <div className="mb-6 p-4 rounded-xl bg-gradient-to-r from-primary/10 to-transparent border border-primary/20">
              <div className="flex items-center gap-3">
                <Target className="w-5 h-5 text-primary" />
                <div>
                  <span className="text-sm font-semibold text-primary">Your Goal for This Module</span>
                  <p className="text-foreground">{module.goal}</p>
                </div>
              </div>
            </div>
          )}

          {/* Progress bar */}
          <div className="mb-6">
            <div className="flex justify-between text-sm mb-2">
              <span className="text-muted-foreground">Progress</span>
              <span className="text-primary font-medium">
                {Math.round((completedLessons.length / module.lessons.length) * 100)}%
              </span>
            </div>
            <div className="h-2 bg-muted rounded-full">
              <div 
                className="h-2 bg-primary rounded-full transition-all"
                style={{ width: `${(completedLessons.length / module.lessons.length) * 100}%` }}
              />
            </div>
          </div>

          {/* Lesson Navigation */}
          <div className="flex gap-2 mb-8 overflow-x-auto pb-2">
            {module.lessons.map((lesson, index) => {
              const isComplete = completedLessons.includes(lesson.id);
              const hasQuizScore = lessonQuizScores[lesson.id] !== undefined;
              
              return (
                <button
                  key={lesson.id}
                  onClick={() => {
                    setCurrentLessonIndex(index);
                    setShowQuiz(false);
                    setQuizCompleted(false);
                  }}
                  className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm whitespace-nowrap transition-colors ${
                    index === currentLessonIndex
                      ? "bg-primary text-primary-foreground"
                      : isComplete
                      ? "bg-green-500/20 text-green-400 border border-green-500/30"
                      : "bg-muted hover:bg-muted/80"
                  }`}
                >
                  {isComplete ? (
                    <CheckCircle className="w-4 h-4" />
                  ) : (
                    <Circle className="w-4 h-4" />
                  )}
                  <span>{lesson.title}</span>
                  {hasQuizScore && (
                    <span className="text-xs bg-primary/20 px-1.5 py-0.5 rounded">
                      {lessonQuizScores[lesson.id]}pts
                    </span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Leaderboard Sidebar */}
          {showLeaderboard && (
            <div className="mb-8 p-4 bg-muted/50 rounded-xl border border-border">
              <Leaderboard moduleId={moduleId} currentUserId={userId || undefined} />
            </div>
          )}

          {/* Quiz View */}
          {showQuiz && currentLesson.quiz ? (
            <Quiz
              questions={currentLesson.quiz}
              onComplete={handleQuizComplete}
              title={`${currentLesson.title} Quiz`}
              allowRetake={true}
            />
          ) : (
            <>
              {/* Lesson Content */}
              <div className="glass-card rounded-xl p-8 mb-8">
                <div className="flex items-center gap-2 mb-2">
                  <span className="text-xs px-2 py-1 bg-primary/20 text-primary rounded">
                    Lesson {currentLessonIndex + 1}
                  </span>
                  {completedLessons.includes(currentLesson.id) && (
                    <span className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" /> Completed
                    </span>
                  )}
                </div>
                <h1 className="font-display text-3xl font-bold mb-6">{currentLesson.title}</h1>
                <div className="prose prose-invert max-w-none">
                  {renderContent(currentLesson.content)}
                </div>
              </div>

              {/* Interactive Elements */}
              {currentLesson.interactiveElements && currentLesson.interactiveElements.length > 0 && (
                <div className="space-y-6 mb-8">
                  <h3 className="text-lg font-semibold flex items-center gap-2">
                    <Target className="w-5 h-5 text-primary" />
                    Try It Yourself
                  </h3>
                  {currentLesson.interactiveElements.map((element, i) => (
                    <InteractiveElement key={i} type={element} />
                  ))}
                </div>
              )}

              {/* Tool Links */}
              {currentLesson.toolLinks && currentLesson.toolLinks.length > 0 && (
                <div className="mb-8 p-5 rounded-xl bg-gradient-to-r from-primary/10 to-purple-500/10 border border-primary/20">
                  <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
                    <Target className="w-5 h-5 text-primary" />
                    See It In Action
                  </h3>
                  <div className="space-y-3">
                    {currentLesson.toolLinks.map((link, i) => (
                      <button
                        key={i}
                        onClick={() => navigate(link.route)}
                        className="w-full text-left p-4 rounded-lg bg-background/50 hover:bg-background/80 border border-border/50 hover:border-primary/40 transition-all group"
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-semibold text-primary group-hover:text-primary/80">
                            {link.text} →
                          </span>
                        </div>
                        <p className="text-sm text-muted-foreground mt-1">{link.description}</p>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Goal Reminder */}
              {currentLesson.goalReminder && (
                <div className="mb-8 p-4 rounded-xl bg-success/10 border border-success/30">
                  <div className="flex items-start gap-3">
                    <CheckCircle className="w-5 h-5 text-success mt-0.5" />
                    <div>
                      <span className="text-sm font-semibold text-success">Your Progress</span>
                      <p className="text-sm text-foreground mt-1">{currentLesson.goalReminder}</p>
                    </div>
                  </div>
                </div>
              )}

              {/* Module Goal Reminder (at end of module) */}
              {currentLessonIndex === module.lessons.length - 1 && module.goal && (
                <div className="mb-8 p-5 rounded-xl bg-gradient-to-r from-primary/10 to-success/10 border border-primary/30">
                  <div className="flex items-start gap-3">
                    <Trophy className="w-6 h-6 text-primary mt-0.5" />
                    <div>
                      <span className="font-semibold text-primary">Module Goal Achieved</span>
                      <p className="text-foreground mt-1">{module.goal}</p>
                      <p className="text-sm text-muted-foreground mt-2">
                        Complete the final quiz to test your knowledge and see how you compare!
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Navigation Buttons */}
              <div className="flex justify-between items-center">
                <button
                  onClick={() => {
                    setCurrentLessonIndex(Math.max(0, currentLessonIndex - 1));
                    setQuizCompleted(false);
                  }}
                  disabled={currentLessonIndex === 0}
                  className="flex items-center gap-2 px-4 py-2 bg-muted rounded-lg text-sm hover:bg-muted/80 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ArrowLeft className="w-4 h-4" />
                  Previous
                </button>
                
                <div className="flex gap-3">
                  {/* Show Take Quiz button if lesson has quiz */}
                  {currentLesson.quiz && currentLesson.quiz.length > 0 && !quizCompleted && (
                    <button
                      onClick={() => setShowQuiz(true)}
                      className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg text-sm hover:opacity-90"
                    >
                      <Trophy className="w-4 h-4" />
                      Take Quiz
                    </button>
                  )}
                  
                  {currentLessonIndex === module.lessons.length - 1 ? (
                    allLessonsComplete ? (
                      <button
                        onClick={() => setShowFinalQuiz(true)}
                        className="flex items-center gap-2 px-6 py-2 bg-gradient-to-r from-primary to-purple-600 text-white rounded-lg text-sm hover:opacity-90"
                      >
                        <Trophy className="w-4 h-4" />
                        Take Final Quiz
                      </button>
                    ) : (
                      <button
                        onClick={handleLessonComplete}
                        className="flex items-center gap-2 px-6 py-2 bg-primary text-primary-foreground rounded-lg text-sm hover:opacity-90"
                      >
                        <CheckCircle className="w-4 h-4" />
                        Complete Module
                      </button>
                    )
                  ) : (
                    <button
                      onClick={handleLessonComplete}
                      className="flex items-center gap-2 px-6 py-2 bg-primary text-primary-foreground rounded-lg text-sm hover:opacity-90"
                    >
                      {completedLessons.includes(currentLesson.id) ? 'Next Lesson' : 'Mark Complete'}
                      <ArrowRight className="w-4 h-4" />
                    </button>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* AI Chat Panel - open by default in learning modules */}
      <div className="hidden lg:flex w-[380px] flex-shrink-0 h-screen sticky top-0">
        <ChatPanel defaultOpen={true} />
      </div>
    </div>
  );
}
