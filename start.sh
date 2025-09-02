#!/bin/bash

# DMR Project Startup Script (Digital Medical Records)

set -e

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🏥 DMR Digital Medical Records System Startup Script${NC}"
echo -e "${BLUE}===============================================${NC}"

# Check Python version
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python3 not installed, please install Python 3.12+${NC}"
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    required_version="3.12"
    
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)" 2>/dev/null; then
        echo -e "${RED}❌ Python version too low (current: $python_version, required: $required_version+)${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Python version check passed ($python_version)${NC}"
}

# Check uv package manager
check_uv() {
    if ! command -v uv &> /dev/null; then
        echo -e "${RED}❌ uv not installed, attempting to install...${NC}"
        curl -LsSf https://astral.sh/uv/install.sh | sh
        
        # Reload PATH
        export PATH="$HOME/.cargo/bin:$PATH"
        
        if ! command -v uv &> /dev/null; then
            echo -e "${RED}❌ uv installation failed, please install manually: https://docs.astral.sh/uv/getting-started/installation/${NC}"
            exit 1
        fi
    fi
    
    echo -e "${GREEN}✅ uv package manager check passed${NC}"
}

# Parse command line arguments
ACTION=${1:-"dev"}

case $ACTION in
    "dev"|"develop")
        echo -e "${GREEN}🔧 Starting development environment...${NC}"
        
        check_python
        check_uv
        
        # Sync dependencies
        echo -e "${YELLOW}📦 Syncing project dependencies...${NC}"
        uv sync
        
        # Run database migrations
        echo -e "${YELLOW}🗃️ Running database migrations...${NC}"
        uv run python manage.py makemigrations
        uv run python manage.py migrate
        
        echo -e "${GREEN}🚀 Starting Django development server...${NC}"
        uv run python manage.py runserver
        ;;
        
    "dev-bg"|"dev-background")
        echo -e "${GREEN}🔧 Starting development environment in background...${NC}"
        
        check_python
        check_uv
        
        # Sync dependencies
        echo -e "${YELLOW}📦 Syncing project dependencies...${NC}"
        uv sync
        
        # Run database migrations
        echo -e "${YELLOW}🗃️ Running database migrations...${NC}"
        uv run python manage.py makemigrations
        uv run python manage.py migrate
        
        echo -e "${GREEN}🚀 Starting Django development server in background...${NC}"
        nohup uv run python manage.py runserver > dmr_server.log 2>&1 &
        
        # Get process ID
        PID=$!
        echo $PID > dmr_server.pid
        
        echo -e "${YELLOW}⏳ Waiting for service to start...${NC}"
        sleep 5
        
        # Check if service started successfully
        if ps -p $PID > /dev/null; then
            echo -e "${GREEN}✅ Development server started successfully!${NC}"
            echo -e "${BLUE}📋 Service Information:${NC}"
            echo -e "  🌐 Django Dev Server: http://127.0.0.1:8000/"
            echo -e "  📖 API Documentation: http://127.0.0.1:8000/schema/swagger-ui/"
            echo -e "  🛡️ Django Admin:      http://127.0.0.1:8000/admin/"
            echo -e "  📊 Process ID:        $PID"
            echo -e "  📝 Log File:          dmr_server.log"
            echo -e ""
            echo -e "${YELLOW}💡 Use '$0 stop' to stop the service${NC}"
            echo -e "${YELLOW}💡 Use '$0 logs' to view logs${NC}"
        else
            echo -e "${RED}❌ Service failed to start, please check log file dmr_server.log${NC}"
            exit 1
        fi
        ;;
        
    "init"|"setup")
        echo -e "${GREEN}🏗️ Initializing DMR project...${NC}"
        
        check_python
        check_uv
        
        # Sync dependencies
        echo -e "${YELLOW}📦 Installing project dependencies...${NC}"
        uv sync
        
        # Database setup
        echo -e "${YELLOW}🗃️ Initializing database...${NC}"
        uv run python manage.py makemigrations
        uv run python manage.py migrate
        
        # Create superuser
        echo -e "${YELLOW}👤 Creating superuser...${NC}"
        echo -e "${BLUE}Please follow the prompts to enter admin account information:${NC}"
        uv run python manage.py createsuperuser
        
        echo -e "${GREEN}✅ Project initialization completed!${NC}"
        echo -e "${BLUE}💡 Run '$0 dev' to start the development server${NC}"
        ;;
        
    "migrate")
        echo -e "${GREEN}🗃️ Running database migrations...${NC}"
        uv run python manage.py makemigrations
        uv run python manage.py migrate
        echo -e "${GREEN}✅ Migration completed${NC}"
        ;;
        
    "shell")
        echo -e "${BLUE}🐍 Entering Django shell...${NC}"
        uv run python manage.py shell
        ;;
        
    "test")
        echo -e "${GREEN}🧪 Running Django tests...${NC}"
        uv run python manage.py test
        ;;
        
    "collect-static")
        echo -e "${GREEN}📁 Collecting static files...${NC}"
        uv run python manage.py collectstatic --noinput
        echo -e "${GREEN}✅ Static files collection completed${NC}"
        ;;
        
    "create-superuser")
        echo -e "${GREEN}👤 Creating superuser...${NC}"
        uv run python manage.py createsuperuser
        ;;
        
    "load-fixtures")
        echo -e "${GREEN}📊 Loading test data...${NC}"
        # Check if fixtures files exist
        if [ -d "fixtures" ]; then
            uv run python manage.py loaddata fixtures/*.json
            echo -e "${GREEN}✅ Test data loading completed${NC}"
        else
            echo -e "${YELLOW}⚠️ Fixtures directory not found, skipping data loading${NC}"
        fi
        ;;
        
    "logs")
        echo -e "${BLUE}📋 Viewing service logs...${NC}"
        if [ -f "dmr_server.log" ]; then
            tail -f dmr_server.log
        else
            echo -e "${YELLOW}⚠️ Log file does not exist, service may not be running in background${NC}"
        fi
        ;;
        
    "stop")
        echo -e "${RED}🛑 Stopping background service...${NC}"
        if [ -f "dmr_server.pid" ]; then
            PID=$(cat dmr_server.pid)
            if ps -p $PID > /dev/null; then
                kill $PID
                echo -e "${GREEN}✅ Service stopped (PID: $PID)${NC}"
            else
                echo -e "${YELLOW}⚠️ Process does not exist (PID: $PID)${NC}"
            fi
            rm dmr_server.pid
        else
            echo -e "${YELLOW}⚠️ PID file does not exist, attempting to find and stop Django processes...${NC}"
            pkill -f "python.*manage.py runserver" || echo -e "${YELLOW}⚠️ No running Django service found${NC}"
        fi
        ;;
        
    "status")
        echo -e "${BLUE}📊 Service status check:${NC}"
        
        # Check PID file
        if [ -f "dmr_server.pid" ]; then
            PID=$(cat dmr_server.pid)
            if ps -p $PID > /dev/null; then
                echo -e "${GREEN}✅ Background service running (PID: $PID)${NC}"
            else
                echo -e "${RED}❌ PID file exists but process not running (PID: $PID)${NC}"
                rm dmr_server.pid
            fi
        else
            echo -e "${YELLOW}⚠️ Background service not running${NC}"
        fi
        
        # Check port
        if lsof -i :8000 > /dev/null 2>&1; then
            echo -e "${GREEN}✅ Port 8000 is occupied (Django service may be running)${NC}"
            echo -e "${BLUE}Process information:${NC}"
            lsof -i :8000
        else
            echo -e "${YELLOW}⚠️ Port 8000 is not occupied${NC}"
        fi
        
        echo ""
        echo -e "${BLUE}🌐 Available endpoints:${NC}"
        echo -e "  Homepage:        http://127.0.0.1:8000/"
        echo -e "  API Documentation: http://127.0.0.1:8000/schema/swagger-ui/"
        echo -e "  Admin Panel:     http://127.0.0.1:8000/admin/"
        echo -e "  API Auth:        http://127.0.0.1:8000/api-auth/"
        echo -e "  Patients API:    http://127.0.0.1:8000/api/patients/"
        echo -e "  Student Groups:  http://127.0.0.1:8000/api/student-groups/"
        ;;
        
    "health")
        echo -e "${BLUE}🏥 Health check...${NC}"
        
        # Check if service is responding
        if curl -s http://127.0.0.1:8000/ > /dev/null; then
            echo -e "${GREEN}✅ Django service responding normally${NC}"
            
            # Check API endpoints
            if curl -s http://127.0.0.1:8000/schema/ > /dev/null; then
                echo -e "${GREEN}✅ API Schema endpoint normal${NC}"
            else
                echo -e "${YELLOW}⚠️ API Schema endpoint abnormal${NC}"
            fi
            
            # Check database connection
            uv run python manage.py check --database default > /dev/null 2>&1
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}✅ Database connection normal${NC}"
            else
                echo -e "${RED}❌ Database connection abnormal${NC}"
            fi
            
        else
            echo -e "${RED}❌ Django service inaccessible${NC}"
        fi
        ;;
        
    "clean")
        echo -e "${RED}🧹 Cleaning project files...${NC}"
        
        # Stop service
        if [ -f "dmr_server.pid" ]; then
            PID=$(cat dmr_server.pid)
            kill $PID 2>/dev/null || true
            rm dmr_server.pid
        fi
        
        # Clean log files
        rm -f dmr_server.log
        
        # Clean Python cache
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
        find . -name "*.pyc" -delete 2>/dev/null || true
        
        # Clean media files (careful operation)
        read -p "Clean media files? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf media/uploads/
            echo -e "${GREEN}✅ Media files cleaned${NC}"
        fi
        
        echo -e "${GREEN}✅ Cleanup completed${NC}"
        ;;
        
    "reinstall")
        echo -e "${YELLOW}🔄 Reinstalling dependencies...${NC}"
        uv sync --reinstall
        echo -e "${GREEN}✅ Dependencies reinstallation completed${NC}"
        ;;
        
    "help"|"--help"|"-h")
        echo -e "${BLUE}Usage: $0 [command]${NC}"
        echo ""
        echo -e "${YELLOW}Service Management:${NC}"
        echo -e "  dev           - Start development server (foreground)"
        echo -e "  dev-bg        - Start development server (background)"
        echo -e "  stop          - Stop background service"
        echo -e "  status        - View service status"
        echo -e "  health        - Health check"
        echo ""
        echo -e "${YELLOW}Project Management:${NC}"
        echo -e "  init          - Initialize project (first run)"
        echo -e "  migrate       - Run database migrations"
        echo -e "  create-superuser - Create superuser"
        echo -e "  collect-static - Collect static files"
        echo -e "  load-fixtures - Load test data"
        echo ""
        echo -e "${YELLOW}Development & Debugging:${NC}"
        echo -e "  shell         - Enter Django shell"
        echo -e "  test          - Run tests"
        echo -e "  logs          - View service logs"
        echo ""
        echo -e "${YELLOW}Maintenance Tools:${NC}"
        echo -e "  clean         - Clean project files"
        echo -e "  reinstall     - Reinstall dependencies"
        echo -e "  help          - Show this help information"
        echo ""
        echo -e "${BLUE}🏥 DMR Project Features:${NC}"
        echo -e "  ✅ Patient Management System - Patient information and file management"
        echo -e "  ✅ Medical Observation Records - Blood pressure, heart rate, body temperature records"
        echo -e "  ✅ Student Group Management - Medical student grouping functionality"
        echo -e "  ✅ REST API - Complete API interface"
        echo -e "  ✅ Swagger Documentation - Auto-generated API documentation"
        echo -e "  ✅ Admin Panel - Django Admin interface"
        echo ""
        echo -e "${BLUE}📋 Quick Start:${NC}"
        echo -e "  1. First time: $0 init"
        echo -e "  2. Start dev:  $0 dev"
        echo -e "  3. Background: $0 dev-bg"
        echo -e "  4. Check status: $0 status"
        ;;
        
    *)
        echo -e "${RED}❌ Unknown command: $ACTION${NC}"
        echo -e "${YELLOW}Use '$0 help' to view available commands${NC}"
        exit 1
        ;;
esac
