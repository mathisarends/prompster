import { useEffect, useRef } from "react";
import { ArrowUp } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

type ChatInputBoxProps = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: (text: string) => void;
  placeholder?: string;
  className?: string;
  textareaClassName?: string;
  rows?: number;
  showSeparator?: boolean;
  sendButtonAriaLabel?: string;
  focusOnTyping?: boolean;
};

const isEditableElement = (element: EventTarget | null) => {
  if (!(element instanceof HTMLElement)) return false;

  return (
    element.isContentEditable ||
    element.closest("input, textarea, select, [contenteditable='true']") !==
      null
  );
};

const isVisible = (element: HTMLElement) => {
  const rect = element.getBoundingClientRect();
  const style = window.getComputedStyle(element);

  return (
    rect.width > 0 &&
    rect.height > 0 &&
    style.display !== "none" &&
    style.visibility !== "hidden"
  );
};

const isTextEntryKey = (event: KeyboardEvent) => {
  return (
    event.key.length === 1 &&
    !event.ctrlKey &&
    !event.metaKey &&
    !event.altKey &&
    !event.isComposing
  );
};

export const ChatInputBox = ({
  value,
  onChange,
  onSubmit,
  placeholder,
  className,
  textareaClassName,
  rows,
  showSeparator = false,
  sendButtonAriaLabel = "Nachricht senden",
  focusOnTyping = true,
}: ChatInputBoxProps) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!focusOnTyping) return;

    const focusChatInputOnTyping = (event: KeyboardEvent) => {
      const textarea = textareaRef.current;
      const dialogOpen = document.querySelector(
        "[data-slot='dialog-content'][data-open]",
      );

      if (
        !textarea ||
        event.defaultPrevented ||
        document.activeElement === textarea ||
        dialogOpen ||
        !isTextEntryKey(event) ||
        !isVisible(textarea) ||
        isEditableElement(event.target)
      ) {
        return;
      }

      textarea.focus();
    };

    window.addEventListener("keydown", focusChatInputOnTyping);
    return () => {
      window.removeEventListener("keydown", focusChatInputOnTyping);
    };
  }, [focusOnTyping]);

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed) return;

    onSubmit(trimmed);
    onChange("");
  };

  return (
    <div
      className={cn(
        "overflow-hidden rounded-2xl bg-card/55 p-4 backdrop-blur-md sm:p-5",
        className,
      )}
    >
      <Textarea
        ref={textareaRef}
        rows={rows}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            submit();
          }
        }}
        placeholder={placeholder}
        className={cn(
          "min-h-15 resize-none border-none bg-transparent p-0 text-base shadow-none focus-visible:ring-0 md:text-base",
          textareaClassName,
        )}
      />

      {showSeparator && <Separator />}

      <div className="flex items-center justify-end">
        <Button
          size="icon"
          onClick={submit}
          disabled={!value.trim()}
          aria-label={sendButtonAriaLabel}
        >
          <ArrowUp className="size-4 text-white" />
        </Button>
      </div>
    </div>
  );
};
