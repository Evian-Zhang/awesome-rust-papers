# Awesome Rust Papers

A curated list of academic papers about the [Rust](https://www.rust-lang.org/) programming language.

See the web version at <https://evian-zhang.github.io/awesome-rust-papers/> for a far more interactive experience.

Subscribe via [RSS](https://evian-zhang.github.io/awesome-rust-papers/feed.xml) for new additions.

Papers are grouped by topic and ordered by year within each group. Contributions are welcome — see [CONTRIBUTING](./CONTRIBUTING.md).

All content-related paper data is collected by human (e.g., categories, tags, the tools that this paper compares or extends), and all data in this repository is checked manually by human. All data is guaranteed to be hallucination-free. If there is anything wrong, feel free to send an issue.

## Agents

This repository ships an [agent skill](./.agents/skills/analyzing-rust-papers/SKILL.md) that lets AI agents query the collection through the [`awesome_rust_papers`](./awesome_rust_papers) Python library. To use it, clone the repository and start your agent from the repository root:

```bash
git clone https://github.com/Evian-Zhang/awesome-rust-papers
cd awesome-rust-papers
```

Agents that discover skills under `.agents/skills/` will pick up `analyzing-rust-papers` automatically; for other agents, point them at the skill file or copy the directory into their skills folder. Then you can ask things like:

* Which papers in this collection cite RustBelt?
* Summarize the C-to-Rust translation papers from 2025–2026.
* How many papers were published each year, and which venues appear most often?
* Which papers on unsafe Rust are from 2025?

## Citation

```bibtex
<!-- CITATION -->
```

## Collection

<!-- PAPERS -->

## Related Projects

* [rust-unofficial/awesome-rust](https://github.com/rust-unofficial/awesome-rust)
* [BurtonQin/Awesome-Rust-Checker](https://github.com/BurtonQin/Awesome-Rust-Checker)

## License

This repository is licensed under [CC BY 4.0](./LICENSE).
