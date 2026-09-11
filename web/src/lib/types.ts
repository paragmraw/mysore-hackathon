export type Localized = { en: string; kn: string };

export type QuestionType = "single_select" | "number" | "pincode";

export type QuestionOption = { value: string; label: Localized };

export type ShowIfMap = Record<
  string,
  string[] | { min?: number | null; max?: number | null }
>;

export type Question = {
  id: string;
  type: QuestionType;
  label: Localized;
  options?: QuestionOption[];
  cols?: 1 | 2;
  optional?: boolean;
  showIf?: ShowIfMap;
  stage?: string[];
  scheme_id?: string | null;
};

export type Channel =
  | { type: "portal"; label: Localized; url: string }
  | { type: "csc" };

export type SchemeRoute = { group: string; value: string };

export type RuleCheck =
  | { op: "equals"; field: string; value: string }
  | { op: "in"; field: string; values: string[] }
  | { op: "num_gte"; field: string; value: number }
  | { op: "num_lte"; field: string; value: number }
  | { op: "income_lte"; value: number };

export type ReasonRef = { code: string; params?: Record<string, string> };

export type ExclusionRule = { id: string; check: RuleCheck; reason: ReasonRef };

export type EligibilityRule = {
  id: string;
  check: RuleCheck;
  on_fail: {
    status: "blocked" | "not_eligible";
    reason: ReasonRef;
    fix_id?: string;
  };
};

export type FixRule = {
  id: string;
  check: RuleCheck;
  reason: ReasonRef;
  fix_id: string;
};

export type SchemeRules = {
  eligibility: EligibilityRule[];
  exclusions: ExclusionRule[];
  fixes: FixRule[];
};

export type SchemeRecord = {
  id: string;
  code: string;
  name: Localized;
  summ: Localized;
  department: Localized;
  benefit_type: string;
  jurisdiction: string;
  benefit: Localized;
  amount: Localized;
  amount_inr: number | null;
  amount_period: string;
  deadline: Localized;
  eligibility_criteria: Localized[];
  application_steps: Localized[];
  channels: Channel[];
  docs: Localized[];
  route: SchemeRoute | null;
  criteria_note: Localized | null;
  rules: SchemeRules;
  confidence_note: string;
  last_verified: string;
  source_url: string;
  source_note: Localized;
};

export type ReasonCode = string;

export type Reason = {
  code: ReasonCode;
  params?: Record<string, string>;
  message: Localized;
};

export type FixRef = {
  fix_id: string;
  reason: Reason;
  title: Localized;
  steps: Localized[];
};

export type MatchResult = {
  scheme_id: string;
  code: string;
  name: Localized;
  summ: Localized;
  status: "eligible" | "blocked" | "not_eligible";
  confidence: "likely";
  reasons: Reason[];
  fixes: FixRef[];
  matched_facts: { question_id: string; answer: string }[];
  docs: Localized[];
};

export type MatchResponse = {
  results: MatchResult[];
  hidden_route_groups: string[];
};

export type QuickMatchResult = {
  scheme_id: string;
  code: string;
  name: Localized;
  summ: Localized;
  status: "likely";
  confidence: "likely";
  amount_inr: number | null;
  amount_period: string;
  amount: Localized;
};

export type QuickMatchResponse = {
  results: QuickMatchResult[];
  benefit_total: { month: number; "one-time": number; year: number };
  hidden_route_groups: string[];
};

export type DeepCheckResponse = MatchResult;

export type CscCenter = {
  id: string;
  name: Localized;
  address: Localized;
  locality: string;
  city: string;
  taluk: string;
  pincode: string;
  lat: number;
  lng: number;
  phone?: string;
  hours?: string;
};

export type CscResponse = {
  match: "pincode" | "nearby" | "district_fallback";
  centers: (CscCenter & { distance_km?: number })[];
};

export type Meta = {
  schemes: number;
  questions: number;
  last_data_update: string;
};

export type Me = {
  mobile: string;
  name: string;
  answers: Record<string, string | null>;
  deep_check_answers: Record<string, string | null>;
};
