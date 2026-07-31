# Makefile for building Go half-close client

.PHONY: all build clean test help

# Default target
all: build

# Build for current platform
build:
	@echo "Building halfclose_client for current platform..."
	go build -o halfclose_client halfclose_client.go
	@echo "✓ Built: ./halfclose_client"

# Build for all platforms
build-all: build-linux build-macos build-windows
	@echo "✓ Built binaries for all platforms"

# Build for Linux
build-linux:
	@echo "Building for Linux..."
	GOOS=linux GOARCH=amd64 go build -o halfclose_client.linux halfclose_client.go
	@echo "✓ Built: ./halfclose_client.linux"

# Build for macOS
build-macos:
	@echo "Building for macOS..."
	GOOS=darwin GOARCH=amd64 go build -o halfclose_client.macos halfclose_client.go
	@echo "✓ Built: ./halfclose_client.macos"

# Build for Windows
build-windows:
	@echo "Building for Windows..."
	GOOS=windows GOARCH=amd64 go build -o halfclose_client.exe halfclose_client.go
	@echo "✓ Built: ./halfclose_client.exe"

# Clean build artifacts
clean:
	@echo "Cleaning build artifacts..."
	rm -f halfclose_client halfclose_client.linux halfclose_client.macos halfclose_client.exe
	@echo "✓ Cleaned"

# Test the binary (requires running server)
test: build
	@echo "Testing halfclose_client..."
	@echo "Note: This requires a running get-back server on localhost:9092"
	./halfclose_client -host localhost -port 9092 || echo "⚠ Test failed - is server running?"

# Show help
help:
	@echo "Available targets:"
	@echo "  make build          - Build for current platform"
	@echo "  make build-all      - Build for Linux, macOS, and Windows"
	@echo "  make build-linux    - Build for Linux"
	@echo "  make build-macos    - Build for macOS"
	@echo "  make build-windows  - Build for Windows"
	@echo "  make clean          - Remove build artifacts"
	@echo "  make test           - Build and test (requires running server)"
	@echo "  make help           - Show this help message"
