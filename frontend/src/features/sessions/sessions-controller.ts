import { createMutationController, createQueryController } from "@tanstack/lit-query";
import type { ReactiveControllerHost } from "lit";
import {
  listSessionsQuery,
  sessionsKeys,
  deleteSessionMutation,
  starSessionMutation,
  unstarSessionMutation,
  updateSessionMutation,
} from "@api/generated/sessions";
import { queryClient } from "@api/query-client";

/** API ownership and invalidation live outside the reusable sidebar. */
export class SessionsController {
  readonly list;
  readonly remove;
  readonly star;
  readonly unstar;
  readonly rename;
  constructor(host: ReactiveControllerHost) {
    this.list = createQueryController(host, listSessionsQuery());
    this.remove = createMutationController(host, deleteSessionMutation());
    this.star = createMutationController(host, starSessionMutation());
    this.unstar = createMutationController(host, unstarSessionMutation());
    this.rename = createMutationController(host, updateSessionMutation());
  }
  get busy(): boolean {
    return (
      this.remove().isPending ||
      this.star().isPending ||
      this.unstar().isPending ||
      this.rename().isPending
    );
  }
  refresh(): Promise<void> {
    return queryClient.invalidateQueries({ queryKey: sessionsKeys.all });
  }
}
