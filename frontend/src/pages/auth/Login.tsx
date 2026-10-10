
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();

    if (!name.trim() || !email.trim()) return;

    login(name, email);
    navigate("/workspace");
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#f6f7f9] px-5 text-slate-900">
      <div className="w-full max-w-md">
        <div className="mb-10 text-center">
          <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-slate-900 text-lg font-semibold text-white">
            P
          </div>

          <h1 className="mt-6 text-2xl font-semibold tracking-tight">
            Welcome to ProjectOps
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            Organize your team. Keep your projects moving.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="space-y-5 rounded-xl border border-slate-200 bg-white p-8 shadow-sm"
        >
          <div>
            <label htmlFor="name" className="mb-2 block text-sm font-medium">
              Your name
            </label>

            <input
              id="name"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Enter your name"
              className="w-full rounded-lg border border-slate-300 px-4 py-3 text-sm outline-none focus:border-slate-700"
            />
          </div>

          <div>
            <label htmlFor="email" className="mb-2 block text-sm font-medium">
              Email address
            </label>

            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full rounded-lg border border-slate-300 px-4 py-3 text-sm outline-none focus:border-slate-700"
            />
          </div>

          <button
            type="submit"
            className="w-full rounded-lg bg-slate-900 py-3 text-sm font-medium text-white transition hover:bg-slate-700"
          >
            Continue
          </button>

          <p className="text-center text-xs text-slate-400">
            Frontend demo only — no identity verification.
          </p>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500">
          New to ProjectOps?{" "}
          <Link to="/register" className="font-medium text-slate-900 underline">
            Get started
          </Link>
        </p>
      </div>
    </main>
  );
}
