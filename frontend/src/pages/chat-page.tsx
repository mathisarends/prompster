import { useCallback, useEffect, useReducer, useState } from "react";
import { useLocation } from "react-router-dom";

import { ChatPageHeader } from "../components/chat-page-header";
import { AssistantChatMessage } from "@/components/assistant-chat-message";
import { ChatInputBox } from "@/components/chat-input-box";
import { ChatWorkspacePanel } from "@/components/chat-workspace-panel";
import { DeckPlaylist } from "@/components/deck-playlist";
import {
  FollowUpQuestionFlow,
  type FollowUpQuestionOption,
} from "@/components/follow-up-question-flow";
import { Button } from "@/components/ui/button";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { UserChatMessage } from "@/components/user-chat-message";
import { useAutoScrollToBottom } from "@/hooks/useAutoScrollToBottom";
import { useLocalStorage } from "@/hooks/useLocalStorage";
import { cn } from "@/lib/utils";

import {
  ChatActionType,
  chatReducer,
  createInitialChatState,
  getActiveFollowUpStep,
  getFollowUpDraftValue,
  getFollowUpStepStatus,
} from "./chat-page.state";

const getInitialPrompt = (state: unknown) => {
  if (!state || typeof state !== "object" || !("initialPrompt" in state)) {
    return undefined;
  }

  const initialPrompt = (state as { initialPrompt?: unknown }).initialPrompt;
  if (typeof initialPrompt !== "string") return undefined;

  const trimmedPrompt = initialPrompt.trim();
  return trimmedPrompt.length > 0 ? trimmedPrompt : undefined;
};

const getCanUseResizableLayout = () => {
  if (typeof window === "undefined") return false;

  return window.matchMedia("(min-width: 768px)").matches;
};

