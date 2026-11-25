# Migrating from a standalone job-search setup

For a user who already runs a personal project with its own skills, scripts and rules, and wants the plugin to take over without losing behaviour. The old project is only ever read.

1. **Inventory the rules.** List every rule your old `CLAUDE.md`, docs and skills enforce. Place each one using `docs/parity.md`: facts and numbers go to `profile.yaml`, prose rules to the workspace `docs/`. A rule with no home is a gap in the plugin: open an issue instead of keeping a private copy in a skill.
2. **Decide which side wins.** Old skills often lag behind the project docs. Treat the project docs as the reference and the old skills as history, and write the decision down.
3. **Create a new workspace** with `init-workspace` outside the old project. Copy (never move) the knowledge base, interview KBs, base CV, tracker and archived trackers. Point `tracker.archives` at the archived snapshots.
4. **Fill `profile.yaml`.** `python3 <plugin>/scripts/jobprofile.py --workspace . --json` shows the merged result; validation catches typos and unknown keys.
5. **Shadow-run on the same inputs.**
   - Tracker queries (`match`, `quiet`, `summary`): run the old and new scripts on the same tracker and diff the output. Expect identical lists.
   - Builds: build an old `spec.json` into a scratch folder with `build_application.py --cv --letter --verify` and compare the extracted PDF text.
   - Scoring and replies: analyse a few postings and draft a few replies with both setups; differences must trace to a rule the old skills got wrong, not to a missing rule.
6. **Hash the old project before and after** (`shasum` over its files) to prove the migration did not touch it.
7. **Cut over.** Back up the old skills directory, remove the duplicate skills so each trigger phrase has exactly one owner, and keep the old project archived. To roll back, restore the backup.

Known differences when comparing company matching: the plugin matches whole words, so a short name no longer matches inside an unrelated longer one. Expect fewer, more accurate hits than a character-ratio matcher.
