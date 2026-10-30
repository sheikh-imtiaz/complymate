"use client";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Textarea } from "@complymate/ui";
import { get } from "@/lib/api-client";

interface DirectoryEntry { user_id: string; full_name: string | null; email: string; role_key: string }

/** Textarea with @mention suggestions. Inserts `@[Name](user:<id>)` tokens the API understands. */
export function MentionInput({ value, onChange, placeholder }: { value: string; onChange: (v: string) => void; placeholder?: string }) {
  const { data: people = [] } = useQuery({ queryKey: ["directory"], queryFn: () => get<DirectoryEntry[]>("/users/directory") });
  const [query, setQuery] = useState<string | null>(null);
  const matches = useMemo(
    () => (query === null ? [] : people.filter((p) => `${p.full_name ?? ""} ${p.email}`.toLowerCase().includes(query.toLowerCase())).slice(0, 5)),
    [people, query],
  );
  return (
    <div className="relative">
      <Textarea
        value={value}
        placeholder={placeholder ?? "Write a comment… use @ to mention someone"}
        onChange={(e) => {
          onChange(e.target.value);
          const m = /@([\w.]*)$/.exec(e.target.value);
          setQuery(m ? m[1] : null);
        }}
      />
      {matches.length ? (
        <ul className="absolute z-10 mt-1 w-72 rounded-md border border-slate-200 bg-white shadow-lg">
          {matches.map((p) => (
            <li key={p.user_id}>
              <button
                type="button"
                className="w-full px-3 py-2 text-left text-sm hover:bg-slate-50"
                onClick={() => {
                  onChange(value.replace(/@[\w.]*$/, `@[${p.full_name ?? p.email}](user:${p.user_id}) `));
                  setQuery(null);
                }}
              >
                {p.full_name ?? p.email} <span className="text-xs text-slate-400">{p.role_key}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
