import Image from 'next/image';

interface HeadingProps {
  onClick?: () => void;
}

export default function Heading({ onClick }: HeadingProps) {
  return (
    <div className="mb-6 flex flex-col items-center gap-2">
      <h1
        onClick={onClick}
        className="text-4xl font-bold cursor-pointer hover:opacity-80 transition text-gray-800"
      >
        Mercedes Scientific Product Search
      </h1>
      <div className="flex items-center gap-2 text-sm">
        Powered by
        <a
          href="https://www.jbbgi.com/journey-ai"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 text-journey-teal font-bold hover:underline"
        >
          <Image
            src="/Journey-LM-teal-icon.png"
            alt="Customer JourneyAI"
            width={24}
            height={24}
            className="rounded-full"
          />
          Customer Journey AI
        </a>
      </div>
    </div>
  );
}
