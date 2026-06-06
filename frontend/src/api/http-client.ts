import {
  AXIOS_INSTANCE,
  customInstance as sharedCustomInstance,
} from "@/shared/api/http-client";
import type { AxiosRequestConfig } from "axios";
import type { BodyType, ErrorType } from "@/shared/api/http-client";

export { AXIOS_INSTANCE };
export type { BodyType, ErrorType };

export const customInstance = <T>(
  config: AxiosRequestConfig,
  options?: AxiosRequestConfig,
): Promise<T> => sharedCustomInstance<T>(config, options);
