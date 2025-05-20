#!/bin/bash

# Docker Compose Helper Script for VeriFact
# This script provides simplified commands for managing VeriFact with Docker Compose

set -e

# Default environment
ENV="dev"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
RESET='\033[0m'

# Help text
show_help() {
    echo -e "${BLUE}VeriFact Docker Compose Helper${RESET}"
    echo
    echo "Usage: $0 [options] COMMAND"
    echo
    echo "Options:"
    echo "  -e, --env ENV    Specify environment (dev, prod) [default: dev]"
    echo "  -h, --help       Show this help message"
    echo
    echo "Commands:"
    echo "  up               Start all services"
    echo "  down             Stop and remove all containers"
    echo "  restart          Restart all services"
    echo "  logs             View logs from all services"
    echo "  ps               List running containers"
    echo "  api              Start only the API service"
    echo "  ui               Start only the UI service"
    echo "  db               Start only the database service"
    echo "  redis            Start only the Redis service"
    echo "  api-logs         View logs from the API service"
    echo "  ui-logs          View logs from the UI service"
    echo "  db-logs          View logs from the database service"
    echo "  redis-logs       View logs from the Redis service"
    echo "  prune            Remove all stopped containers, unused images and volumes"
    echo "  health           Check the health of all services"
    echo "  backup-db        Backup the database"
    echo "  restore-db       Restore the database from backup"
    echo
    echo "Examples:"
    echo "  $0 up                      # Start all services in development mode"
    echo "  $0 -e prod up              # Start all services in production mode"
    echo "  $0 logs                    # View logs from all services"
    echo "  $0 -e prod backup-db       # Backup the production database"
}

# Parse command line options
while [[ $# -gt 0 ]]; do
    case "$1" in
        -e|--env)
            ENV="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            break
            ;;
    esac
done

# Command validation
COMMAND=$1
if [[ -z "$COMMAND" ]]; then
    echo -e "${RED}Error: No command specified${RESET}"
    show_help
    exit 1
fi

# Environment validation
if [[ "$ENV" != "dev" && "$ENV" != "prod" ]]; then
    echo -e "${RED}Error: Invalid environment. Use 'dev' or 'prod'${RESET}"
    exit 1
fi

# Base docker-compose command
if [[ "$ENV" == "dev" ]]; then
    COMPOSE_CMD="docker-compose"
else
    COMPOSE_CMD="docker-compose -f docker-compose.yml -f docker-compose.prod.yml"
fi

# Execute command
case "$COMMAND" in
    up)
        echo -e "${GREEN}Starting VeriFact services in ${ENV} mode...${RESET}"
        $COMPOSE_CMD up -d
        ;;
    down)
        echo -e "${YELLOW}Stopping and removing VeriFact containers...${RESET}"
        $COMPOSE_CMD down
        ;;
    restart)
        echo -e "${YELLOW}Restarting VeriFact services...${RESET}"
        $COMPOSE_CMD restart
        ;;
    logs)
        echo -e "${BLUE}Showing logs for all services...${RESET}"
        $COMPOSE_CMD logs -f
        ;;
    ps)
        echo -e "${BLUE}Listing running containers...${RESET}"
        $COMPOSE_CMD ps
        ;;
    api)
        echo -e "${GREEN}Starting API service...${RESET}"
        $COMPOSE_CMD up -d verifact-api
        ;;
    ui)
        echo -e "${GREEN}Starting UI service...${RESET}"
        $COMPOSE_CMD up -d verifact-ui
        ;;
    db)
        echo -e "${GREEN}Starting database service...${RESET}"
        $COMPOSE_CMD up -d verifact-db
        ;;
    redis)
        echo -e "${GREEN}Starting Redis service...${RESET}"
        $COMPOSE_CMD up -d verifact-redis
        ;;
    api-logs)
        echo -e "${BLUE}Showing logs for API service...${RESET}"
        $COMPOSE_CMD logs -f verifact-api
        ;;
    ui-logs)
        echo -e "${BLUE}Showing logs for UI service...${RESET}"
        $COMPOSE_CMD logs -f verifact-ui
        ;;
    db-logs)
        echo -e "${BLUE}Showing logs for database service...${RESET}"
        $COMPOSE_CMD logs -f verifact-db
        ;;
    redis-logs)
        echo -e "${BLUE}Showing logs for Redis service...${RESET}"
        $COMPOSE_CMD logs -f verifact-redis
        ;;
    prune)
        echo -e "${YELLOW}Pruning all unused Docker resources...${RESET}"
        docker system prune --volumes -f
        ;;
    health)
        echo -e "${BLUE}Checking service health...${RESET}"
        echo -e "\n${BLUE}API Health Check:${RESET}"
        curl -s http://localhost:8000/health | python -m json.tool || echo -e "${RED}API is not available${RESET}"
        echo -e "\n${BLUE}Database Connection Check:${RESET}"
        $COMPOSE_CMD exec verifact-db pg_isready -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-postgres}" || echo -e "${RED}Database is not available${RESET}"
        echo -e "\n${BLUE}Redis Connection Check:${RESET}"
        $COMPOSE_CMD exec verifact-redis redis-cli ping || echo -e "${RED}Redis is not available${RESET}"
        ;;
    backup-db)
        echo -e "${GREEN}Creating database backup...${RESET}"
        BACKUP_FILE="verifact_db_backup_$(date +%Y%m%d_%H%M%S).sql"
        $COMPOSE_CMD exec -T verifact-db pg_dump -U "${POSTGRES_USER:-postgres}" "${POSTGRES_DB:-postgres}" > "./backups/$BACKUP_FILE"
        echo -e "${GREEN}Backup created: ./backups/$BACKUP_FILE${RESET}"
        ;;
    restore-db)
        if [[ -z "$2" ]]; then
            echo -e "${RED}Error: No backup file specified${RESET}"
            echo -e "Usage: $0 restore-db <backup-file>"
            exit 1
        fi
        BACKUP_FILE=$2
        if [[ ! -f "$BACKUP_FILE" ]]; then
            echo -e "${RED}Error: Backup file $BACKUP_FILE not found${RESET}"
            exit 1
        fi
        echo -e "${YELLOW}Restoring database from $BACKUP_FILE...${RESET}"
        $COMPOSE_CMD exec -T verifact-db psql -U "${POSTGRES_USER:-postgres}" "${POSTGRES_DB:-postgres}" < "$BACKUP_FILE"
        echo -e "${GREEN}Database restored successfully${RESET}"
        ;;
    *)
        echo -e "${RED}Error: Unknown command '$COMMAND'${RESET}"
        show_help
        exit 1
        ;;
esac 