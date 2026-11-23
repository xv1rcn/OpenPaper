import { describe, expect, it } from "vitest";
import { createSSRApp, h } from "vue";
import { renderToString } from "vue/server-renderer";
import TechnicalRead from "./TechnicalRead.vue";
import StructuredRead from "./StructuredRead.vue";
describe("reading presentation", () => {
  it("retains prose, source pages and evidence limitations without nested cards", async () => {
    const html = await renderToString(
      createSSRApp({
        render: () =>
          h(TechnicalRead, {
            value: {
              summary: "总览",
              modules: [
                {
                  name: "标题索引",
                  role: "加速查询",
                  mechanism: "精确匹配",
                  technical_explanation: "每次查找使用字典",
                  terms: ["哈希"],
                  page_refs: [2, 2, -1],
                },
              ],
              terms: [
                {
                  term: "哈希",
                  explanation: "映射键值",
                  paper_context: "用于索引",
                  basis: "general_background",
                },
              ],
              missing_details: ["未报告内存开销"],
            },
          }),
      }),
    );
    expect(html).toContain("<h3>标题索引</h3>");
    for (const text of [
      "每次查找使用字典",
      "未报告内存开销",
      "背景知识",
      "用于索引",
    ])
      expect(html).toContain(text);
    expect(html.match(/第 2 页/g)).toHaveLength(1);
    for (const text of [
      "technical_explanation",
      'class="reading-record"',
      "<dt>名称</dt>",
      " open",
    ])
      expect(html).not.toContain(text);
  });
  it("supports text caches and omits empty supplemental sections", async () => {
    const html = await renderToString(
      createSSRApp({
        render: () => h(TechnicalRead, { value: "旧版技术说明" }),
      }),
    );
    expect(html).toContain("旧版技术说明");
    expect(html).not.toContain("术语解释");
    expect(html).not.toContain("尚未交代的细节");
  });
  it("orders records consistently and retains false, zero and unknown fields", async () => {
    const html = await renderToString(
      createSSRApp({
        render: () =>
          h(StructuredRead, {
            value: [
              {
                result: "实验结果",
                custom: false,
                scale: 0,
                description: "方法说明",
                name: "对照方法",
              },
            ],
          }),
      }),
    );
    expect(html).toContain("reading-record-list");
    expect(html).toContain('class="reading-record-title">对照方法</h4>');
    expect(html.indexOf("方法说明")).toBeLessThan(html.indexOf("实验结果"));
    expect(html).toContain("false");
    expect(html).toContain(">0</p>");
  });
});
