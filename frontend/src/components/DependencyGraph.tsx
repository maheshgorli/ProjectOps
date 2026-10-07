import { useMemo } from 'react';
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  BackgroundVariant,
  MarkerType,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { CustomTaskNode, type CustomTaskNodeData } from './CustomTaskNode';
import type { ProjectPlan, ScheduleResult, Member } from '../types/api';
import { Flame, Clock, Calendar, CheckSquare } from 'lucide-react';

interface DependencyGraphProps {
  plan: ProjectPlan | null;
  schedule: ScheduleResult | null;
  members: Member[];
}

const nodeTypes = {
  taskNode: CustomTaskNode,
};

const NODE_WIDTH = 260;
const NODE_HEIGHT = 120;

function getLayoutedElements(nodes: Node<CustomTaskNodeData>[], edges: Edge[]) {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: 'LR', ranksep: 80, nodesep: 40 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - NODE_WIDTH / 2,
        y: nodeWithPosition.y - NODE_HEIGHT / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
}

export const DependencyGraph: React.FC<DependencyGraphProps> = ({
  plan,
  schedule,
  members,
}) => {
  const membersMap = useMemo(() => {
    const map = new Map<string, Member>();
    members.forEach((m) => map.set(m.id, m));
    return map;
  }, [members]);

  const criticalPathSet = useMemo(() => {
    return new Set(schedule?.critical_path ?? []);
  }, [schedule]);

  const { nodes, edges } = useMemo(() => {
    if (!plan || !plan.tasks || plan.tasks.length === 0) {
      return { nodes: [], edges: [] };
    }

    const rawNodes: Node<CustomTaskNodeData>[] = plan.tasks.map((task) => {
      const isCritical = criticalPathSet.has(task.id);
      const scheduled = schedule?.tasks?.[task.id];
      const member = task.assigned_to_id ? membersMap.get(task.assigned_to_id) : undefined;

      return {
        id: task.id,
        type: 'taskNode',
        data: {
          task,
          scheduled,
          member,
          isCritical,
        },
        position: { x: 0, y: 0 },
      };
    });

    const rawEdges: Edge[] = plan.dependencies.map((dep, idx) => {
      const isCriticalEdge =
        criticalPathSet.has(dep.predecessor_id) && criticalPathSet.has(dep.successor_id);

      return {
        id: `e-${dep.predecessor_id}-${dep.successor_id}-${idx}`,
        source: dep.predecessor_id,
        target: dep.successor_id,
        type: 'smoothstep',
        animated: isCriticalEdge,
        className: isCriticalEdge ? 'critical-edge' : '',
        style: {
          stroke: isCriticalEdge ? '#ef4444' : '#64748b',
          strokeWidth: isCriticalEdge ? 3 : 1.5,
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          width: 14,
          height: 14,
          color: isCriticalEdge ? '#ef4444' : '#64748b',
        },
      };
    });

    return getLayoutedElements(rawNodes, rawEdges);
  }, [plan, schedule, membersMap, criticalPathSet]);

  if (!plan || nodes.length === 0) {
    return (
      <div className="glass-panel mx-6 flex h-[480px] flex-col items-center justify-center rounded-2xl p-8 text-center">
        <CheckSquare className="h-12 w-12 text-slate-600 mb-3" />
        <h3 className="font-display text-base font-bold text-slate-300">No Plan Tasks Available</h3>
        <p className="mt-1 max-w-sm text-xs text-slate-500">
          Create a project plan or use the AI Goal Assistant to generate a deterministic task DAG.
        </p>
      </div>
    );
  }

  return (
    <div className="relative mx-6 h-[540px] rounded-2xl glass-panel overflow-hidden border border-slate-800">
      {/* Graph Toolbar / Legend */}
      <div className="absolute top-4 left-4 z-10 flex flex-wrap items-center gap-3 rounded-xl bg-slate-900/90 p-2.5 backdrop-blur-md border border-slate-800 shadow-xl text-xs">
        <div className="flex items-center gap-1.5 font-semibold text-slate-200">
          <Calendar className="h-4 w-4 text-indigo-400" />
          <span>CPM Dependency DAG</span>
        </div>
        <div className="h-4 w-px bg-slate-800" />
        <div className="flex items-center gap-1.5 text-rose-400">
          <Flame className="h-3.5 w-3.5 text-rose-500 animate-pulse" />
          <span className="font-medium">Critical Path:</span>
          <span className="font-bold">{schedule?.critical_path?.length ?? 0} tasks</span>
        </div>
        <div className="h-4 w-px bg-slate-800" />
        <div className="flex items-center gap-1 text-slate-400">
          <Clock className="h-3.5 w-3.5 text-indigo-400" />
          <span>Finish:</span>
          <span className="font-medium text-slate-200">{schedule?.project_finish_date || 'N/A'}</span>
        </div>
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.2}
        maxZoom={1.8}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={20} size={1} color="#334155" />
        <Controls className="!border-slate-800 !bg-slate-900" />
        <MiniMap
          nodeColor={(n) => {
            if ((n.data as unknown as CustomTaskNodeData)?.isCritical) return '#ef4444';
            return '#6366f1';
          }}
          className="!rounded-lg !border !border-slate-800 !bg-slate-950/80"
          maskColor="rgba(2, 6, 23, 0.7)"
        />
      </ReactFlow>
    </div>
  );
};
