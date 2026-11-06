# Ride Algeria — Mashwari Passenger App

Flutter Android passenger app for the Ride Algeria project.

## Build

The GitHub Actions workflow builds the passenger APK on pushes to `main` and can also be run manually from Actions. Configure repository secrets `SUPABASE_URL`, `SUPABASE_PUBLISHABLE_KEY`, and `MAP_TILE_URL` before building a connected app. Without them the APK opens a configuration notice and cannot request rides.
