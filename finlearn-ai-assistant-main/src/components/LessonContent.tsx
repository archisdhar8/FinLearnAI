import type { ReactNode } from "react";

/**
 * Renders lesson body strings from moduleContent.ts.
 * Supports: ## / ### headings, ---, markdown tables, blockquotes (>), bullet and numbered lists, paragraphs, **bold**.
 */

function renderInline(text: string, keyPrefix: string): ReactNode {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, j) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={`${keyPrefix}-${j}`} className="text-foreground font-semibold">
          {part.replace(/\*\*/g, "")}
        </strong>
      );
    }
    return part;
  });
}

function parseTableRow(line: string): string[] {
  const t = line.trim();
  if (!t.includes("|")) return [];
  let inner = t.startsWith("|") ? t.slice(1) : t;
  inner = inner.endsWith("|") ? inner.slice(0, -1) : inner;
  return inner.split("|").map((c) => c.trim());
}

function isTableSeparator(line: string): boolean {
  const cells = parseTableRow(line).filter((c) => c !== "");
  return cells.length > 0 && cells.every((c) => /^-+:?$/.test(c.replace(/\s/g, "")));
}

function parseTableRows(tableLines: string[]): { headers: string[]; rows: string[][] } | null {
  const body: string[][] = [];
  for (const line of tableLines) {
    if (isTableSeparator(line)) continue;
    const cells = parseTableRow(line);
    if (cells.some((c) => c.length > 0)) body.push(cells);
  }
  if (body.length < 1) return null;
  return { headers: body[0], rows: body.slice(1) };
}

