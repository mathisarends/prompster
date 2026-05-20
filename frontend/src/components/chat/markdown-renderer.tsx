import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { vscDarkPlus } from "react-syntax-highlighter/dist/esm/styles/prism";
import type { Components } from "react-markdown";
import { cn } from "@/lib/utils";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

const markdownComponents: Components = {
  code({ className, children, ...props }) {
    const match = /language-(\w+)/.exec(className ?? "");

    if (!match) {
      return (
        <code className={className} {...props}>
          {children}
        </code>
      );
    }

    return (
      <div className="relative mt-4 overflow-hidden rounded-xl border border-border bg-black/90">
        {match && (
          <div className="flex w-full items-center bg-white/10 px-4 py-1 text-xs text-muted-foreground">
            <span>{match[1]}</span>
          </div>
        )}
        <SyntaxHighlighter
          style={vscDarkPlus}
          language={match ? match[1] : "text"}
          PreTag="div"
          className="!m-0 !bg-transparent !p-4"
          {...(props as object)}
        >
          {String(children).replace(/\n$/, "")}
        </SyntaxHighlighter>
      </div>
    );
  },
};

export const MarkdownRenderer = ({
  content,
  className,
}: MarkdownRendererProps) => {
  return (
    <div
      className={cn(
        "prose prose-sm prose-invert max-w-none break-words",
        className,
      )}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={markdownComponents}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
