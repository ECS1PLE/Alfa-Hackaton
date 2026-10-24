"use client";

import { useState, type ReactNode } from "react";
import { usePathname } from "next/navigation";
import Sidebar from "./Sidebar/Sidebar";
import Topbar from "./Topbar/Topbar";
import styles from "@/src/styles/Design.module.css";

const AppShell = ({ children }: { children: ReactNode }) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const pathname = usePathname();

  return (
    <div className={styles.app}>
      <a className={styles.skipLink} href="#main-content">
        К содержимому
      </a>
      <Sidebar open={menuOpen} />
      <main className={styles.main} id="main-content">
        <Topbar onMenu={() => setMenuOpen(!menuOpen)} menuOpen={menuOpen} />
        <div className={styles.pageContent} key={pathname}>
          {children}
        </div>
      </main>
    </div>
  );
};

export default AppShell;
