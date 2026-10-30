import { Building2, User } from "lucide-react";
import { Badge } from "@complymate/ui";

export interface TreeNode {
  id: string;
  name: string;
  is_entity: boolean;
  party_type: string;
  direct_percent: number | null;
  effective_percent: number;
  is_beneficial_owner: boolean;
  is_pep: boolean;
  children: TreeNode[];
}

function Node({ node }: { node: TreeNode }) {
  const Icon = node.is_entity ? Building2 : User;
  return (
    <li className="ml-4 border-l border-slate-200 pl-4">
      <div className="flex flex-wrap items-center gap-2 py-1.5">
        <Icon className="h-4 w-4 text-slate-500" />
        <span className="font-medium">{node.name}</span>
        <span className="text-xs text-slate-500">{node.party_type.replace(/_/g, " ")}</span>
        {node.direct_percent != null ? <span className="text-xs text-slate-500">{node.direct_percent}% direct · {node.effective_percent}% effective</span> : null}
        {node.is_beneficial_owner ? <Badge tone="info">Beneficial owner</Badge> : null}
        {node.is_pep ? <Badge tone="danger">PEP</Badge> : null}
      </div>
      {node.children.length ? <ul>{node.children.map((c) => <Node key={c.id} node={c} />)}</ul> : null}
    </li>
  );
}

export function OwnershipTree({ root, tree }: { root: { name: string; client_type: string }; tree: TreeNode[] }) {
  return (
    <div className="text-sm">
      <div className="flex items-center gap-2 font-semibold"><Building2 className="h-4 w-4" />{root.name}</div>
      {tree.length ? <ul className="mt-1">{tree.map((n) => <Node key={n.id} node={n} />)}</ul> : <p className="mt-2 text-slate-500">No owners or controllers recorded yet.</p>}
    </div>
  );
}
