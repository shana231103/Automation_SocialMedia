# Makefile for Automation Social Media Backend

.PHONY: help install db run test test-integration clean

# Môi trường ảo Python mặc định
PYTHON = .venv/bin/python
PIP = .venv/bin/pip
UVICORN = .venv/bin/uvicorn

help:
	@echo "======================================================================"
	@echo "Makefile tiện ích của Backend Automation Social Media"
	@echo "======================================================================"
	@echo "Các lệnh khả dụng:"
	@echo "  make install           - Cài đặt thư viện dependencies"
	@echo "  make db                - Khởi tạo bảng cơ sở dữ liệu ban đầu"
	@echo "  make run               - Chạy FastAPI server ở chế độ phát triển"
	@echo "  make test              - Chạy các Unit Test giả lập cô lập (Mock)"
	@echo "  make test-integration  - Chạy kịch bản kiểm thử tích hợp thực tế"
	@echo "  make clean             - Dọn dẹp bộ nhớ đệm python cache"
	@echo "======================================================================"

install:
	$(PIP) install -r requirements.txt

db:
	$(PYTHON) create_db.py

run:
	$(UVICORN) app.main:app --reload --port 8000

test:
	$(PYTHON) -m unittest discover -s .

test-integration:
	$(PYTHON) test_automation.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".venv" -prune -o -type d -name "profiles" -exec rm -rf {} +
