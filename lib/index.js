/**
 * 把 material-to-book 这份技能作为「组合包内嵌技能」注册进 DSH。
 *
 * @module dsh-skill-material-to-book
 */

import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

/** 技能名：与 `~/.dsh/skills/material-to-book` 同名，两个来源只有一份会生效。 */
const SKILL_NAME = "material-to-book";

/** 提供者标识，出现在 `<skill_content>` 的来源信息里。 */
const PROVIDER_NAME = "material-to-book-bundled";

/** 技能本体所在目录（包根），模型按这个绝对路径去找 scripts/ 与 references/。 */
const RESOURCE_BASE = {
	kind: "directory",
	path: fileURLToPath(new URL("../", import.meta.url))
};

/** SKILL.md 的位置；正文与 frontmatter 都在这里。 */
const SKILL_FILE = new URL("../SKILL.md", import.meta.url);

/** 打包技能的标准优先级（与 @deepseek-ai/dsh-skill 的 BUNDLED_SKILL_RANK 一致）。 */
const BUNDLED_SKILL_RANK = 600;

/** frontmatter 整体匹配。 */
const FRONTMATTER = /^---\r?\n([\s\S]*?)\r?\n---\r?\n/u;

/**
 * 拆出 SKILL.md 的 frontmatter 与正文。
 *
 * @param text - SKILL.md 全文。
 * @returns `data` 为顶层标量键值，`body` 为去掉 frontmatter 的正文。
 */
function parseFrontmatter(text) {
	const match = FRONTMATTER.exec(text);
	if (match === null) return { data: {}, body: text };
	const data = {};
	for (const line of match[1].split(/\r?\n/u)) {
		if (line === "" || /^\s/u.test(line)) continue; // 跳过 metadata: 下面的缩进行
		const colon = line.indexOf(":");
		if (colon <= 0) continue;
		const key = line.slice(0, colon).trim();
		const value = line
			.slice(colon + 1)
			.trim()
			.replace(/^["']|["']$/gu, "");
		if (key !== "" && value !== "") data[key] = value;
	}
	return { data, body: text.slice(match[0].length) };
}

/** 读一次、缓存住，避免每次列技能都读盘。 */
let cached = null;

/**
 * 读取并解析 SKILL.md。
 *
 * @returns frontmatter 数据与正文。
 */
async function loadSkill() {
	if (cached !== null) return cached;
	cached = parseFrontmatter(await readFile(SKILL_FILE, "utf8"));
	return cached;
}

/**
 * 组装技能摘要。description 与 whenToUse 直接来自 SKILL.md，改技能说明不用改插件。
 *
 * @param data - SKILL.md 的 frontmatter。
 * @returns 提供给技能注册表的候选项。
 */
function candidate(data) {
	return {
		name: SKILL_NAME,
		description: data.description ?? "把一文件夹资料整理成一本可印刷的讲义。",
		...(data.whenToUse === undefined ? {} : { whenToUse: data.whenToUse }),
		invocation: { modelInvocable: true, userInvocable: true },
		provider: PROVIDER_NAME,
		source: "bundled",
		resourceBase: RESOURCE_BASE,
		rank: BUNDLED_SKILL_RANK,
		locator: SKILL_FILE
	};
}

/** 技能提供者：`list` 报摘要，`get` 按需读全文。 */
const provider = {
	name: PROVIDER_NAME,
	async list() {
		return [candidate((await loadSkill()).data)];
	},
	async get() {
		const { data, body } = await loadSkill();
		const summary = candidate(data);
		return {
			name: summary.name,
			description: summary.description,
			...(summary.whenToUse === undefined ? {} : { whenToUse: summary.whenToUse }),
			invocation: summary.invocation,
			provider: summary.provider,
			source: summary.source,
			resourceBase: summary.resourceBase,
			content: body
		};
	}
};

/** Cordis 插件名。 */
const name = "skill-material-to-book";

/** 依赖 `skills` 服务。 */
const inject = ["skills"];

/**
 * 把内嵌技能注册到 `ctx.skills`。
 *
 * @param ctx - Cordis 上下文。
 */
function apply(ctx) {
	ctx.skills.registerProvider(() => provider);
}

export { apply, inject, name };
