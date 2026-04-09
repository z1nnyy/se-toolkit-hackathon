# Project Plan

## Product Idea

- Product title: `Cava Menu Bot`
- End users: Innopolis University students, staff, and campus visitors who want to check the Cava cafe menu before going to the counter.
- Problem: during busy hours people often have to walk to Cava and stand near the counter just to see what is available.
- One-line product idea: a Telegram bot and admin panel that show the current Cava menu and let staff update it in real time.
- Core feature: instant access to the latest menu through Telegram, with staff-side editing through a protected web panel.

## Version 1

Version 1 focused on the minimum useful product:

- backend API for menu items and availability;
- SQLite database for persistent menu storage;
- Telegram bot that returns the current menu to end users;
- admin panel for staff to edit dishes, prices, and availability;
- local and Docker-based запуск for demonstration.

## Version 2

Version 2 turned the MVP into a more complete product:

- login and password protection for the admin panel;
- separate super-admin cabinet for managing staff accounts;
- bilingual menu fields and language switcher in the bot;
- menu image rendering for Telegram instead of plain long text;
- deleted dishes history and menu collection management for seasonal menus;
- one-command Docker deployment.

## Feedback Addressed In Version 2

The product was improved in the following directions:

- the editing workflow became safer because staff now log in with named accounts;
- the bot became easier to use because it switched from command-heavy interaction to buttons and an updatable menu message;
- menu content became more realistic because dishes support sections, multilingual names, and multiple price variants;
- deployment became easier because the whole product can run with `docker compose up --build`.

## Architecture

- `backend/`: `FastAPI + SQLModel`
- `bot/`: `aiogram`
- `frontend/`: `React + Vite`
- `compose.yaml`: single-command Docker deployment

## What Still Needs Manual Completion

- choose the final public deployment target;
- deploy the latest containerized version;
- record the 2-minute demo video;
- add the final public URLs and QR codes to the presentation.
