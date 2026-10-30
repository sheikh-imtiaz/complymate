// Types generated from docs/api/openapi.json (`pnpm --filter @complymate/api-types generate`).
import type { components, paths } from "./schema";

export type { components, paths };
type S = components["schemas"];

export type Me = S["MeOut"];
export type Tenant = S["TenantOut"];
export type TenantSettings = S["SettingsOut"];
export type Client = S["ClientOut"];
export type ClientListItem = S["ClientListItem"];
export type Party = S["PartyOut"];
export type Document = S["DocumentOut"];
export type Assessment = S["AssessmentOut"];
export type EddTask = S["EddTaskOut"];
export type ScreeningRun = S["RunOut"];
export type Program = S["ProgramOut"];
export type ProgramVersion = S["VersionDetail"];
export type ProgramSection = S["SectionOut"];
export type Interview = S["InterviewOut"];
export type SmrCase = S["SmrOut"];
export type SmrDetail = S["SmrDetail"];
export type Task = S["TaskOut"];
export type Notification = S["NotificationOut"];
export type AuditEvent = S["AuditEventOut"];
export type Member = S["MemberOut"];
export type Role = S["RoleOut"];
export type Invitation = S["InvitationOut"];
export type ApiKey = S["ApiKeyOut"];
export type Billing = S["BillingOut"];
export type TrainingModule = S["ModuleOut"];
export type TrainingModuleDetail = S["ModuleDetail"];
export type CommentItem = S["CommentOut"];
export type ChatAnswer = S["ChatAnswer"];
export type TenantSummary = S["TenantSummary"];
export type KbSource = S["KbSourceOut"];
export type QuizQuestion = S["QuizQuestionOut"];
export type ReportJob = S["ReportJobOut"];

export interface Page<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}
