import { useNavigate } from "react-router-dom";
import { BookOpen, Search, Settings, ArrowRight } from "lucide-react";

const topics = [
  {
    id: "foundations",
    icon: BookOpen,
    title: "The Foundation",
    description: "Everything you need to understand before investing your first dollar.",
    level: "Beginner",
    lessons: 7,
  },
  {
    id: "investor-insight",
    icon: Search,
    title: "Investor Insight",
    description: "Learn why markets move and how to avoid psychological traps.",
    level: "Intermediate",
    lessons: 6,
  },
  {
    id: "applied-investing",
    icon: Settings,
    title: "Applied Investing",
    description: "Build your actual portfolio with asset allocation strategies.",
    level: "Advanced",
    lessons: 6,
  },
];

const levelColors: Record<string, string> = {
  Beginner: "bg-success/20 text-success",
  Intermediate: "bg-info/20 text-info",
  Advanced: "bg-primary/20 text-primary",
};

export function LessonGrid() {
  const navigate = useNavigate();

  const handleTopicClick = (topicId: string) => {
    navigate(`/learn/${topicId}`);
  };

  return (
    <section className="py-8">
      <h2 className="font-display text-2xl font-bold mb-6">Learning Modules</h2>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {topics.map((topic) => {
          const Icon = topic.icon;
          return (
            <div
              key={topic.id}
              onClick={() => handleTopicClick(topic.id)}
              className="glass-card rounded-xl p-6 hover:border-primary/40 transition-all duration-300 cursor-pointer group"
            >
              <div className="p-2.5 rounded-lg bg-primary/10 text-primary w-fit mb-4 group-hover:glow-gold transition-all">
                <Icon className="w-5 h-5" />
              </div>
              
              <div className="flex items-center gap-2 mb-2">
                <h3 className="font-display text-lg font-semibold group-hover:text-primary transition-colors">
                  {topic.title}
                </h3>
              </div>
              
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${levelColors[topic.level]} inline-block mb-3`}>
                {topic.level}
              </span>
              
              <p className="text-sm text-muted-foreground mb-4 leading-relaxed">
                {topic.description}
              </p>

              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>{topic.lessons} lessons</span>
                <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform text-primary" />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
