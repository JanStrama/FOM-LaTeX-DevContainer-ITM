#!/bin/bash

# Script zur Konvertierung von HTML/MD Dateien in PDF
# Quellverzeichnis: fluechtige_quellen/ki_prompt/
# Zielverzeichnis: abbildungen/ki_belege/

set -e  # Bei Fehlern abbrechen

# Verzeichnisse definieren
SOURCE_DIR="fluechtige_quellen/ki_prompt"
TARGET_DIR="abbildungen/ki_belege"

# Farben für Ausgabe
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging Funktion
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Verzeichnisse prüfen
if [ ! -d "$SOURCE_DIR" ]; then
    error "Quellverzeichnis '$SOURCE_DIR' existiert nicht!"
    exit 1
fi

if [ ! -d "$TARGET_DIR" ]; then
    warn "Zielverzeichnis '$TARGET_DIR' existiert nicht, wird erstellt..."
    mkdir -p "$TARGET_DIR"
fi

# Tools prüfen
check_tool() {
    if ! command -v "$1" &> /dev/null; then
        error "Tool '$1' ist nicht installiert oder nicht im PATH gefunden!"
        return 1
    fi
    return 0
}

log "Prüfe benötigte Tools..."
TOOLS_MISSING=0

if ! check_tool "pandoc"; then
    TOOLS_MISSING=1
fi

if ! check_tool "wkhtmltopdf"; then
    TOOLS_MISSING=1
fi

if [ $TOOLS_MISSING -eq 1 ]; then
    error "Ein oder mehrere benötigte Tools sind nicht installiert!"
    error "Bitte installieren Sie pandoc und wkhtmltopdf:"
    error "  Ubuntu/Debian: sudo apt-get install pandoc wkhtmltopdf"
    error "  CentOS/RHEL:   sudo yum install pandoc wkhtmltopdf"
    error "  macOS:         brew install pandoc wkhtmltopdf"
    exit 1
fi

log "Alle benötigten Tools gefunden."

# Zähler für konvertierte Dateien
CONVERTED_COUNT=0
SKIPPED_COUNT=0

# Funktion zur Normalisierung von Dateinamen
normalize_filename() {
    local filename="$1"
    # Entferne die Erweiterung, normalisiere, füge .pdf hinzu
    local basename="${filename%.*}"
    local normalized=$(echo "$basename" | tr '[:upper:]' '[:lower:]' | tr ' ' '_' | sed 's/[^a-z0-9_-]//g')
    echo "${normalized}.pdf"
}

# Funktion zur Konvertierung von MD zu PDF
convert_md_to_pdf() {
    local input_file="$1"
    local output_file="$2"

    log "Konvertiere MD: $input_file -> $output_file"

    # Pandoc Optionen für bessere PDF-Qualität
    if pandoc "$input_file" -o "$output_file" \
        --pdf-engine=pdflatex \
        --variable=geometry:margin=1in \
        --variable=fontsize:11pt \
        --variable=paper:a4 \
        --variable=colorlinks=true \
        --variable=allcolors=blue \
        --highlight-style=pygments \
        2>/dev/null; then
        log "MD Konvertierung erfolgreich: $output_file"
        return 0
    else
        error "MD Konvertierung fehlgeschlagen: $input_file"
        return 1
    fi
}

# Funktion zur Konvertierung von HTML zu PDF
convert_html_to_pdf() {
    local input_file="$1"
    local output_file="$2"

    log "Konvertiere HTML: $input_file -> $output_file"

    # wkhtmltopdf Optionen für bessere PDF-Qualität
    if wkhtmltopdf \
        --page-size A4 \
        --margin-top 1in \
        --margin-right 1in \
        --margin-bottom 1in \
        --margin-left 1in \
        --encoding UTF-8 \
        --enable-local-file-access \
        "$input_file" "$output_file" 2>/dev/null; then
        log "HTML Konvertierung erfolgreich: $output_file"
        return 0
    else
        error "HTML Konvertierung fehlgeschlagen: $input_file"
        return 1
    fi
}

# Hauptverarbeitung
log "Suche nach Dateien in '$SOURCE_DIR'..."

# Finde alle .md und .html Dateien
find "$SOURCE_DIR" -type f \( -name "*.md" -o -name "*.html" \) | while read -r file; do
    filename=$(basename "$file")
    extension="${filename##*.}"
    normalized_name=$(normalize_filename "$filename")
    output_path="$TARGET_DIR/$normalized_name"

    log "Verarbeite Datei: $filename"

    # Prüfen ob Zieldatei bereits existiert
    if [ -f "$output_path" ]; then
        warn "Zieldatei existiert bereits, überspringe: $normalized_name"
        ((SKIPPED_COUNT++))
        continue
    fi

    # Je nach Dateityp konvertieren
    case "$extension" in
        "md")
            if convert_md_to_pdf "$file" "$output_path"; then
                ((CONVERTED_COUNT++))
            fi
            ;;
        "html")
            if convert_html_to_pdf "$file" "$output_path"; then
                ((CONVERTED_COUNT++))
            fi
            ;;
        *)
            warn "Nicht unterstützter Dateityp: $extension"
            ;;
    esac
done

# Zusammenfassung
log "=========================================="
log "Konvertierung abgeschlossen!"
log "Konvertierte Dateien: $CONVERTED_COUNT"
log "Übersprungene Dateien: $SKIPPED_COUNT"
log "=========================================="

if [ $CONVERTED_COUNT -gt 0 ]; then
    log "PDF-Dateien wurden in '$TARGET_DIR' erstellt."
    log "Verzeichnisinhalt:"
    ls -la "$TARGET_DIR"/*.pdf 2>/dev/null || warn "Keine PDF-Dateien gefunden."
else
    warn "Keine Dateien wurden konvertiert."
fi

exit 0
