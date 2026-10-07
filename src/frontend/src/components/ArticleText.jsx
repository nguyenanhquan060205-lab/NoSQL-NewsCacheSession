export default function ArticleText({ content = '' }) {
  return content.split(/(https?:\/\/[^\s<>]+)/g).map((part, index) => (
    /^https?:\/\//.test(part)
      ? <a key={index} href={part} target="_blank" rel="noopener noreferrer" className="break-all text-red-700 underline decoration-red-200 underline-offset-4 hover:decoration-red-700">{part}</a>
      : part
  ));
}
