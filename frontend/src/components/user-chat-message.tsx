type UserChatMessageProps = {
  text: string;
};

export const UserChatMessage = ({ text }: UserChatMessageProps) => {
  return (
    <div className="ml-auto max-w-[82%] rounded-2xl bg-white/10 px-4 py-3 text-sm leading-relaxed text-foreground sm:text-base">
      {text}
    </div>
  );
};