export function LessonContent({ content }: { content: string }) {
  const lines = content.split("\n");
  const nodes: ReactNode[] = [];
  let i = 0;
  let blockKey = 0;

  const nextKey = () => `lb-${blockKey++}`;

  while (i < lines.length) {
    const raw = lines[i];
    const trimmed = raw.trim();

    if (!trimmed) {
      i++;
      continue;
    }

    // Horizontal rule
    if (trimmed === "---") {
      nodes.push(<hr key={nextKey()} className="my-8 border-border" />);
      i++;
      continue;
    }

    // Headings
    if (trimmed.startsWith("## ")) {
      nodes.push(
        <h2 key={nextKey()} className="text-2xl font-bold mt-10 mb-4 text-foreground scroll-mt-20 first:mt-0">
          {renderInline(trimmed.slice(3), nextKey())}
        </h2>
      );
      i++;
      continue;
    }
    if (trimmed.startsWith("### ")) {
      nodes.push(
        <h3 key={nextKey()} className="text-xl font-semibold mt-8 mb-3 text-foreground">
          {renderInline(trimmed.slice(4), nextKey())}
        </h3>
      );
      i++;
      continue;
    }

    // Table (GitHub-style)
    if (trimmed.startsWith("|") && trimmed.includes("|")) {
      const tableLines: string[] = [];
      while (i < lines.length) {
        const t = lines[i].trim();
        if (!t.startsWith("|") || !t.includes("|")) break;
        tableLines.push(t);
        i++;
      }
      const parsed = parseTableRows(tableLines);
      if (parsed && parsed.headers.length > 0) {
        nodes.push(
          <div key={nextKey()} className="my-6 overflow-x-auto rounded-lg border border-border/60 bg-muted/20">
            <table className="w-full min-w-[280px] text-sm border-collapse">
              <thead>
                <tr className="border-b border-border bg-muted/40">
                  {parsed.headers.map((h, hi) => (
                    <th
                      key={hi}
                      className="px-3 py-2.5 text-left font-semibold text-foreground align-bottom"
                    >
                      {renderInline(h, `${nextKey()}-h-${hi}`)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {parsed.rows.map((row, ri) => (
                  <tr key={ri} className="border-b border-border/50 last:border-0 hover:bg-muted/30">
                    {row.map((cell, ci) => (
                      <td key={ci} className="px-3 py-2.5 text-muted-foreground align-top">
                        {renderInline(cell, `${nextKey()}-c-${ri}-${ci}`)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      }
      continue;
    }

    // Blockquote (possibly multiline)
    if (trimmed.startsWith(">")) {
      const quoteParts: string[] = [];
      while (i < lines.length) {
        const t = lines[i].trim();
        if (!t.startsWith(">")) break;
        quoteParts.push(t.replace(/^>\s?/, ""));
        i++;
      }
      nodes.push(
        <blockquote
          key={nextKey()}
          className="my-6 border-l-4 border-primary/50 pl-4 py-1 text-muted-foreground bg-primary/[0.06] rounded-r-lg pr-3"
        >
          {quoteParts.map((q, qi) => (
            <p key={qi} className="leading-relaxed my-2 first:mt-0 last:mb-0">
              {renderInline(q, `${nextKey()}-q-${qi}`)}
            </p>
          ))}
        </blockquote>
      );
      continue;
    }

    // Bullet list (group consecutive)
    if (trimmed.startsWith("- ")) {
      const items: string[] = [];
      while (i < lines.length) {
        const t = lines[i].trim();
        if (!t.startsWith("- ")) break;
        items.push(t.slice(2));
        i++;
      }
      nodes.push(
        <ul key={nextKey()} className="my-4 ml-1 space-y-2 text-muted-foreground list-none">
          {items.map((item, li) => {
            const m = item.match(/^\[([ xX])\]\s*(.*)$/);
            const k = `${nextKey()}-li-${li}`;
            if (m) {
              const done = m[1].toLowerCase() === "x";
              return (
                <li key={li} className="leading-relaxed flex gap-3 items-start">
                  <span
                    className={`mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded border text-[10px] ${
                      done ? "border-primary bg-primary/20 text-primary" : "border-muted-foreground/40"
                    }`}
                    aria-hidden
                  >
                    {done ? "✓" : ""}
                  </span>
                  <span>{renderInline(m[2], k)}</span>
                </li>
              );
            }
            return (
              <li key={li} className="leading-relaxed flex gap-2 items-start">
                <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-primary/70" aria-hidden />
                <span>{renderInline(item, k)}</span>
              </li>
            );
          })}
        </ul>
      );
      continue;
    }

    // Numbered list — line starts with digit + dot + space
    if (/^\d+\.\s/.test(trimmed)) {
      const items: string[] = [];
      while (i < lines.length) {
        const t = lines[i].trim();
        const m = t.match(/^(\d+)\.\s(.*)$/);
        if (!m) break;
        items.push(m[2]);
        i++;
      }
      nodes.push(
        <ol key={nextKey()} className="my-4 ml-5 space-y-2 list-decimal marker:text-primary text-muted-foreground">
          {items.map((item, li) => (
            <li key={li} className="leading-relaxed pl-1">
              {renderInline(item, `${nextKey()}-oli-${li}`)}
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // Paragraph (single line or block until break)
    const paraLines: string[] = [trimmed];
    i++;
    while (i < lines.length) {
      const t = lines[i].trim();
      if (
        !t ||
        t === "---" ||
        t.startsWith("## ") ||
        t.startsWith("### ") ||
        t.startsWith("|") ||
        t.startsWith(">") ||
        t.startsWith("- ") ||
        /^\d+\.\s/.test(t)
      ) {
        break;
      }
      paraLines.push(t);
      i++;
    }
    const paraText = paraLines.join(" ");
    nodes.push(
      <p key={nextKey()} className="text-muted-foreground leading-relaxed my-3 text-[15px]">
        {renderInline(paraText, nextKey())}
      </p>
    );
  }

  return (
    <div className="lesson-markdown space-y-1 max-w-none [&_h2:first-of-type]:mt-4 [&_blockquote]:text-[15px]">
      {nodes}
    </div>
  );
}
