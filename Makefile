.PHONY: help build up down restart logs ps stop start clean

help:
	@echo "Docker Multi-Container gRPC Health Check System"
	@echo ""
	@echo "Available targets:"
	@echo "  make build    - Build all Docker images"
	@echo "  make up       - Start all services"
	@echo "  make down     - Stop and remove all services"
	@echo "  make start    - Run start.sh (smart rebuild)"
	@echo "  make stop     - Stop all services"
	@echo "  make restart  - Restart all services"
	@echo "  make logs     - View logs from all services"
	@echo "  make ps       - Show running containers"
	@echo "  make clean    - Remove all containers, images, and cache"

build:
	docker-compose build

up:
	docker-compose -f docker-compose-extended.yml up -d

down:
	docker-compose -f docker-compose-extended.yml down 2>/dev/null || docker-compose down 2>/dev/null || true

start:
	./start.sh

stop:
	docker-compose -f docker-compose-extended.yml stop 2>/dev/null || docker-compose stop 2>/dev/null || true

restart: down up

logs:
	docker-compose -f docker-compose-extended.yml logs -f

ps:
	docker-compose -f docker-compose-extended.yml ps

clean: down
	docker-compose rm -f
	docker rmi -f tiler-v3_static-tiler tiler-v3_controller tiler-v3_apphost tiler-v3_apphost1 tiler-v3_apphost2 tiler-v3_apphost3 tiler-v3_apphost4 2>/dev/null || true
	rm -f .build_cache docker-compose-extended.yml
