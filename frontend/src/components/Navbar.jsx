import React from 'react';
import { Sparkles, Activity, User, LogOut, CheckCircle2, AlertCircle } from 'lucide-react';

export default function Navbar({ user, onOpenAuth, onLogout, healthStatus }) {
  return (
    <header className="border-b border-gray-800 bg-gray-950/80 backdrop-blur sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Sparkles className="w-5 h-5 text-gray-950 stroke-[2.5]" />
          </div>
          <div>
            <h1 className="font-bold text-lg text-white tracking-tight flex items-center gap-2">
              SkillReadiness <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">AI</span>
            </h1>
            <p className="text-xs text-gray-400 hidden sm:block">Intelligent Role Benchmark & Career Pathways</p>
          </div>
        </div>

        {/* Right Controls */}
        <div className="flex items-center gap-4">
          {/* Health status pill */}
          <div className="flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border bg-gray-900 border-gray-800">
            <span className={`w-2 h-2 rounded-full animate-pulse ${healthStatus.connected ? 'bg-emerald-500' : 'bg-amber-500'}`} />
            <span className="text-gray-300">
              {healthStatus.connected ? 'API & DB Ready' : (healthStatus.checked ? 'Connecting...' : 'API Connecting')}
            </span>
          </div>

          {/* User auth state */}
          {user ? (
            <div className="flex items-center gap-3 pl-2 border-l border-gray-800">
              <div className="flex items-center gap-2 text-sm text-gray-300">
                <div className="w-8 h-8 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-semibold text-xs border border-emerald-500/30">
                  {user.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
                </div>
                <span className="hidden md:inline font-medium text-white">{user.full_name}</span>
              </div>
              <button
                onClick={onLogout}
                className="p-1.5 rounded-lg text-gray-400 hover:text-rose-400 hover:bg-gray-900 transition"
                title="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </div>
          ) : (
            <button
              onClick={onOpenAuth}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium transition shadow-sm shadow-emerald-600/20"
            >
              <User className="w-4 h-4" />
              <span>Sign In / Register</span>
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
