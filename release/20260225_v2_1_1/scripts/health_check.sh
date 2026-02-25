#!/bin/bash
# Health Check & Auto-Recovery Script for IDE Agent Wizard
# Usage: ./health_check.sh [--auto-restart]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOCKER_COMPOSE_FILE="../docker/docker-compose.yml"
WORKSPACE_DIR="workspace"
MEMORY_DIR="$WORKSPACE_DIR/memory"
WEB_UI_URL="http://localhost:8082/health"
KIMI_AGENT_URL="http://localhost:8081/health"
TELEGRAM_CONTAINER="ide-agent-telegram"
WEB_UI_CONTAINER="ide-agent-web"
KIMI_AGENT_CONTAINER="ide-agent-kimi"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Check if Docker is running
check_docker() {
    log "Checking Docker..."
    if ! docker info &>/dev/null; then
        error "Docker is not running!"
        return 1
    fi
    success "Docker is running"
    return 0
}

# Check container status
check_container() {
    local container_name=$1
    local container_friendly=$2
    
    log "Checking $container_friendly..."
    if docker ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
        success "$container_friendly is running"
        return 0
    else
        error "$container_friendly is NOT running!"
        return 1
    fi
}

# Check Kimi Agent health
check_kimi_agent() {
    log "Checking Kimi Agent health..."
    if curl -s "$KIMI_AGENT_URL" &>/dev/null; then
        success "Kimi Agent is responding"
        return 0
    else
        error "Kimi Agent is not responding!"
        return 1
    fi
}

# Check Web UI health
check_web_ui() {
    log "Checking Web UI health..."
    if curl -s "$WEB_UI_URL" &>/dev/null; then
        success "Web UI is responding"
        return 0
    else
        error "Web UI is not responding!"
        return 1
    fi
}

# Check memory files
check_memory() {
    log "Checking memory files..."
    if [ -f "$MEMORY_DIR/agent_memory.db" ]; then
        local size=$(du -h "$MEMORY_DIR/agent_memory.db" | cut -f1)
        success "Memory database exists ($size)"
        
        # Check if database is valid
        if sqlite3 "$MEMORY_DIR/agent_memory.db" "SELECT COUNT(*) FROM memories;" &>/dev/null; then
            local count=$(sqlite3 "$MEMORY_DIR/agent_memory.db" "SELECT COUNT(*) FROM memories;")
            log "  → $count memories stored"
        fi
        return 0
    else
        warning "Memory database not found"
        return 1
    fi
}

# Check SOUL.md and USER.md
check_identity() {
    log "Checking identity files..."
    local all_ok=true
    
    if [ -f "$WORKSPACE_DIR/SOUL.md" ]; then
        local agent_name=$(grep -m1 "^# SOUL" "$WORKSPACE_DIR/SOUL.md" | sed 's/# SOUL - //')
        success "SOUL.md found: $agent_name"
    else
        error "SOUL.md not found!"
        all_ok=false
    fi
    
    if [ -f "$WORKSPACE_DIR/USER.md" ]; then
        local user_name=$(grep -m1 "^# USER" "$WORKSPACE_DIR/USER.md" | sed 's/# USER - //')
        success "USER.md found: $user_name"
    else
        error "USER.md not found!"
        all_ok=false
    fi
    
    $all_ok && return 0 || return 1
}

# Load all SOULs into memory info
show_templates() {
    log "Available templates:"
    if [ -d "templates" ]; then
        for template_dir in templates/*/; do
            if [ -f "${template_dir}SOUL.md" ]; then
                local name=$(basename "$template_dir")
                local role=$(grep -m1 "Role:" "${template_dir}SOUL.md" | cut -d':' -f2 | xargs | cut -c1-50)
                echo -e "  ${GREEN}•${NC} $name - $role"
            fi
        done
    fi
}

# Restart services
restart_services() {
    log "Restarting services..."
    
    # Pre-load identity files into summary
    log "Loading identity files into memory..."
    local agent_name="Unknown"
    local user_name="Unknown"
    
    if [ -f "$WORKSPACE_DIR/SOUL.md" ]; then
        agent_name=$(grep -m1 "^# SOUL" "$WORKSPACE_DIR/SOUL.md" | sed 's/# SOUL - //')
        log "  Agent: $agent_name"
    fi
    
    if [ -f "$WORKSPACE_DIR/USER.md" ]; then
        user_name=$(grep -m1 "^# USER" "$WORKSPACE_DIR/USER.md" | sed 's/# USER - //')
        log "  User: $user_name"
    fi
    
    # Stop containers
    log "Stopping containers..."
    docker compose -f "$DOCKER_COMPOSE_FILE" down
    
    # Start containers
    log "Starting containers..."
    docker compose -f "$DOCKER_COMPOSE_FILE" --profile web up -d
    
    # Wait for services to be ready
    log "Waiting for services to be ready..."
    local retries=0
    local max_retries=30
    
    while [ $retries -lt $max_retries ]; do
        if curl -s "$WEB_UI_URL" &>/dev/null && curl -s "$KIMI_AGENT_URL" &>/dev/null; then
            success "All services are ready!"
            return 0
        fi
        sleep 2
        retries=$((retries + 1))
        echo -n "."
    done
    echo
    
    error "Services did not become ready in time"
    return 1
}

# Quick restart (no build)
quick_restart() {
    log "Performing quick restart..."
    docker compose -f "$DOCKER_COMPOSE_FILE" restart
    sleep 5
    
    if curl -s "$WEB_UI_URL" &>/dev/null; then
        success "Services restarted successfully!"
    else
        warning "Quick restart may have failed, trying full restart..."
        restart_services
    fi
}

# Show system status
show_status() {
    echo ""
    echo "=========================================="
    echo "    IDE Agent Wizard - System Status"
    echo "=========================================="
    echo ""
    
    local issues=0
    
    check_docker || ((issues++))
    echo ""
    
    check_container "$KIMI_AGENT_CONTAINER" "Kimi Agent" || ((issues++))
    check_container "$WEB_UI_CONTAINER" "Web UI" || ((issues++))
    check_container "$TELEGRAM_CONTAINER" "Telegram Bot" || ((issues++))
    echo ""
    
    check_kimi_agent || ((issues++))
    check_web_ui || ((issues++))
    echo ""
    
    check_memory
    echo ""
    
    check_identity
    echo ""
    
    show_templates
    echo ""
    
    if [ $issues -eq 0 ]; then
        echo -e "${GREEN}✓ All systems operational!${NC}"
    else
        echo -e "${RED}✗ Found $issues issue(s)${NC}"
    fi
    
    echo ""
    echo "=========================================="
    
    return $issues
}

# Main function
main() {
    local auto_restart=false
    
    # Parse arguments
    if [ "$1" = "--auto-restart" ]; then
        auto_restart=true
    fi
    
    cd "$(dirname "$0")/.."
    
    echo ""
    log "Starting health check..."
    echo ""
    
    show_status
    local status=$?
    
    if [ $status -ne 0 ] && [ "$auto_restart" = true ]; then
        echo ""
        warning "Issues detected! Auto-restarting services..."
        echo ""
        restart_services
        
        # Check again
        echo ""
        log "Verifying restart..."
        show_status
    elif [ $status -ne 0 ]; then
        echo ""
        warning "Issues detected! Run with --auto-restart to fix automatically"
        echo "  ./health_check.sh --auto-restart"
    fi
    
    exit $status
}

# Run main function
main "$@"
