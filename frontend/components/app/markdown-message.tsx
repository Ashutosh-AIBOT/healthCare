"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Structured chat answer renderer.
 * - Tables/lists/headings/code render as real elements (never raw pipes).
 * - Raw HTML from model output is NOT parsed (no rehype-raw) → XSS-safe.
 * - Wide tables scroll horizontally inside the bubble so 360px screens fit.
 */
export function MarkdownMessage({ content }: { content: string }) {
  return (
    <div className="text-[14px] leading-relaxed text-ink [&>*:first-child]:mt-0 [&>*:last-child]:mb-0">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p className="my-2">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
          h1: ({ children }) => <h3 className="mt-4 mb-2 text-base font-semibold">{children}</h3>,
          h2: ({ children }) => <h3 className="mt-4 mb-2 text-base font-semibold">{children}</h3>,
          h3: ({ children }) => <h4 className="mt-3 mb-1.5 text-sm font-semibold">{children}</h4>,
          h4: ({ children }) => <h4 className="mt-3 mb-1.5 text-sm font-semibold">{children}</h4>,
          ul: ({ children }) => <ul className="my-2 ml-4 list-disc space-y-1">{children}</ul>,
          ol: ({ children }) => <ol className="my-2 ml-4 list-decimal space-y-1">{children}</ol>,
          li: ({ children }) => <li className="leading-relaxed">{children}</li>,
          a: ({ children, href }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" className="text-primary underline">
              {children}
            </a>
          ),
          code: ({ children, className }) => {
            const inline = !className;
            return inline ? (
              <code className="rounded bg-mist px-1 py-0.5 text-[13px]">{children}</code>
            ) : (
              <code className="block overflow-x-auto rounded-lg bg-mist p-3 text-[13px] whitespace-pre">
                {children}
              </code>
            );
          },
          pre: ({ children }) => <pre className="my-2 overflow-x-auto">{children}</pre>,
          table: ({ children }) => (
            <div className="my-3 -mx-1 overflow-x-auto rounded-xl border border-line/60">
              <table className="w-full min-w-[480px] border-collapse text-[13px]">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-mist/70">{children}</thead>,
          th: ({ children }) => (
            <th className="border-b border-line/60 px-3 py-2 text-left font-semibold whitespace-nowrap">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="border-b border-line/40 px-3 py-2 align-top">{children}</td>
          ),
          hr: () => <hr className="my-3 border-line/60" />,
          blockquote: ({ children }) => (
            <blockquote className="my-2 border-l-2 border-primary/40 pl-3 text-ink/80">
              {children}
            </blockquote>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
