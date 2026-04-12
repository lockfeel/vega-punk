#!/usr/bin/env bash
# 将 agency-agents 中的 agent 文件内化为独立的 SKILL
# 用法: bash scripts/ingest-agency-agents.sh

set -euo pipefail

REPO_URL="https://github.com/msitarzewski/agency-agents.git"
CLONE_DIR="/tmp/agency-agents"
SKILLS_DIR="$HOME/.agents/skills"

echo "=== Agency Agents 内化脚本 ==="

# 1. 下载项目
if [ -d "$CLONE_DIR/.git" ]; then
    echo "[1/4] 更新已有仓库..."
    cd "$CLONE_DIR" && git pull --ff-only
else
    echo "[1/4] 克隆仓库..."
    rm -rf "$CLONE_DIR"
    git clone --depth 1 "$REPO_URL" "$CLONE_DIR"
fi

# 2. 遍历分类目录，转换为 SKILL.md 格式
echo "[2/4] 转换 agent 文件为 SKILL 格式..."

convert_file() {
    local src_file="$1"
    local category="$2"
    local filename
    filename=$(basename "$src_file" .md)

    # 从文件名提取 agent 名称 (去掉前缀)
    local agent_name
    agent_name=$(echo "$filename" | sed "s/^${category}-//")

    # 提取原文件的 frontmatter 内容 (仅第一对 --- 之间)
    local existing_name=""
    local existing_desc=""
    local in_frontmatter=false
    while IFS= read -r line; do
        if [[ "$line" == "---" ]]; then
            if [ "$in_frontmatter" = false ]; then
                in_frontmatter=true
                continue
            else
                break
            fi
        fi
        if [ "$in_frontmatter" = true ]; then
            if [[ "$line" =~ ^name:\ *(.*) ]]; then
                existing_name="${BASH_REMATCH[1]}"
                existing_name="${existing_name#\"}"
                existing_name="${existing_name%\"}"
                existing_name="${existing_name#\'}"
                existing_name="${existing_name%\'}"
            fi
            if [[ "$line" =~ ^description:\ *(.*) ]]; then
                existing_desc="${BASH_REMATCH[1]}"
                existing_desc="${existing_desc#\"}"
                existing_desc="${existing_desc%\"}"
                existing_desc="${existing_desc#\'}"
                existing_desc="${existing_desc%\'}"
            fi
        fi
    done < "$src_file"

    local skill_desc="${existing_desc:-$agent_name}"

    # 目标目录: ~/.agents/skills/{agent-name}/
    local target_dir="$SKILLS_DIR/$filename"
    mkdir -p "$target_dir"

    # 用 awk 跳过第一对 --- 之间的 yaml frontmatter，提取正文
    local body
    body=$(awk '
        BEGIN { fm=0; skip=1 }
        /^---$/ { fm++; if (fm==2) { skip=0; next } next }
        !skip { print }
    ' "$src_file")

    # 写入 SKILL.md
    {
        echo "---"
        echo "name: $filename"
        echo "description: $skill_desc"
        echo "license: MIT (from msitarzewski/agency-agents)"
        echo "---"
        echo ""
        echo "$body"
    } > "$target_dir/SKILL.md"

    echo "  -> $filename"
}

# 需要转换的分类 (跳过 scripts, examples, integrations, strategy)
CATEGORIES=(
    academic
    design
    engineering
    finance
    game-development
    marketing
    paid-media
    product
    project-management
    sales
    spatial-computing
    specialized
    support
    testing
)

total=0
for category in "${CATEGORIES[@]}"; do
    src_dir="$CLONE_DIR/$category"
    [ -d "$src_dir" ] || continue

    # 递归查找所有 .md 文件 (支持子目录)
    while IFS= read -r md_file; do
        [ -f "$md_file" ] || continue
        convert_file "$md_file" "$category"
        total=$((total + 1))
    done < <(find "$src_dir" -name "*.md" -type f | sort)
done

# 4. 在 ~/.openclaw/skills/ 下创建软链接
LINK_DIR="$HOME/.openclaw/skills"

echo "[3/4] 在 $LINK_DIR 创建软链接..."
mkdir -p "$LINK_DIR"

linked=0
for category in "${CATEGORIES[@]}"; do
    src_dir="$CLONE_DIR/$category"
    [ -d "$src_dir" ] || continue

    while IFS= read -r md_file; do
        [ -f "$md_file" ] || continue
        filename=$(basename "$md_file" .md)
        skill_target="$SKILLS_DIR/$filename"
        skill_link="$LINK_DIR/$filename"

        if [ -d "$skill_target" ]; then
            rm -rf "$skill_link" 2>/dev/null || true
            ln -s "$skill_target" "$skill_link"
            linked=$((linked + 1))
        fi
    done < <(find "$src_dir" -name "*.md" -type f | sort)
done

echo ""
echo "=== Done ==="
echo "Ingested: $total skills"
echo "Linked: $linked symlinks"
echo "Skills dir: $SKILLS_DIR"
ls -1 "$SKILLS_DIR" | sort
