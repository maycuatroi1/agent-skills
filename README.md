# agent-skills

Skill dùng chung cho Claude Code, sync giữa các máy qua git.

Skill nằm ở đây, không nằm trong `~/.claude/skills/`. `install.sh` symlink chúng vào
đó để Claude Code thấy được, nên sửa skill là sửa thẳng trong repo này và commit.

## Trên máy mới

```bash
git clone <remote> ~/git/agent-skills
~/git/agent-skills/install.sh
```

Mở lại Claude Code để nạp skill.

## Sau khi sửa skill

```bash
cd ~/git/agent-skills
git add -A && git commit -m "..." && git push
```

Máy khác: `git pull` là xong, symlink đã trỏ sẵn vào repo nên không cần chạy lại
`install.sh` (trừ khi thêm skill mới).

## Skill hiện có

| Skill | Dùng khi |
|---|---|
| `manim-explainer-video` | Làm video giải thích kỹ thuật bằng Manim, tiếng Việt, kèm script + phụ đề timecode |

## Thêm skill mới

Tạo thư mục có `SKILL.md` (frontmatter `name` + `description` với trigger phrase cụ thể),
rồi chạy lại `install.sh`.
