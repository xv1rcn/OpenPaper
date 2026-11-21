<script setup lang="ts">
import KnowledgeGraph from "./KnowledgeGraph.vue";
import { computed } from "vue";
import type { Paper } from "@/lib/types";
import { libraryStatistics } from "@/lib/statistics";
import { readerUrl } from "@/lib/api";
const props = defineProps<{ papers: Paper[] }>();
const data = computed(() => libraryStatistics(props.papers));
const recent = computed(() =>
  [...props.papers]
    .sort((a, b) => b.added_at.localeCompare(a.added_at))
    .slice(0, 15),
);
function points(field: "cumulative" | "cumulativeRead") {
  const rows = data.value.months,
    max = Math.max(...rows.map((r) => r.cumulative), 1);
  return rows
    .map(
      (r, i) =>
        `${30 + (i * 640) / Math.max(rows.length - 1, 1)},${180 - (r[field] * 150) / max}`,
    )
    .join(" ");
}
const heatDays = computed(() => {
  if (!data.value.days.length) return [];
  const counts = new Map(data.value.days),
    end = new Date(data.value.days.at(-1)![0] + "T00:00:00Z");
  return Array.from({ length: 364 }, (_, i) => {
    const d = new Date(end);
    d.setUTCDate(end.getUTCDate() - 363 + i);
    const day = d.toISOString().slice(0, 10);
    return { day, count: counts.get(day) || 0 };
  });
});
</script>
<template>
  <div class="extended-statistics">
    <section>
      <h2>累计增长与阅读进度</h2>
      <p class="field-help">按加入月份统计当前已读数量，不代表实际阅读日期。</p>
      <svg
        v-if="data.months.length"
        viewBox="0 0 700 210"
        role="img"
        aria-label="累计加入和当前已读曲线"
        class="growth-chart"
      >
        <path
          d="M30 15V180H675"
          fill="none"
          stroke="currentColor"
          opacity=".25"
        />
        <polyline
          :points="points('cumulative')"
          fill="none"
          stroke="var(--accent)"
          stroke-width="3"
        />
        <polyline
          :points="points('cumulativeRead')"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-dasharray="5 4"
        />
        <text x="30" y="202">{{ data.months[0]?.month }}</text>
        <text x="670" y="202" text-anchor="end">
          {{ data.months.at(-1)?.month }}
        </text>
      </svg>
      <details>
        <summary>查看数值（实线：累计加入；虚线：当前已读）</summary>
        <table>
          <thead>
            <tr>
              <th>月份</th>
              <th>累计加入</th>
              <th>当前已读</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in data.months" :key="row.month">
              <th>{{ row.month }}</th>
              <td>{{ row.cumulative }}</td>
              <td>{{ row.cumulativeRead }}</td>
            </tr>
          </tbody>
        </table>
      </details>
    </section>
    <div class="stats-grid">
      <section>
        <h2>周新增量</h2>
        <p v-if="!data.weeks.length">暂无加入时间数据</p>
        <div v-for="[week, count] in data.weeks" :key="week" class="stat-bar">
          <span>{{ week }} 起</span
          ><meter
            min="0"
            :max="Math.max(...data.weeks.map((r) => r[1]), 1)"
            :value="count"
            :aria-label="week + ' 起新增 ' + count + ' 篇'"
          /><b>{{ count }}</b>
        </div>
      </section>
      <section>
        <h2>各标签阅读进度</h2>
        <div v-for="[tag, row] in data.tags" :key="tag" class="stat-bar">
          <span>{{ tag }}</span><meter
            min="0"
            :max="row.total"
            :value="row.read"
            :aria-label="tag + ' 已读 ' + row.read + '/' + row.total"
          /><b>{{ row.read }}/{{ row.total }}</b>
        </div>
      </section>
    </div>
    <section>
      <h2>加入热力图</h2>
      <p class="field-help">截至最近加入日期的 52 周</p>
      <div class="heatmap" v-if="heatDays.length">
        <span
          v-for="day in heatDays"
          :key="day.day"
          :title="day.day + '：' + day.count + ' 篇'"
          :aria-label="day.day + '：' + day.count + ' 篇'"
          :style="{
            background: day.count ? 'var(--accent)' : 'var(--read-background)',
            opacity: day.count ? Math.min(0.4 + day.count * 0.15, 1) : 0.4,
          }"
        />
      </div>
      <p v-else>暂无加入时间数据</p>
    </section>
    <section>
      <h2>标签 × 年份</h2>
      <div class="statistics-table">
        <table>
          <thead>
            <tr>
              <th>标签</th>
              <th v-for="year in data.years" :key="year">{{ year }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="[tag, row] in data.tags" :key="tag">
              <th>{{ tag }}</th>
              <td v-for="year in data.years" :key="year">
                {{ row.years[year] || "—" }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <KnowledgeGraph :papers="papers" />
    <section>
      <h2>近期新增</h2>
      <ul class="recent-papers">
        <li v-for="paper in recent" :key="paper.file_key">
          <a :href="readerUrl(paper)">{{ paper.title }}</a><time>{{
            paper.added_at.slice(0, 10)
          }}</time>
        </li>
      </ul>
    </section>
  </div>
</template>
