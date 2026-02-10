# 🚂 Railway Deployment - Quick Start Guide

## Step-by-Step: Deploy Your Video Downloader to Railway

### ✅ What You'll Get
- A live URL like: `video-downloader.up.railway.app`
- Access from ANY device (phone, tablet, laptop)
- No need to keep your PC running
- Works just like a real website!

---

## 📋 Prerequisites

You need these 6 files (all provided):
- ✅ `backend.py`
- ✅ `video-downloader.html`
- ✅ `requirements.txt`
- ✅ `Procfile`
- ✅ `runtime.txt`
- ✅ `README.md` (optional)

---

## 🚀 Deployment Steps

### Step 1: Create a GitHub Account (if you don't have one)

1. Go to https://github.com
2. Click "Sign up"
3. Create your free account

### Step 2: Create a New Repository

1. Click the **"+"** icon (top right) → "New repository"
2. Repository name: `video-downloader`
3. Description: "Video downloader with quality selection"
4. Choose **Public** (required for free Railway)
5. Click "Create repository"

### Step 3: Upload Your Files to GitHub

**Option A: Via Web Interface (Easiest)**

1. On your new repository page, click "uploading an existing file"
2. Drag and drop ALL 6 files:
   - `backend.py`
   - `video-downloader.html`
   - `requirements.txt`
   - `Procfile`
   - `runtime.txt`
   - `README.md`
3. Click "Commit changes"

**Option B: Via GitHub Desktop (If you prefer)**

1. Download GitHub Desktop from https://desktop.github.com
2. Clone your repository
3. Copy all 6 files into the folder
4. Commit and push

### Step 4: Deploy to Railway

1. Go to https://railway.app
2. Click **"Start a New Project"**
3. Click **"Deploy from GitHub repo"**
4. Sign in with GitHub (authorize Railway)
5. Select your `video-downloader` repository
6. Railway will automatically:
   - ✅ Detect it's a Python app
   - ✅ Read `requirements.txt`
   - ✅ Install all dependencies
   - ✅ Install Playwright and Chromium
   - ✅ Start your app!

### Step 5: Generate Your Public URL

1. Wait for deployment to complete (5-10 minutes first time)
2. Click on your project
3. Go to **"Settings"** tab
4. Scroll to **"Domains"** section
5. Click **"Generate Domain"**
6. You'll get a URL like: `video-downloader-production.up.railway.app`

### Step 6: Test It!

1. Copy your Railway URL
2. Open it on your phone or any device
3. Paste a video URL
4. Click "Fetch Video Info"
5. Download your video! 🎉

---

## 🔧 Troubleshooting

### "Build Failed" or "Deployment Failed"

**Check these:**

1. **All 6 files uploaded?** Make sure you didn't miss `Procfile` or `runtime.txt`
2. **Files in root directory?** They should NOT be in a subfolder
3. **Repository is Public?** Railway free tier requires public repos

**Fix:** Re-upload missing files to GitHub, Railway auto-deploys when you push changes

### "Application Error" When Opening URL

**This usually means Playwright didn't install correctly**

**Fix:** Add a build script

1. Go to your Railway project
2. Settings → Build
3. Under "Build Command", add:
   ```
   pip install -r requirements.txt && playwright install-deps && playwright install chromium
   ```
4. Redeploy

### App Works But "No Video URLs Found"

**This is normal for some videos!** Try:
- Different video URLs
- Public videos (not premium/restricted)
- Wait 15-20 seconds for Playwright to load

### Slow First Load

**This is normal!** First request after deployment can take 10-20 seconds because:
- Playwright starts a browser
- Server "cold starts"

After first use, it's much faster!

---

## 💰 Railway Free Tier Limits

Railway's free tier gives you:
- ✅ $5 credit per month (renews monthly)
- ✅ Enough for ~500 hours of runtime
- ✅ Perfect for personal use!

**Tips to stay within limits:**
- App auto-sleeps when not in use (free!)
- Only active when someone is using it
- Monitor usage in Railway dashboard

---

## 🎯 Advanced: Custom Domain (Optional)

Want `videodownloader.com` instead of Railway URL?

1. Buy a domain (NameCheap, GoDaddy, Google Domains)
2. In Railway Settings → Domains
3. Click "Custom Domain"
4. Enter your domain
5. Update DNS records as Railway instructs
6. Done! Now you have a pro domain 😎

---

## 📱 Using Your App

Once deployed, share your Railway URL with anyone!

**On Mobile:**
1. Open your Railway URL
2. Paste video link
3. Click "Fetch Video Info"
4. Select quality
5. Download!

**On Desktop:**
Same thing! Works everywhere!

---

## 🔄 Updating Your App

Need to make changes?

1. Edit files in your GitHub repo
2. Commit changes
3. Railway automatically redeploys!

That's it! Railway watches your GitHub repo and updates automatically.

---

## ✨ You're All Set!

Your video downloader is now:
- ✅ Live on the internet
- ✅ Accessible from any device
- ✅ Works like a real website
- ✅ Automatically maintained

**Your Railway URL is your new website!** Share it, bookmark it, use it anywhere! 🎉

---

## 🆘 Need Help?

- Railway Docs: https://docs.railway.app
- Railway Discord: Great community support
- Check Railway logs: Click your project → "Deployments" → Click latest → "View Logs"

Good luck! 🚀
