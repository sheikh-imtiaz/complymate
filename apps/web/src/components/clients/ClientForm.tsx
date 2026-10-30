"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Button, Checkbox, Field, Input, Select, Textarea } from "@complymate/ui";

const country = z.string().trim().toUpperCase().regex(/^[A-Z]{2}$/, "2-letter code").optional().or(z.literal(""));

export const clientSchema = z
  .object({
    client_type: z.enum(["individual", "company", "trust", "partnership"]),
    given_names: z.string().optional(),
    family_name: z.string().optional(),
    legal_name: z.string().optional(),
    date_of_birth: z.string().optional(),
    acn: z.string().optional(),
    abn: z.string().optional(),
    residential_country: country,
    nationality: country,
    country_of_incorporation: country,
    occupation: z.string().optional(),
    channel: z.enum(["face_to_face", "non_face_to_face", "intermediary"]),
    services: z.array(z.string()),
    source_of_funds: z.string().optional(),
    source_of_funds_verified: z.boolean(),
    cash_intensive: z.boolean(),
    is_pep: z.boolean(),
    pep_details: z.string().optional(),
  })
  .refine((v) => (v.client_type === "individual" ? !!(v.given_names && v.family_name) : !!v.legal_name), {
    message: "Name is required",
    path: ["legal_name"],
  });

export type ClientFormValues = z.infer<typeof clientSchema>;

const SERVICES = [
  ["real_estate_transaction", "Real estate transaction"],
  ["handling_client_money", "Handling client money"],
  ["company_or_trust_formation", "Company or trust formation"],
  ["nominee_director_or_shareholder", "Nominee director/shareholder"],
  ["registered_office_services", "Registered office"],
  ["selling_shareholdings_or_businesses", "Buying/selling a business"],
] as const;

export function ClientForm({ defaultValues, onSubmit, submitting }: {
  defaultValues?: Partial<ClientFormValues>;
  onSubmit: (values: ClientFormValues) => void;
  submitting?: boolean;
}) {
  const { register, handleSubmit, watch, formState: { errors } } = useForm<ClientFormValues>({
    resolver: zodResolver(clientSchema),
    defaultValues: { client_type: "individual", channel: "face_to_face", services: [], source_of_funds_verified: false, cash_intensive: false, is_pep: false, ...defaultValues },
  });
  const type = watch("client_type");
  const clean = (v: ClientFormValues) =>
    onSubmit(Object.fromEntries(Object.entries(v).filter(([, x]) => x !== "" && x !== undefined)) as ClientFormValues);

  return (
    <form onSubmit={handleSubmit(clean)} className="grid gap-5">
      <div className="grid gap-4 md:grid-cols-3">
        <Field label="Client type">
          <Select {...register("client_type")}>
            <option value="individual">Individual</option>
            <option value="company">Company</option>
            <option value="trust">Trust</option>
            <option value="partnership">Partnership</option>
          </Select>
        </Field>
        <Field label="How did you meet the client?">
          <Select {...register("channel")}>
            <option value="face_to_face">Face to face</option>
            <option value="non_face_to_face">Not face to face</option>
            <option value="intermediary">Through an intermediary</option>
          </Select>
        </Field>
      </div>
      {type === "individual" ? (
        <div className="grid gap-4 md:grid-cols-3">
          <Field label="Given names"><Input {...register("given_names")} autoComplete="off" /></Field>
          <Field label="Family name" error={errors.legal_name?.message}><Input {...register("family_name")} autoComplete="off" /></Field>
          <Field label="Date of birth"><Input type="date" {...register("date_of_birth")} /></Field>
          <Field label="Residential country" hint="ISO code, e.g. AU" error={errors.residential_country?.message}><Input {...register("residential_country")} maxLength={2} /></Field>
          <Field label="Nationality" error={errors.nationality?.message}><Input {...register("nationality")} maxLength={2} /></Field>
          <Field label="Occupation"><Input {...register("occupation")} /></Field>
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          <Field label="Legal name" error={errors.legal_name?.message}><Input {...register("legal_name")} /></Field>
          <Field label="ACN / registration number"><Input {...register("acn")} /></Field>
          <Field label="ABN"><Input {...register("abn")} /></Field>
          <Field label="Country of incorporation" error={errors.country_of_incorporation?.message}><Input {...register("country_of_incorporation")} maxLength={2} /></Field>
        </div>
      )}
      <fieldset className="grid gap-2">
        <legend className="mb-1 text-sm font-medium text-slate-700">Services for this client</legend>
        <div className="grid gap-2 md:grid-cols-3">
          {SERVICES.map(([value, label]) => (
            <label key={value} className="flex items-center gap-2 text-sm">
              <input type="checkbox" value={value} {...register("services")} className="h-4 w-4" /> {label}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="grid gap-4 md:grid-cols-2">
        <Field label="Source of funds"><Textarea {...register("source_of_funds")} rows={2} /></Field>
        <div className="flex flex-col gap-2 pt-6">
          <Checkbox label="Source of funds verified" {...register("source_of_funds_verified")} />
          <Checkbox label="Cash-intensive business" {...register("cash_intensive")} />
          <Checkbox label="Politically exposed person (declared)" {...register("is_pep")} />
        </div>
      </div>
      {watch("is_pep") ? <Field label="PEP details"><Textarea {...register("pep_details")} rows={2} /></Field> : null}
      <div className="flex justify-end">
        <Button type="submit" loading={submitting}>Save client</Button>
      </div>
    </form>
  );
}
