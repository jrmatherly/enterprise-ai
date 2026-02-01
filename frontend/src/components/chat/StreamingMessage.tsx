interface StreamingMessageProps {
  content: string;
}

export function StreamingMessage({ content }: StreamingMessageProps) {
  return (
    <div className="flex gap-3">
      {/* Avatar */}
      <div className="flex size-8 flex-shrink-0 items-center justify-center rounded-full bg-neutral-700 text-xs font-medium text-neutral-300">
        AI
      </div>

      {/* Message Content */}
      <div className="max-w-[75%] rounded-2xl bg-neutral-800 px-4 py-2.5">
        <div className="whitespace-pre-wrap text-sm leading-relaxed text-neutral-100 text-pretty">
          {content}
          <span className="ml-0.5 inline-block size-2 animate-pulse rounded-full bg-neutral-400" />
        </div>
      </div>
    </div>
  );
}
