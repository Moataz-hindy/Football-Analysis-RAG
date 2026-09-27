import React, { useMemo } from 'react';
import { marked } from 'marked';

// Configure marked for clean, safe GFM parsing with breaks
marked.setOptions({
  gfm: true,
  breaks: true,
});

/**
 * Renders markdown text as compiled HTML preview instead of raw syntax (*, #, etc).
 */
export default function MarkdownPreview({ content = '', className = '', style = {} }) {
  const html = useMemo(() => {
    if (!content || typeof content !== 'string') return '';
    try {
      return marked.parse(content);
    } catch (e) {
      console.error('Markdown parse error:', e);
      return content;
    }
  }, [content]);

  if (!content) return null;

  return (
    <div
      className={`markdown-preview ${className}`}
      style={{
        lineHeight: 1.6,
        color: 'var(--color-neutral-300)',
        fontSize: '14.5px',
        ...style,
      }}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
}
