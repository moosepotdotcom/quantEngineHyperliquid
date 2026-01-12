#!/bin/bash
# Complete GitHub Backup Push Script
# Username: moosepotdotcom
# Repository: quantEngineHyperliquid
# SSH URL: git@github.com:moosepotdotcom/quantEngineHyperliquid.git

set -e  # Exit on error

echo "🔥 Complete Backup Push to GitHub"
echo "=================================="
echo ""

# Navigate to repository
cd /Users/alifiyaa/Downloads/quantEngineHyperliquid

# Check if commit is complete
echo "📊 Checking repository status..."
git status

echo ""
echo "✅ Creating branches..."

# Create and name branches
git branch -M main
git checkout -b dev
git checkout -b staging
git checkout main

echo ""
echo "🔗 Adding GitHub remote (SSH)..."

# Remove existing remote if any
git remote remove origin 2>/dev/null || true

# Add SSH remote
git remote add origin git@github.com:moosepotdotcom/quantEngineHyperliquid.git

echo ""
echo "🚀 Pushing to GitHub..."
echo "Repository: git@github.com:moosepotdotcom/quantEngineHyperliquid.git"
echo "This will take a while due to large files (5.2GB)"
echo ""

# Push main branch
echo "📤 Pushing main branch..."
git push -u origin main --progress

# Push dev branch
echo "📤 Pushing dev branch..."
git push origin dev --progress

# Push staging branch
echo "📤 Pushing staging branch..."
git push origin staging --progress

echo ""
echo "🎉 SUCCESS! Complete backup pushed to GitHub!"
echo ""
echo "📊 Repository: https://github.com/moosepotdotcom/quantEngineHyperliquid"
echo "🔥 All 5.2GB backed up safely!"
echo ""
echo "Next steps:"
echo "1. Visit: https://github.com/moosepotdotcom/quantEngineHyperliquid"
echo "2. Verify all files are there"
echo "3. Set up branch protection (Settings → Branches)"
echo "4. Consider upgrading to GitHub Pro for more LFS storage"
echo ""
