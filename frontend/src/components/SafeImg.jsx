import { useState } from 'react';

// <img> com fallback: se a URL quebrar (ex: /uploads legados que não
// existem na Vercel), mostra o 🐊 em vez de ícone quebrado.
export default function SafeImg({ src, alt = '', className, style, ...rest }) {
  const [quebrou, setQuebrou] = useState(false);
  if (!src || quebrou) return <span aria-label={alt || 'sem imagem'}>🐊</span>;
  return (
    <img
      src={src}
      alt={alt}
      className={className}
      style={style}
      loading="lazy"
      onError={() => setQuebrou(true)}
      {...rest}
    />
  );
}
