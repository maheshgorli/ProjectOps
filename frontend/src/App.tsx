
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import type { ReactNode } from "react";

import { AuthProvider } from "./context/AuthContext";
import { useAuth } from "./context/useAuth";

// Authentication
import Login from "./pages/auth/Login";
import Register from "./pages/auth/Register";

// Workspace
import Workspace from "./pages/Workspace";
import JoinTeam from "./pages/JoinTeam";

// Project onboarding
import CreateTeam from "./pages/CreateTeam";
import CreateProject from "./pages/CreateProject";
import AddMembers from "./pages/AddMembers";
import Requirements from "./pages/Requirements";
import AIPlan from "./pages/AIPlan";

// New role-based dashboard
import Dashboard from "./pages/dashboard/Dashboard";

// Protect pages from users who haven't signed in
function ProtectedRoute({
  children,
}: {
  children: ReactNode;
}) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f6f7f9] text-slate-500">
        <div className="text-sm">Loading session...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

// Redirect the homepage depending on login status
function HomeRedirect() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f6f7f9] text-slate-500">
        <div className="text-sm">Loading session...</div>
      </div>
    );
  }

  return (
    <Navigate
      to={user ? "/workspace" : "/login"}
      replace
    />
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>

          {/* Default homepage */}
          <Route
            path="/"
            element={<HomeRedirect />}
          />

          {/* Login and registration */}
          <Route
            path="/login"
            element={<Login />}
          />

          <Route
            path="/register"
            element={<Register />}
          />

          {/* Workspace selection */}
          <Route
            path="/workspace"
            element={
              <ProtectedRoute>
                <Workspace />
              </ProtectedRoute>
            }
          />

          <Route
            path="/join-team"
            element={
              <ProtectedRoute>
                <JoinTeam />
              </ProtectedRoute>
            }
          />

          {/* Team setup */}
          <Route
            path="/create-team"
            element={
              <ProtectedRoute>
                <CreateTeam />
              </ProtectedRoute>
            }
          />

          {/* Project setup */}
          <Route
            path="/create-project"
            element={
              <ProtectedRoute>
                <CreateProject />
              </ProtectedRoute>
            }
          />

          {/* Team members */}
          <Route
            path="/add-members"
            element={
              <ProtectedRoute>
                <AddMembers />
              </ProtectedRoute>
            }
          />

          {/* Project requirements */}
          <Route
            path="/requirements"
            element={
              <ProtectedRoute>
                <Requirements />
              </ProtectedRoute>
            }
          />

          {/* Project plan */}
          <Route
            path="/ai-plan"
            element={
              <ProtectedRoute>
                <AIPlan />
              </ProtectedRoute>
            }
          />

          {/* Dashboard */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />

          {/* Unknown URLs */}
          <Route
            path="*"
            element={<HomeRedirect />}
          />

        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
