
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../context/AuthContext";

export default function Register() {
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
        <div className="mb-8 text-center">
          <div className="mx-auto flex h-11 w-11 items-center justify-center rounded-xl bg-slate-900 text-lg font-semibold text-white">
            P
          </div>

          <h1 className="mt-6 text-2xl font-semibold">
            Create your account
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            Start managing your team and projects in one place.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          className="space-y-5 rounded-xl border border-slate-200 bg-white p-8 shadow-sm"
        >
          <div>
            <label htmlFor="register-name" className="mb-2 block text-sm font-medium">
              Full name
            </label>
            <input
              id="register-name"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Your full name"
              className="w-full rounded-lg border border-slate-300 px-4 py-3 text-sm outline-none"
            />
          </div>

          <div>
            <label htmlFor="register-email" className="mb-2 block text-sm font-medium">
              Email address
            </label>
            <input
              id="register-email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="w-full rounded-lg border border-slate-300 px-4 py-3 text-sm outline-none"
            />
          </div>

          <button
            type="submit"
            className="w-full rounded-lg bg-slate-900 py-3 text-sm font-medium text-white hover:bg-slate-700"
          >
            Create demo account
          </button>

          <p className="text-center text-xs text-slate-400">
            Prototype registration — no real account is created.
          </p>
        </form>

        <p className="mt-6 text-center text-sm text-slate-500">
          Already started?{" "}
          <Link to="/login" className="font-medium text-slate-900 underline">
            Sign in
          </Link>
        </p>
      </div>
    </main>
  );
}
