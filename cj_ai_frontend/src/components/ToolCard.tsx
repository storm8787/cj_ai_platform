import { Card, CardContent } from "@/components/ui/card";
import type { LucideIcon } from "lucide-react";
import { useNavigate } from "react-router-dom";

interface ToolCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  path?: string;
}

export const ToolCard = ({ icon: Icon, title, description, path }: ToolCardProps) => {
  const navigate = useNavigate();

  const handleClick = () => {
    if (path) {
      navigate(path);
    }
  };

  return (
    <Card
      className={`group flex h-full min-h-[120px] border border-border bg-card
                 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-card-hover
                 ${path ? 'cursor-pointer' : 'cursor-not-allowed opacity-60'}`}
      onClick={handleClick}
    >
      <CardContent className="flex flex-1 items-center p-6">
        <div className="flex w-full items-center gap-4">
          <div className={`shrink-0 rounded-lg p-3 transition-colors
                          ${path ? 'bg-primary-lighter group-hover:bg-primary/10' : 'bg-muted'}`}>
            <Icon className={`h-5 w-5 ${path ? 'text-primary' : 'text-muted-foreground'}`} />
          </div>
          <div className="space-y-1.5">
            <h3 className={`font-semibold transition-colors
                           ${path ? 'text-foreground group-hover:text-primary' : 'text-muted-foreground'}`}>
              {title}
            </h3>
            <p className="text-sm leading-relaxed text-muted-foreground">
              {description}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
};