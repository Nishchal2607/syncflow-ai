"use client";
import { useEffect, useMemo } from "react";
import ReactFlow, {
  Background, Controls, Node, Edge, MarkerType, Position, Handle, MiniMap, useReactFlow,
} from "reactflow";
import "reactflow/dist/style.css";
import { Task } from "@/types";
import { Search, ShieldCheck, FileText, Workflow } from "lucide-react";

const AGENT_ICON: Record<string, any> = {
  planner: Workflow,
  research: Search,
  verification: ShieldCheck,
  reporter: FileText,
};

const STATUS_COLOR: Record<string, string> = {
  pending: "#4b5563",
  running: "#22d3ee",
  completed: "#22c55e",
  failed: "#ef4444",
  paused: "#f59e0b",
  skipped: "#374151",
};

function TaskNode({ data }: { data: { task: Task; selected: boolean } }) {
  const { task, selected } = data;
  const Icon = AGENT_ICON[task.agent] || Workflow;
  const color = STATUS_COLOR[task.status] || "#4b5563";
  return (
    <div
      className="workflow-node rounded-xl2 border px-4 py-3 w-56 shadow-lg transition-all"
      style={{
        background: "#161c25",
        borderColor: selected ? "#22d3ee" : "#232b36",
        boxShadow: task.status === "running" ? `0 0 0 1px ${color}, 0 0 14px ${color}55` : undefined,
        opacity: task.status === "skipped" ? 0.45 : 1,
      }}
    >
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-slate-400">
          <Icon size={12} />
          {task.agent}
        </div>
        <span
          className="text-[10px] px-1.5 py-0.5 rounded-full font-medium"
          style={{ color, background: `${color}22`, border: `1px solid ${color}55` }}
        >
          {task.status}
        </span>
      </div>
      <div className="text-sm text-slate-100 leading-snug">{task.name}</div>
    </div>
  );
}

const nodeTypes = { taskNode: TaskNode };

// fitView only runs on mount; tasks usually arrive afterwards, so refit when the count changes.
function RefitOnChange({ count }: { count: number }) {
  const { fitView } = useReactFlow();
  useEffect(() => {
    const t = setTimeout(() => fitView({ padding: 0.2, duration: 250 }), 50);
    return () => clearTimeout(t);
  }, [count, fitView]);
  return null;
}
export default function WorkflowGraph({
  tasks, selectedId, onSelect,
}: { tasks: Task[]; selectedId: string | null; onSelect: (id: string) => void }) {
  const { nodes, edges } = useMemo(() => {
    const sorted = [...tasks].sort((a, b) => a.order_index - b.order_index);
    const colWidth = 290;
    const nodes: Node[] = sorted.map((t, i) => ({
      id: t.id,
      type: "taskNode",
      position: { x: i * colWidth, y: (i % 2) * 125 },
      data: { task: t, selected: t.id === selectedId },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
    }));
    const edges: Edge[] = [];
    sorted.forEach((t) => {
      (t.depends_on || []).forEach((dep) => {
        edges.push({
          id: `${dep}-${t.id}`,
          source: dep,
          target: t.id,
          animated: t.status === "running",
          style: { stroke: t.status === "running" ? "#22d3ee" : "#52647d", strokeWidth: 1.8 },
          markerEnd: { type: MarkerType.ArrowClosed, color: "#334155" },
        });
      });
    });
    return { nodes, edges };
  }, [tasks, selectedId]);

  return (
    <div className="graph-shell"><div className="panel-heading flex items-center justify-between"><span>Workflow graph</span><span className="event-count">{tasks.length} tasks</span></div><div className="graph-canvas">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodeClick={(_, node) => onSelect(node.id)}
        fitView
        proOptions={{ hideAttribution: true }}
        minZoom={0.3}
      >
        <RefitOnChange count={tasks.length} />
        <Background color="#1b2330" gap={18} />
        <Controls showInteractive={false} />
        <MiniMap pannable zoomable nodeColor={(n) => STATUS_COLOR[n.data?.task?.status] || "#475569"} maskColor="rgba(8,13,23,.65)" />
      </ReactFlow>
    </div><div className="graph-legend">{Object.entries(STATUS_COLOR).map(([status,color])=><span key={status}><i style={{background:color}} />{status}</span>)}</div></div>
  );
}
