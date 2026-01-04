# 🌳 Git Branching Strategy

## Branch Structure

### Main Branches

**`main`** - Production
- Production-ready code
- Auto-deploys to live trading bot
- Protected (requires PR approval)
- Only merge from `dev` after testing

**`dev`** - Development
- Integration branch
- Auto-deploys to paper trading bot
- Merge features here first
- Test before promoting to main

### Supporting Branches

**`feature/*`** - New Features
- Branch from: `dev`
- Merge to: `dev`
- Naming: `feature/description`
- Examples:
  - `feature/new-strategy`
  - `feature/risk-management`
  - `feature/dashboard-v2`

**`experiment/*`** - Experiments
- Branch from: `dev`
- Merge to: `dev` (if successful)
- Naming: `experiment/description`
- Examples:
  - `experiment/ml-optimization`
  - `experiment/new-indicators`
  - `experiment/backtesting`

**`hotfix/*`** - Emergency Fixes
- Branch from: `main`
- Merge to: `main` AND `dev`
- Naming: `hotfix/description`
- Examples:
  - `hotfix/tp-sl-fix`
  - `hotfix/data-validation`

## Workflow

### Creating a Feature
\`\`\`bash
git checkout dev
git pull origin dev
git checkout -b feature/my-feature
# ... make changes ...
git add .
git commit -m "feat: add my feature"
git push origin feature/my-feature
# Create PR to dev on GitHub
\`\`\`

### Creating an Experiment
\`\`\`bash
git checkout dev
git pull origin dev
git checkout -b experiment/my-experiment
# ... make changes ...
git add .
git commit -m "experiment: test new approach"
git push origin experiment/my-experiment
# Create PR to dev if successful
\`\`\`

### Hotfix
\`\`\`bash
git checkout main
git pull origin main
git checkout -b hotfix/critical-fix
# ... make changes ...
git add .
git commit -m "fix: critical bug"
git push origin hotfix/critical-fix
# Create PR to main (urgent)
# Then merge to dev as well
\`\`\`

## Current Branches

- ✅ `main` - Production (live bot)
- ✅ `dev` - Development (paper bot)
- 📝 Create `feature/*` as needed
- 📝 Create `experiment/*` as needed

