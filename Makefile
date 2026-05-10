.PHONY: up down build clean

# Start the app — kills any local Python process on port 5000 first
up:
	-@powershell -Command "\$$pid = (netstat -ano | findstr ':5000 ') -match 'LISTENING' | ForEach-Object { (\$$_ -split '\s+')[-1] } | Select-Object -First 1; if (\$$pid) { Write-Host \"Killing process \$$pid on port 5000\"; taskkill /PID \$$pid /F }"
	docker compose up

# Start with a full rebuild (use after changing code)
build:
	docker compose up --build

# Start with a completely clean rebuild (use after changing Dockerfile or .dockerignore)
rebuild:
	docker compose build --no-cache
	docker compose up

# Stop the app
down:
	docker compose down
