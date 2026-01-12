# Deployment Guide - Proper Version Control

## The Problem We Had

- No version control on deployments
- Couldn't track what code was running when
- Couldn't easily rollback to working versions
- Confusion about what changed between deployments

## The Solution

### 1. Git-Based Versioning

**Every deployment must be tagged:**

```bash
# After making changes and testing locally
git add .
git commit -m "feat: add new feature X"
git tag -a v1.0.5 -m "Release 1.0.5: Feature X"
git push origin main --tags
```

**Tag naming convention:**
- `v1.0.x` - Patch (bug fixes, no new features)
- `v1.x.0` - Minor (new features, backward compatible)
- `vx.0.0` - Major (breaking changes)

### 2. Deployment Workflow

**Option A: Automated (Recommended)**
1. Push code with tag to GitHub
2. GitHub Actions automatically builds and deploys
3. Deployment is tagged with version number
4. Can rollback by tag name

**Option B: Manual**
```bash
# Tag the release
git tag -a v1.0.5 -m "Release 1.0.5"

# Deploy with version tag
./deploy_versioned.sh v1.0.5
```

### 3. Rollback Process

**By version tag:**
```bash
# List available versions
gcloud run revisions list --service=quant-engine-hl --region=us-central1

# Rollback to specific version
gcloud run services update-traffic quant-engine-hl \
  --region us-central1 \
  --to-tags v1.0.4=100
```

**By git commit:**
```bash
# Find the working commit
git log --oneline

# Checkout that commit
git checkout abc1234

# Deploy
./deploy_versioned.sh v1.0.4-hotfix
```

### 4. What to Version Control

**DO commit:**
- ✅ Source code (`.py` files)
- ✅ Configuration files (`.env.template`, `Dockerfile`)
- ✅ Documentation (`.md` files)
- ✅ Deployment scripts (`.sh` files)

**DON'T commit:**
- ❌ Trained models (`.pkl`, `.json` model files) - too large
- ❌ Secrets (`.env` with actual keys)
- ❌ Logs (`logs/` directory)
- ❌ Data files (`*.csv`, `*.json` data)

**For models:** Use Cloud Storage or model registry
```bash
# Upload models to Cloud Storage
gsutil cp models/*.pkl gs://your-bucket/models/v1.0.5/

# Download during deployment
gsutil cp gs://your-bucket/models/v1.0.5/*.pkl models/
```

### 5. Deployment Checklist

Before deploying:
- [ ] All changes committed to git
- [ ] Version tag created
- [ ] Local tests passed (`python3 pre_deploy_check.py`)
- [ ] Models uploaded to Cloud Storage (if changed)
- [ ] Deployment notes added to `CHANGELOG.md`

After deploying:
- [ ] Health check passed
- [ ] Logs show no errors
- [ ] Test trade executed successfully
- [ ] Document deployment in `deployments.log`

### 6. Emergency Rollback

If something breaks in production:

```bash
# Quick rollback to last known good version
./rollback.sh

# Or manually
gcloud run services update-traffic quant-engine-hl \
  --region us-central1 \
  --to-revisions quant-engine-hl-00005-hx4=100
```

### 7. Current Status

**Active Revision:** `quant-engine-hl-00005-hx4`  
**Git Tag:** (not tagged - this is the problem!)  
**Deployed:** Jan 8, 2026 23:11 UTC

**Action Required:**
1. Tag the current working code as `v1.0.0`
2. Set up GitHub Actions for future deployments
3. Never deploy without a version tag again

## Example Workflow

```bash
# 1. Make changes
vim quant_engine.py

# 2. Test locally
python3 pre_deploy_check.py

# 3. Commit with semantic message
git add quant_engine.py
git commit -m "fix: exclude hurst from model features"

# 4. Tag the release
git tag -a v1.0.1 -m "Fix: Feature shape mismatch"

# 5. Push to GitHub
git push origin main --tags

# 6. GitHub Actions deploys automatically
# OR deploy manually:
./deploy_versioned.sh v1.0.1

# 7. Verify deployment
curl https://quant-engine-hl-xxx.run.app/health

# 8. Monitor logs
python3 monitor_cloud.py
```

## Never Again

With this workflow:
- ✅ Every deployment is traceable
- ✅ Easy rollback to any version
- ✅ Clear history of what changed when
- ✅ No more confusion about "what code is running?"
