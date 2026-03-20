# Rove R2-4K-DUAL Firmware Build
# ─────────────────────────────────────────────────────────────────
# Rebuilds R2D.bin with a modified rootfs (RTSP VencType=3 config).
#
# First time:
#   make setup        # extract R2D.tar from APK → R2D.bin + rootfs
#   make backup       # back up stock default.ini
#   (edit rootfs/bootconfig/bin/default.ini)
#   make diff         # review changes
#   make build        # repack rootfs → R2D.bin
#   make tar          # create R2D.tar
#   make flash-sd SD=/Volumes/SDCARD
#   make verify       # after camera reboots
#
# Shortcuts:
#   make all          # build + tar
#   make flash SD=..  # build + tar + copy to SD
#
# Recovery:
#   make restore && make tar && make flash-sd SD=/Volumes/SDCARD

SHELL    := /bin/bash
FW_DIR   := $(CURDIR)/work
FWTOOL   := python3 $(CURDIR)/scripts/fwtool.py --fw-dir $(FW_DIR)
REPO     := $(CURDIR)/..
APK      := $(REPO)/rove_split_firmware_pack.apk
INI      := $(FW_DIR)/rootfs/bootconfig/bin/default.ini
INI_BAK  := $(INI).bak
VERIFY   := $(CURDIR)/scripts/verify.sh
OTA_PUSH := $(CURDIR)/scripts/ota-push.sh
CAM_IP   ?= 192.168.1.252
SD       ?= /Volumes/SDCARD

.PHONY: help setup extract build tar flash-sd flash-ota flash-stock info diff backup restore verify \
        edit clean check-tools all flash push

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

check-tools: ## Verify required tools are installed
	@command -v python3 >/dev/null || { echo "Error: python3 required"; exit 1; }
	@command -v cpio    >/dev/null || { echo "Error: cpio required"; exit 1; }
	@command -v gzip    >/dev/null || { echo "Error: gzip required"; exit 1; }
	@echo "All required tools available."

setup: check-tools ## Extract R2D.tar from APK and unpack R2D.bin + rootfs
	@test -f "$(APK)" || { echo "Error: $(APK) not found"; exit 1; }
	@mkdir -p "$(FW_DIR)"
	@if [ ! -f "$(FW_DIR)/R2D.bin" ]; then \
		echo "Extracting R2D.tar from APK ..."; \
		unzip -o "$(APK)" assets/R2D.tar -d "$(FW_DIR)" && \
		tar xf "$(FW_DIR)/assets/R2D.tar" -C "$(FW_DIR)" && \
		rm -rf "$(FW_DIR)/assets"; \
		echo "  → $(FW_DIR)/R2D.bin"; \
	else \
		echo "$(FW_DIR)/R2D.bin already exists — skipping APK extraction."; \
	fi
	$(FWTOOL) extract

backup: ## Back up original default.ini (before any edits)
	@if [ -f "$(INI_BAK)" ]; then \
		echo "Backup already exists: $(INI_BAK)"; \
	elif [ -f "$(INI)" ]; then \
		cp "$(INI)" "$(INI_BAK)"; \
		echo "Backed up → $(INI_BAK)"; \
	else \
		echo "Error: $(INI) not found — run 'make setup' first"; \
		exit 1; \
	fi

edit: ## Open default.ini in $$EDITOR
	@test -f "$(INI)" || { echo "Error: run 'make setup' first"; exit 1; }
	$${EDITOR:-nano} "$(INI)"

diff: ## Show config changes from stock default.ini
	@if [ -f "$(INI_BAK)" ] && [ -f "$(INI)" ]; then \
		diff -u "$(INI_BAK)" "$(INI)" || true; \
	else \
		$(FWTOOL) diff; \
	fi

build: check-tools ## Repack rootfs and rebuild R2D.bin
	@test -f "$(INI)" || { echo "Error: run 'make setup' first"; exit 1; }
	$(FWTOOL) build

tar: ## Create R2D.tar from R2D.bin + bootloader components
	$(FWTOOL) tar

flash-sd: ## Copy R2D.bin to SD card as SigmastarUpgradeSD.bin (set SD=/path)
	@test -d "$(SD)" || { echo "Error: SD card not found at $(SD)"; echo "Usage: make flash-sd SD=/Volumes/YOUR_SD"; exit 1; }
	$(FWTOOL) flash-sd "$(SD)"

flash-ota: ## Upload R2D.tar to camera over WiFi and trigger OTA update
	@test -f "$(FW_DIR)/R2D.tar" || { echo "Error: run 'make tar' first"; exit 1; }
	@bash "$(OTA_PUSH)" "$(FW_DIR)/R2D.tar" "$(CAM_IP)"

info: ## Show firmware layout, partition sizes, and integrity checks
	$(FWTOOL) info

verify: ## Run post-flash verification (ping, RTSP, MJPEG)
	@bash "$(VERIFY)" "$(CAM_IP)"

restore: ## Restore R2D.bin to stock from backup
	$(FWTOOL) restore

flash-stock: ## OTA push the original stock firmware to the camera
	@test -f "$(APK)" || { echo "Error: $(APK) not found"; exit 1; }
	@echo "Extracting stock R2D.tar from APK ..."
	@mkdir -p "$(FW_DIR)/stock"
	@unzip -o "$(APK)" assets/R2D.tar -d "$(FW_DIR)/stock" 2>/dev/null
	@mv "$(FW_DIR)/stock/assets/R2D.tar" "$(FW_DIR)/stock/R2D.tar"
	@rm -rf "$(FW_DIR)/stock/assets"
	@echo "Pushing stock firmware to camera ..."
	@bash "$(OTA_PUSH)" "$(FW_DIR)/stock/R2D.tar" "$(CAM_IP)"

clean: ## Remove build artifacts (keeps rootfs/ and backups)
	rm -f "$(FW_DIR)/rootfs.cpio.gz" "$(FW_DIR)/rootfs_mod.cpio.gz" "$(FW_DIR)/R2D.tar"
	@echo "Cleaned build artifacts."

clean-all: ## Remove entire work directory (full reset)
	rm -rf "$(FW_DIR)"
	@echo "Removed $(FW_DIR). Run 'make setup' to start fresh."

# ── Convenience aliases ──

all: build tar ## Build and package (shortcut)
flash: build flash-sd ## Build and copy to SD card
push: build tar flash-ota ## Build, package, and OTA push over WiFi
