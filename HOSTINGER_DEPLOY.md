# Hostinger Custom PHP/HTML Deployment Guide (venue-orbit.com)

This document outlines the steps to deploy the PHP-wrapped **Venue Orbit** web application to Hostinger Shared Hosting via GitHub integration.

---

## 📡 Step 1: Link GitHub to Hostinger

1. Log into your **Hostinger hPanel**.
2. Go to **Websites** ➔ Click **Manage** next to `venue-orbit.com`.
3. In the left sidebar, click **Advanced** ➔ **Git**.
4. Link your GitHub account and select your `10_Venue_Orbit` repository (branch `main`).
5. Set the **Install Directory** to `public_html`.
6. Click **Deploy**. Hostinger will pull all files including `index.php` and the database `venue_orbit.db` into the public folder.

---

## ⏰ Step 2: Automating the Scraper Daily (Cron Job)

To keep your event listings up to date, schedule the python scraper to run once a day:
1. Go to **Advanced** ➔ **Cron Jobs** in the hPanel sidebar.
2. Under **Create a new Cron Job**, select custom settings:
   * **Command:** `cd /home/uXXXXXXX/domains/venue-orbit.com/public_html && python3 src/aggregator.py`
     *(Note: Replace `uXXXXXXX` with your actual Hostinger username found at the top of your dashboard, or use the absolute path shown in your file manager).*
   * **Common Settings:** **Once a day** (e.g. 2:00 AM).
3. Save the Cron Job.

---

🎉 Your website is now live and self-updating on **[http://venue-orbit.com](http://venue-orbit.com)**!