export const ChatPage = () => {
  const location = useLocation();
  const initialPrompt = getInitialPrompt(location.state);
  const [prompt, setPrompt] = useState("");
  const [workspacePanelLayout, setWorkspacePanelLayout] = useLocalStorage<
    Record<string, number>
  >("prompster.chat.workspace-layout", { chat: 50, workspace: 50 });
  const [canUseResizableLayout, setCanUseResizableLayout] = useState(
    getCanUseResizableLayout,
  );
  const [state, dispatch] = useReducer(
    chatReducer,
    initialPrompt,
    createInitialChatState,
  );
  const { messages, followUp, workspacePanel } = state;
  const messagesEndRef = useAutoScrollToBottom<HTMLDivElement>(messages.length);
  const currentStep = getActiveFollowUpStep(followUp);
  const currentAnswer = getFollowUpDraftValue(followUp);
  const { currentStepIndex, totalSteps, isFirstStep, isLastStep } =
    getFollowUpStepStatus(followUp);
  const isWorkspacePanelOpen = workspacePanel.status === "open";

  const sendMessage = useCallback(
    (text: string) => dispatch({ type: ChatActionType.SendMessage, text }),
    [],
  );
  const answerFollowUp = useCallback(
    (answer: string, option?: FollowUpQuestionOption) =>
      dispatch({ type: ChatActionType.AnswerFollowUp, answer, option }),
    [],
  );
  const updateFollowUpDraft = useCallback(
    (value: string) => {
      if (!currentStep) return;

      dispatch({
        type: ChatActionType.UpdateFollowUpDraft,
        stepId: currentStep.id,
        value,
      });
    },
    [currentStep],
  );
  const skipFollowUp = useCallback(
    () => dispatch({ type: ChatActionType.SkipFollowUp }),
    [],
  );
  const dismissFollowUp = useCallback(
    () => dispatch({ type: ChatActionType.DismissFollowUp }),
    [],
  );
  const goToPrevStep = useCallback(
    () => dispatch({ type: ChatActionType.GoToPrevStep }),
    [],
  );
  const goToNextStep = useCallback(
    () => dispatch({ type: ChatActionType.GoToNextStep }),
    [],
  );
  const openWorkspacePanel = useCallback(
    () => dispatch({ type: ChatActionType.OpenWorkspacePanel }),
    [],
  );
  const closeWorkspacePanel = useCallback(
    () => dispatch({ type: ChatActionType.CloseWorkspacePanel }),
    [],
  );

  useEffect(() => {
    const mediaQuery = window.matchMedia("(min-width: 768px)");
    const updateLayoutMode = (event: MediaQueryListEvent) => {
      setCanUseResizableLayout(event.matches);
    };

    mediaQuery.addEventListener("change", updateLayoutMode);

    return () => {
      mediaQuery.removeEventListener("change", updateLayoutMode);
    };
  }, []);

  const shouldUseResizableLayout =
    isWorkspacePanelOpen && canUseResizableLayout;

  const chatPanelContent = (
    <section className="flex h-full min-h-0 min-w-0 flex-1 flex-col">
      <ChatPageHeader />

      <main className="prompster-scrollbar min-h-0 flex-1 overflow-y-auto px-4 sm:px-8">
        <div
          className={cn(
            "mx-auto flex w-full flex-col transition-[max-width] duration-500 ease-out",
            isWorkspacePanelOpen ? "max-w-3xl" : "max-w-4xl",
          )}
        >
          <div className="flex flex-col gap-4 px-1 pt-1 sm:px-2">
            {messages.map((message) =>
              message.role === "user" ? (
                <UserChatMessage key={message.id} text={message.text} />
              ) : (
                <AssistantChatMessage
                  key={message.id}
                  text={message.text}
                  toolCalls={message.toolCalls}
                />
              ),
            )}
            <div ref={messagesEndRef} />
          </div>
        </div>
      </main>

      <div className="shrink-0 bg-gradient-to-t from-background via-background/85 to-transparent px-4 pb-4 pt-6 sm:px-8 sm:pb-3">
        <div
          className={cn(
            "mx-auto w-full transition-[max-width] duration-500 ease-out",
            isWorkspacePanelOpen ? "max-w-3xl" : "max-w-4xl",
          )}
        >
          {!isWorkspacePanelOpen && (
            <div className="mb-3 flex flex-col gap-3 rounded-3xl border border-white/10 bg-card/60 px-4 py-3 text-sm text-muted-foreground shadow-xl shadow-black/10 backdrop-blur-md sm:flex-row sm:items-center sm:justify-between">
              <span>
                Prototyp-Test: Sende <span className="font-mono">/deck</span>,{" "}
                <span className="font-mono">/split</span> oder öffne die
                Arbeitsfläche direkt.
              </span>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={openWorkspacePanel}
                className="shrink-0 border-white/15 bg-transparent hover:bg-white/10"
              >
                Split-Screen testen
              </Button>
            </div>
          )}

          {currentStep && (
            <div className="mb-3">
              <FollowUpQuestionFlow
                key={currentStep.id}
                question={currentStep.question}
                options={currentStep.options}
                value={currentAnswer}
                onValueChange={updateFollowUpDraft}
                onAnswer={answerFollowUp}
                onSkip={skipFollowUp}
                onDismiss={dismissFollowUp}
                step={{
                  current: currentStepIndex + 1,
                  total: totalSteps,
                  onPrev: isFirstStep ? undefined : goToPrevStep,
                  onNext: isLastStep ? undefined : goToNextStep,
                }}
                className="rounded-3xl border-border/60 bg-card/90"
              />
            </div>
          )}
          <ChatInputBox
            value={prompt}
            onChange={setPrompt}
            onSubmit={sendMessage}
            disclaimerText="Prompster ist eine KI und kann Fehler machen. Bitte überprüfe die Antworten."
            showDisclaimer
            placeholder="Deine Antwort ..."
            sendButtonAriaLabel="Nachricht senden"
            className="rounded-3xl border border-border/50 bg-card/70 p-4 shadow-2xl shadow-black/20"
            textareaClassName="max-h-40"
            rows={1}
          />
        </div>
      </div>
    </section>
  );

  const workspacePanelContent = workspacePanel.status === "open" && (
    <ChatWorkspacePanel onClose={closeWorkspacePanel}>
      <DeckPlaylist />
    </ChatWorkspacePanel>
  );

  return (
    <div className="chat-page-background flex h-dvh overflow-hidden text-foreground">
      <div className="relative z-10 min-h-0 flex-1">
        {shouldUseResizableLayout ? (
          <ResizablePanelGroup
            orientation="horizontal"
            className="h-full bg-transparent"
            defaultLayout={workspacePanelLayout}
            onLayoutChanged={setWorkspacePanelLayout}
          >
            <ResizablePanel
              id="chat"
              defaultSize={`${workspacePanelLayout.chat ?? 50}`}
              minSize="36"
              maxSize="68"
            >
              {chatPanelContent}
            </ResizablePanel>
            <ResizableHandle
              withHandle
              className="w-px cursor-col-resize bg-white/5 hover:bg-white/10 data-[separator=active]:bg-primary/35"
            />
            <ResizablePanel
              id="workspace"
              defaultSize={`${workspacePanelLayout.workspace ?? 50}`}
              minSize="32"
              maxSize="64"
            >
              <div className="h-full animate-in slide-in-from-right-6 duration-500">
                {workspacePanelContent}
              </div>
            </ResizablePanel>
          </ResizablePanelGroup>
        ) : (
          <div className="relative flex h-full min-h-0">
            {chatPanelContent}

            <aside
              className={cn(
                "absolute inset-y-0 right-0 z-30 h-full w-full max-w-xl overflow-hidden border-l border-white/10 bg-[hsl(222_36%_7%)] transition-[transform,opacity] duration-500 ease-out",
                isWorkspacePanelOpen
                  ? "translate-x-0 opacity-100"
                  : "pointer-events-none translate-x-full opacity-0",
              )}
              aria-hidden={!isWorkspacePanelOpen}
            >
              {workspacePanelContent}
            </aside>
          </div>
        )}
      </div>
    </div>
  );
};
