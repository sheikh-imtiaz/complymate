"use client";
import { useEffect, useState } from "react";
import { EditorContent, useEditor } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Bold, Italic, List, ListOrdered, Heading3, Lock } from "lucide-react";
import type { ProgramSection } from "@complymate/api-types";
import { Alert, Badge, Button } from "@complymate/ui";
import { ApiError, api, del, post, put } from "@/lib/api-client";
import { formatDateTime } from "@/lib/format";

/** Rich text editor for one program section. Locks the section while editing (5 minute lease, renewed on save),
 * shows the agent's draft for accept/reject, and keeps a tracked-changes history server-side. */
export function SectionEditor({ versionId, section, editable, currentUserId, onSaved }: {
  versionId: string;
  section: ProgramSection;
  editable: boolean;
  currentUserId?: string;
  onSaved: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const lockedByOther = !!section.locked_by && section.locked_by !== currentUserId && !!section.locked_until && new Date(section.locked_until) > new Date();
  const editor = useEditor({
    extensions: [StarterKit],
    content: section.content_html || "<p></p>",
    editable: false,
    immediatelyRender: false,
    editorProps: { attributes: { class: "prose prose-sm max-w-none min-h-32 focus:outline-none" } },
  });

  useEffect(() => {
    if (editor && !editing) editor.commands.setContent(section.content_html || "<p></p>");
  }, [editor, section.content_html, editing]);
  useEffect(() => {
    editor?.setEditable(editing);
  }, [editor, editing]);

  async function start() {
    setError(null);
    try {
      await post(`/program/versions/${versionId}/sections/${section.key}/lock`);
      setEditing(true);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not lock section");
    }
  }
  async function save() {
    if (!editor) return;
    try {
      await put(`/program/versions/${versionId}/sections/${section.key}`, { content_html: editor.getHTML(), expected_updated_at: section.updated_at });
      await del(`/program/versions/${versionId}/sections/${section.key}/lock`);
      setEditing(false);
      onSaved();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save");
    }
  }
  async function decide(accept: boolean) {
    await api(`/program/versions/${versionId}/sections/${section.key}/ai-decision`, { method: "POST", body: { accept } });
    onSaved();
  }

  const tool = (label: string, Icon: typeof Bold, action: () => void, active: boolean) => (
    <button type="button" aria-label={label} onClick={action} className={`rounded p-1.5 ${active ? "bg-slate-200" : "hover:bg-slate-100"}`}>
      <Icon className="h-4 w-4" />
    </button>
  );

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="font-semibold">{section.title}</h3>
        <div className="flex items-center gap-2">
          {section.ai_generated ? <Badge tone="info">AI-assisted</Badge> : null}
          {lockedByOther ? <Badge tone="warning"><Lock className="mr-1 h-3 w-3" />Being edited</Badge> : null}
          {editable && !editing ? <Button size="sm" variant="secondary" onClick={start} disabled={lockedByOther}>Edit</Button> : null}
          {editing ? <Button size="sm" onClick={save}>Save</Button> : null}
        </div>
      </div>
      {editing && editor ? (
        <div className="mb-2 flex gap-1 border-b border-slate-100 pb-2">
          {tool("Bold", Bold, () => editor.chain().focus().toggleBold().run(), editor.isActive("bold"))}
          {tool("Italic", Italic, () => editor.chain().focus().toggleItalic().run(), editor.isActive("italic"))}
          {tool("Heading", Heading3, () => editor.chain().focus().toggleHeading({ level: 3 }).run(), editor.isActive("heading"))}
          {tool("Bullet list", List, () => editor.chain().focus().toggleBulletList().run(), editor.isActive("bulletList"))}
          {tool("Numbered list", ListOrdered, () => editor.chain().focus().toggleOrderedList().run(), editor.isActive("orderedList"))}
        </div>
      ) : null}
      <EditorContent editor={editor} className={editing ? "rounded-md border border-brand-100 p-3" : ""} />
      {section.ai_draft_html ? (
        <div className="mt-4 rounded-lg border border-brand-100 bg-brand-50 p-4">
          <p className="mb-2 text-sm font-semibold text-brand-700">Suggested draft from the agent — review before accepting</p>
          <div className="prose prose-sm max-w-none rounded bg-white p-3 text-sm whitespace-pre-wrap">
            {section.ai_draft_html.replace(/<[^>]+>/g, (tag) => (/^<\/(p|h\d|li)>$/.test(tag) ? "\n" : ""))}
          </div>
          {section.citations.length ? (
            <ul className="mt-2 list-disc pl-5 text-xs text-slate-600">
              {section.citations.map((c) => <li key={String(c.ref)}>{String(c.ref)}: {String(c.title)}</li>)}
            </ul>
          ) : null}
          {editable ? (
            <div className="mt-3 flex gap-2">
              <Button size="sm" onClick={() => void decide(true)}>Accept draft</Button>
              <Button size="sm" variant="secondary" onClick={() => void decide(false)}>Reject</Button>
            </div>
          ) : null}
        </div>
      ) : null}
      {section.updated_at ? <p className="mt-2 text-xs text-slate-400">Last edited {formatDateTime(section.updated_at)} · {section.tracked_changes.length} tracked change(s)</p> : null}
      {error ? <Alert tone="danger" className="mt-2">{error}</Alert> : null}
    </section>
  );
}
