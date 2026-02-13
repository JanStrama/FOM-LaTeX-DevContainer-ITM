FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

# Install LaTeX dependencies
RUN apt-get update \
	&& apt-get install -y \
		wget \
		texlive-latex-recommended \
		texlive-latex-extra \
		texlive-fonts-recommended \
		texlive-bibtex-extra \
		texlive-lang-german \
		texlive-plain-generic \
		texlive-luatex \
		texlive-extra-utils \
		biber \
		latexmk \
		xz-utils \
		python3 \
		python3-pygments \
		pandoc \
		wkhtmltopdf \
		--no-install-recommends \
	&& rm -rf /var/lib/apt/lists/*

# Set up user environment
ENV USER=vscode
ENV PATH=/home/vscode/.local/bin:$PATH

# Create a custom compile script for the dev container
COPY ../compile.sh /home/vscode/compile.sh
RUN chmod +x /home/vscode/compile.sh

# Fix X11 Forwarding in case we are running on a Wayland System
# X11 und /tmp Verzeichnis vorbereiten
RUN mkdir -p /tmp/.X11-unix && chmod 1777 /tmp/.X11-unix && \
    chmod 1777 /tmp

# Set working directory
WORKDIR /workspace
