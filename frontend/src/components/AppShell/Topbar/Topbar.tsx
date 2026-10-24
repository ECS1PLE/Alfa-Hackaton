"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { useClient } from "@/src/providers/ClientProvider";
import Avatar from "@/src/components/UI/Avatar/Avatar";
import Icon from "@/src/components/UI/Icon/Icon";
import styles from "@/src/styles/Design.module.css";

const Topbar = ({
  onMenu,
  menuOpen,
}: {
  onMenu: () => void;
  menuOpen: boolean;
}) => {
  const { client } = useClient();
  const [query, setQuery] = useState("");
  const router = useRouter();
  const handleSearch = (event: FormEvent) => {
    event.preventDefault();
    if (query.trim())
      router.push(`/feed?q=${encodeURIComponent(query.trim())}`);
  };

  return (
    <header className={styles.top}>
      <button
        className={styles.menuButton}
        onClick={onMenu}
        aria-label="Открыть навигацию"
        aria-expanded={menuOpen}
        aria-controls="main-navigation"
      >
        <Icon name="menu" />
      </button>
      <Link className={styles.co} href="/clients" title="Сменить клиента">
        <Avatar text={client.short} />
        <div>
          <b>{client.name}</b>
          <small>
            {client.id} · группа {client.group} · {client.groupSize} юрлица
          </small>
        </div>
        <span className={styles.muted}>▾</span>
      </Link>
      <form className={styles.search} onSubmit={handleSearch}>
        <Icon name="search" />
        <input
          aria-label="Поиск по новостям"
          placeholder="Поиск по платежам, контрагентам и новостям"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </form>
      <span className={styles.demo}>ДЕМО</span>
      <div className={styles.user}>
        <div>
          <b>{client.user.name}</b>
          <small>{client.user.role}</small>
        </div>
        <Avatar text={client.user.ini} background="var(--red)" />
      </div>
    </header>
  );
};

export default Topbar;
