
"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

export type Task = {
  id: string;
  title: string;
  completed: boolean;
  priority: "Low" | "Medium" | "High";
  deadline: string;
};

type TaskContextType = {
  tasks: Task[];
  addTask: (task: Omit<Task, "id">) => void;
  updateTask: (id: string, updates: Partial<Task>) => void;
  deleteTask: (id: string) => void;
  toggleTask: (id: string) => void;
};

const initialTasks: Task[] = [
  {
    id: "1",
    title: "Membaca materi AI",
    completed: false,
    priority: "Medium",
    deadline: "2026-11-10",
  },
  {
    id: "2",
    title: "Mengerjakan latihan soal",
    completed: false,
    priority: "High",
    deadline: "2026-11-12",
  },
  {
    id: "3",
    title: "Membuat ringkasan",
    completed: true,
    priority: "Low",
    deadline: "2026-11-15",
  },
];

const TaskContext = createContext<TaskContextType | undefined>(
  undefined
);

export function TaskProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [tasks, setTasks] = useState<Task[]>(initialTasks);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("gradatim-tasks");

      if (saved) {
        const parsed: unknown = JSON.parse(saved);

        if (Array.isArray(parsed)) {
          setTasks(parsed as Task[]);
        }
      }
    } catch (error) {
      console.error("Gagal membaca data tugas:", error);
    } finally {
      setLoaded(true);
    }
  }, []);

  useEffect(() => {
    if (!loaded) return;

    try {
      localStorage.setItem(
        "gradatim-tasks",
        JSON.stringify(tasks)
      );
    } catch (error) {
      console.error("Gagal menyimpan data tugas:", error);
    }
  }, [tasks, loaded]);

  function addTask(task: Omit<Task, "id">) {
    setTasks((previous) => [
      ...previous,
      {
        ...task,
        id: crypto.randomUUID(),
      },
    ]);
  }

  function updateTask(id: string, updates: Partial<Task>) {
    setTasks((previous) =>
      previous.map((task) =>
        task.id === id ? { ...task, ...updates } : task
      )
    );
  }

  function deleteTask(id: string) {
    setTasks((previous) =>
      previous.filter((task) => task.id !== id)
    );
  }

  function toggleTask(id: string) {
    setTasks((previous) =>
      previous.map((task) =>
        task.id === id
          ? { ...task, completed: !task.completed }
          : task
      )
    );
  }

  return (
    <TaskContext.Provider
      value={{
        tasks,
        addTask,
        updateTask,
        deleteTask,
        toggleTask,
      }}
    >
      {children}
    </TaskContext.Provider>
  );
}

export function useTasks() {
  const context = useContext(TaskContext);

  if (!context) {
    throw new Error(
      "useTasks harus digunakan di dalam TaskProvider"
    );
  }

  return context;
}
