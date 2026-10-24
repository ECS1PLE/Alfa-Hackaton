"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { useClient } from "@/src/providers/ClientProvider";
import PageHeader from "@/src/components/PageHeader/PageHeader";
import FilterPills from "@/src/components/UI/FilterPills/FilterPills";
import InsightCard from "@/src/components/Insights/InsightCard/InsightCard";
import EmptyFeed from "@/src/components/Insights/EmptyFeed/EmptyFeed";
import DailyDigest from "@/src/components/Feed/DailyDigest/DailyDigest";
import FeedSidebar from "@/src/components/Feed/FeedSidebar/FeedSidebar";
import styles from "@/src/styles/Design.module.css";

const Feed = () => {
  const { client, events, allEvents } = useClient();
  const [kind, setKind] = useState("all");
  const [category, setCategory] = useState("all");
  const [period, setPeriod] = useState("7");
  const params = useSearchParams();
  const query = (params.get("q") ?? "").toLowerCase();
  const categories = [...new Set(events.map((event) => event.cat))];
  const activeCategory = categories.includes(category) ? category : "all";
  const low = allEvents.filter(
    (event) => !events.some((visible) => visible.id === event.id),
  );
  const list = events.filter(
    (event) =>
      (kind === "all" || event.p.kind === kind) &&
      (activeCategory === "all" || event.cat === activeCategory) &&
      (!query ||
        `${event.title} ${event.p.head} ${event.p.why}`
          .toLowerCase()
          .includes(query)) &&
      (period !== "today" || /сегодня|ч назад/.test(event.ago)),
  );

  return (
    <>
      <PageHeader
        title="Лента инсайтов"
        description={`${client.name} · ${events.length} значимых событий из 1 284 обработанных за 7 дней`}
      />
      <DailyDigest client={client} events={events} excluded={low.length} />
      <div className={styles.grid}>
        <section>
          <div className={styles["sec-h"]}>
            <FilterPills
              label="Тип события"
              value={kind}
              onChange={setKind}
              options={[
                { value: "all", label: "Все" },
                { value: "risk", label: "Риски" },
                { value: "opp", label: "Возможности" },
                { value: "watch", label: "Наблюдать" },
              ]}
            />
            <FilterPills
              label="Тема события"
              value={activeCategory}
              onChange={setCategory}
              options={[
                { value: "all", label: "Все темы" },
                ...categories.map((value) => ({ value, label: value })),
              ]}
            />
          </div>
          {query && (
            <p className={styles.muted}>
              Результаты поиска: «{params.get("q")}»
            </p>
          )}
          <div className={styles.feed}>
            {list.length ? (
              list.map((event) => <InsightCard key={event.id} event={event} />)
            ) : (
              <EmptyFeed />
            )}
          </div>
          <details>
            <summary>
              Низкая значимость для вашей компании ({low.length}) — показаны для
              прозрачности отбора
            </summary>
            <div className={`${styles.feed} ${styles.low}`}>
              {low.length ? (
                low.map((event) => <InsightCard key={event.id} event={event} />)
              ) : (
                <EmptyFeed text="Нет" />
              )}
            </div>
          </details>
        </section>
        <FeedSidebar period={period} onPeriodChange={setPeriod} />
      </div>
    </>
  );
};

export default Feed;
