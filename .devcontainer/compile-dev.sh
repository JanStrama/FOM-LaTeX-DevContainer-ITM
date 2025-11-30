#!/bin/bash
# Dev container compilation script for FOM LaTeX thesis

# Set colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}FOM LaTeX Thesis Compilation Script${NC}"
echo "=================================="

# Function to compile German version
compile_german() {
    echo -e "${YELLOW}Compiling German version...${NC}"
    ./compile.sh
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ German version compiled successfully!${NC}"
        echo "PDF: thesis_main.pdf"
    else
        echo -e "${RED}✗ German version compilation failed!${NC}"
        return 1
    fi
}

# Function to compile English version
compile_english() {
    echo -e "${YELLOW}Compiling English version...${NC}"
    ./compile.sh en
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ English version compiled successfully!${NC}"
        echo "PDF: thesis_englisch.pdf"
    else
        echo -e "${RED}✗ English version compilation failed!${NC}"
        return 1
    fi
}

# Function to clean temporary files
clean_files() {
    echo -e "${YELLOW}Cleaning temporary files...${NC}"
    rm -f ./*.bbl ./*.blg ./*.aux ./*.bcf ./*.ilg ./*.lof ./*.log ./*.lot ./*.nlo ./*.nls* ./*.out ./*.toc ./*.run.xml ./*.sub ./*.suc ./*.syc ./*.sym ./*.fdb_latexmk ./*.fls ./*.synctex.gz
    echo -e "${GREEN}✓ Temporary files cleaned!${NC}"
}

# Function to show help
show_help() {
    echo "Usage: $0 [option]"
    echo "Options:"
    echo "  de, german    Compile German version (default)"
    echo "  en, english   Compile English version"
    echo "  all           Compile both versions"
    echo "  clean         Clean temporary files"
    echo "  help          Show this help message"
}

# Main script logic
case "${1:-german}" in
    "de"|"german")
        compile_german
        ;;
    "en"|"english")
        compile_english
        ;;
    "all")
        compile_german && echo "" && compile_english
        ;;
    "clean")
        clean_files
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown option: $1${NC}"
        show_help
        exit 1
        ;;
esac