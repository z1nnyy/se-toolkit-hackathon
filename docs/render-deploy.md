# Render Deployment

## Why Render

Render gives web services a public `onrender.com` URL, supports Docker deployments, and supports persistent disks for paid web services.

## Important note about plans

For this project, `starter` or higher is the practical choice because:

- the Telegram bot should stay online continuously;
- the project uses `SQLite` and cached menu images on disk;
- free Render web services spin down after 15 minutes without inbound traffic and do not support persistent disks.

## Deploy steps

1. Push the repository to GitHub.
2. Sign in to Render.
3. Click `New` -> `Blueprint`.
4. Connect your GitHub account and select this repository.
5. Render will detect [render.yaml](/Users/z1nny/software-engineering-toolkit/se-toolkit-hackathon/render.yaml).
6. During setup, provide secrets:
   - `BOT_TOKEN`
   - `CAVA_SUPERADMIN_PASSWORD`
7. Confirm deploy.

## What you get

- public admin panel URL like `https://cava-menu-bot.onrender.com`
- backend API at the same domain
- Telegram bot running inside the same container

## After deploy

1. Open the public URL.
2. Log in with:
   - username: `owner`
   - password: the `CAVA_SUPERADMIN_PASSWORD` value you entered in Render
3. Open your Telegram bot and send `/start`.

## Updating the app

Every push to `main` can trigger an automatic redeploy on Render if auto-deploy is enabled for the service.
