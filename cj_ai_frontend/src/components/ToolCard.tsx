// src/components/ToolCard.tsx
import { Card, CardContent } from "@/components/ui/card";
import type { LucideIcon } from "lucide-react";

interface ToolCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
}

export const ToolCard = ({ icon: Icon, title, description }: ToolCardProps) => {
  return (
    <Card
      className="group flex h-full min-h-[120px] cursor-pointer border border-border bg-card
                 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-card-hover"
    >
      {/* 카드 전체를 flex로 만들고, 안에서 가운데 정렬 */}
      <CardContent className="flex flex-1 items-center p-6">
        <div className="flex w-full items-center gap-4">
          <div className="shrink-0 rounded-lg bg-primary-lighter p-3 transition-colors group-hover:bg-primary/10">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <div className="space-y-1.5">
            <h3 className="font-semibold text-foreground transition-colors group-hover:text-primary">
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
