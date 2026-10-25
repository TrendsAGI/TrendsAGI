export interface TrendsAGIErrorOptions {
  status?: number;
  detail?: string;
  body?: unknown;
  headers?: Headers;
  code?: string;
  cause?: unknown;
}

/**
 * Error thrown for network failures and non-2xx API responses.
 *
 * `status` is the HTTP status when a response was received. `detail` is the
 * API's error message (or the raw response text when it is not JSON).
 */
export class TrendsAGIError extends Error {
  readonly status?: number;
  readonly detail?: string;
  readonly body?: unknown;
  readonly headers?: Headers;
  readonly code?: string;

  constructor(message: string, options: TrendsAGIErrorOptions = {}) {
    super(message, options.cause === undefined ? undefined : { cause: options.cause });
    this.name = "TrendsAGIError";
    this.status = options.status;
    this.detail = options.detail;
    this.body = options.body;
    this.headers = options.headers;
    this.code = options.code;
  }
}
