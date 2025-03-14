"use client";

import { useState } from "react";
import Dashboard from "@/Components/Dashboard/Dashboard";
import Navbar from "@/Components/Navbar/Navbar";

export default function Home() {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <div className="h-screen flex overflow-hidden">
      {/* Sidebar Navbar */}
      <Navbar isCollapsed={isCollapsed} />

      {/* Main Dashboard */}
      <div className="flex-1 h-screen overflow-auto">
        <Dashboard onToggle={() => setIsCollapsed((prev) => !prev)} />
      </div>
    </div>
  );
}
