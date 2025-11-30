# FOM LaTeX Thesis Dev Container

This development container is optimized for working with the FOM LaTeX Thesis template.

## Features

- **Complete LaTeX Environment**: Full TeX Live installation with LuaLaTeX, XeLaTeX, and pdfLaTeX
- **Biber Support**: For bibliography management
- **German Language Support**: Complete German language Spell Check
- **VS Code Extensions**: Pre-configured LaTeX Workshop and supporting extensions
- **Compilation Scripts**: Easy compilation for both German and English versions

## Quick Start

1. Open this folder in VS Code
2. When prompted, reopen in the container
3. Use the built-in terminal to compile your thesis

## Compilation Commands

```bash
# German version
./compile.sh

# English version
./compile.sh en
```

## VS Code Features

- **LaTeX Workshop**: Auto-build on save, PDF preview, and compilation tools
- **LTeX – LanguageTool grammar/spell checking**: German and English spell checking
- **Git Integration**: Built-in Git support

## File Structure

- `thesis_main.tex` - Main German thesis file
- `compile.sh` - Original compilation script
- `.devcontainer/` - Dev container configuration
- `kapitel/` - Chapter files
- `literatur/` - Bibliography files

## Development Tips

- Use the built-in terminal for all compilation
- The PDF viewer opens automatically after successful compilation
- Changes are auto-detected and recompiled (if enabled in settings)
