import ReactMarkdown from 'react-markdown'

interface MarkdownRendererProps {
  content: string
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div style={{ lineHeight: '1.8' }}>
      <ReactMarkdown
        components={{
          p: ({ children }) => (
            <p style={{ marginBottom: '12px' }}>{children}</p>
          ),
          strong: ({ children }) => (
            <strong style={{ fontWeight: 700, color: '#1f2937' }}>{children}</strong>
          ),
          em: ({ children }) => (
            <em style={{ fontStyle: 'italic' }}>{children}</em>
          ),
          ul: ({ children }) => (
            <ul style={{ marginLeft: '20px', marginBottom: '12px', listStyleType: 'disc' }}>{children}</ul>
          ),
          ol: ({ children }) => (
            <ol style={{ marginLeft: '20px', marginBottom: '12px', listStyleType: 'decimal' }}>{children}</ol>
          ),
          li: ({ children }) => (
            <li style={{ marginBottom: '4px' }}>{children}</li>
          ),
          code: ({ children }) => (
            <code style={{
              backgroundColor: '#f3f4f6',
              padding: '2px 6px',
              borderRadius: '4px',
              fontFamily: 'monospace',
              fontSize: '14px'
            }}>{children}</code>
          ),
          pre: ({ children }) => (
            <pre style={{
              backgroundColor: '#1f2937',
              color: '#e5e7eb',
              padding: '12px',
              borderRadius: '8px',
              overflow: 'auto',
              marginBottom: '12px'
            }}>{children}</pre>
          ),
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: '#3b82f6' }}>{children}</a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
