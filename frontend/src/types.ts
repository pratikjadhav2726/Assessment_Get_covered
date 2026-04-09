export type ScanState =
  | "found"
  | "not_found"
  | "protected_or_blocked"
  | "invalid_input"
  | "timeout"
  | "scan_error";

export type DebugPayload = {
  input_url?: string;
  final_url?: string;
  page_title?: string;
  html_length?: number;
  blocked_reasons?: string[];
  html_preview?: string;
  has_password_input?: boolean;
  has_sign_in_text?: boolean;
  has_continue_with?: boolean;
  has_one_time?: boolean;
};

export type ScanResponse = {
  input_url: string;
  state: ScanState;
  found: boolean;
  confidence: number;
  source: string;
  detection_signals: string[];
  html_snippet: string | null;
  message: string;
  debug?: DebugPayload | null;
};
